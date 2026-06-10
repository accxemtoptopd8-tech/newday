import litellm
import json
import hashlib
import tiktoken
from json_repair import repair_json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from Core.config import DEFAULT_MODEL_PRIORITY, DRY_RUN_MODE, REDIS_URL
from Core.redis_client import redis_client, safe_redis_execute
from Core.mongo import db

litellm.drop_params = True
litellm.num_retries = 2
litellm.retry_policy = {"TimeoutError": 2, "RateLimitError": 2}

# Định nghĩa bảng giá (cập nhật theo thời giá)
MODEL_COST_PER_1K = {
    "gpt-3.5-turbo": (0.0015, 0.002),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gemini/gemini-1.5-flash": (0.000, 0.000),   # free tier
    "deepseek/deepseek-chat": (0.00014, 0.00028),
    "openrouter/openai/gpt-4o-mini": (0.00015, 0.0006),
}

def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    cost_key = model
    if cost_key not in MODEL_COST_PER_1K:
        # fallback
        return 0.0
    prompt_cost, completion_cost = MODEL_COST_PER_1K[cost_key]
    return (prompt_tokens / 1000) * prompt_cost + (completion_tokens / 1000) * completion_cost

def get_cache_key(model: str, messages: List[Dict]) -> str:
    content = json.dumps([model, messages], sort_keys=True)
    return f"llm_cache:{hashlib.sha256(content.encode()).hexdigest()}"

def truncate_by_tokens(text: str, max_tokens: int, model: str = "gpt-3.5-turbo") -> str:
    enc = tiktoken.encoding_for_model(model.split('/')[-1])
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    truncated_tokens = tokens[:max_tokens]
    return enc.decode(truncated_tokens)

def dynamic_token_buffer(system_prompt: str, user_prompt: str, model: str) -> tuple[str, str]:
    try:
        model_info = litellm.get_model_info(model)
        max_input = model_info.get("max_input_tokens", 8000)
    except:
        max_input = 8000
    buffer = int(max_input * 0.1)  # 10% buffer
    sys_tokens = len(tiktoken.encoding_for_model(model.split('/')[-1]).encode(system_prompt))
    available = max_input - buffer - sys_tokens
    if available < 500:
        available = 500
    truncated_user = truncate_by_tokens(user_prompt, available, model)
    return system_prompt, truncated_user

def safe_llm_call(
    model: str,
    messages: List[Dict],
    response_format: Optional[Dict] = None,
    project_id: Optional[str] = None,
    worker_name: str = "unknown"
) -> Dict:
    """
    Gọi LLM với:
    - Cache (TTL 24h)
    - Fallback model (nếu lỗi quota)
    - Dry-run mode
    - Dynamic token buffer (đã được gọi từ bên ngoài)
    - Tính cost và ghi event
    """
    if DRY_RUN_MODE:
        print(f"🔸 [DRY_RUN] Skip LLM call to {model}")
        return {"text": "[DRY_RUN MOCK RESPONSE]", "usage": {"total_tokens": 0}}

    cache_key = get_cache_key(model, messages)
    cached = safe_redis_execute(redis_client.get, cache_key)
    if cached:
        try:
            return json.loads(cached)
        except:
            pass

    # Thử từng model theo priority
    models_to_try = DEFAULT_MODEL_PRIORITY if model not in DEFAULT_MODEL_PRIORITY else [model] + [m for m in DEFAULT_MODEL_PRIORITY if m != model]

    last_error = None
    for try_model in models_to_try:
        try:
            kwargs = {
                "model": try_model,
                "messages": messages,
                "temperature": 0.2,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = litellm.completion(**kwargs)
            raw_text = response.choices[0].message.content

            if response_format and response_format.get("type") == "json_object":
                try:
                    data = json.loads(raw_text)
                except json.JSONDecodeError:
                    print("⚠️ [JSON_REPAIR] Attempting repair...")
                    repaired = repair_json(raw_text)
                    data = json.loads(repaired)
                result = data
            else:
                result = {"text": raw_text}

            # Ghi cache
            safe_redis_execute(redis_client.setex, cache_key, 86400, json.dumps(result))

            # Ghi event tính cost
            if project_id and response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                cost = calculate_cost(try_model, prompt_tokens, completion_tokens)
                # Ghi vào outbox để CostTracker xử lý
                from Core.event_bus import publish_event
                with db.client.start_session() as session:
                    with session.start_transaction():
                        publish_event(
                            session=session,
                            event_type="LLM_CALL_COMPLETED",
                            publisher=worker_name,
                            payload={
                                "project_id": project_id,
                                "model": try_model,
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": completion_tokens,
                                "total_tokens": response.usage.total_tokens,
                                "cost": cost,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
            return result

        except Exception as e:
            last_error = e
            if "quota" in str(e).lower() or "exceeded" in str(e).lower():
                print(f"⚠️ [LITELLM] Quota exceeded for {try_model}, trying next...")
                continue
            else:
                # Lỗi khác thì break không fallback
                raise e

    raise last_error or Exception("No model available in priority list")
