# ==================================================
# FILE: ./Workers/strategy_generator.py
# ==================================================
import time
import os
import json
from datetime import datetime, timezone, timedelta
from Core.base_worker import BaseWorker
from Core.event_worker import EventWorker
from Core.mongo import db
from Core.redis_client import redis_client, safe_redis_execute
from Core.litellm_client import safe_llm_call

RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"

class StrategyGeneratorWorker(EventWorker):
    def __init__(self):
        super().__init__("strategy_generator")
        self.interested_events = ["PHASE_1_COMPLETED", "FORCE_PHASE2_EARLY"]
        self.default_model = "openrouter/openai/gpt-4o-mini"

    def check_and_reserve_budget(self, project_id: str, cost_limit: float = 0.05) -> bool:
        budget_key = f"project_budget:{project_id}"
        current_budget = redis_client.get(budget_key)
        if current_budget and float(current_budget) < cost_limit:
            return False
        now = datetime.now(timezone.utc)
        try:
            with db.client.start_session() as session:
                with session.start_transaction():
                    db.budget_reservations.insert_one({
                        "project_id": project_id,
                        "worker_name": self.name,
                        "reserved_amount": cost_limit,
                        "created_at": now
                    }, session=session)
            return True
        except Exception:
            return False

    def process_event(self, event: dict):
        payload = event["payload"]
        project_id = payload.get("project_id")
        print(f"🚀 [STRATEGY] Tiếp nhận sản xuất bản vẽ chiến lược cho Dự án ID: {project_id}")

        if not self.validate_project_id(project_id):
            print(f"❌ [STRATEGY] Vi phạm định dạng Project ID: {project_id}")
            return

        lock_key = f"project_lock:{project_id}:{self.name}"
        if not redis_client.set(lock_key, self.instance_id, ex=300, nx=True):
            print(f"⏳ [STRATEGY] Dự án {project_id} đang được xử lý bởi một instance khác. Bỏ qua.")
            return

        if not self.check_and_reserve_budget(project_id):
            print(f"🚨 [STRATEGY] Từ chối xử lý! Dự án {project_id} không đủ định biên ngân sách an toàn.")
            db.sos_queue.insert_one({
                "project_id": project_id,
                "worker_name": self.name,
                "error_message": "Budget reservation failed / Exhausted",
                "status": "pending",
                "created_at": datetime.now(timezone.utc)
            })
            redis_client.delete(lock_key)
            return

        try:
            p1_data = db.product_phase_1.find_one({"project_id": project_id})
            raw_prod = db.raw_products.find_one({"project_id": project_id})
            if not p1_data or not raw_prod:
                print(f"⚠️ [STRATEGY] Thiếu điều kiện tiên quyết dữ liệu đầu vào cho ID: {project_id}")
                redis_client.delete(lock_key)
                return

            insights = p1_data.get("refined_insights", {})
            model = raw_prod.get("model_assignment", self.default_model)
            if not model.startswith("openrouter/"):
                print(f"⚠️ [STRATEGY] Model {model} không phải OpenRouter, chuyển về {self.default_model}")
                model = self.default_model

            system_prompt = (
                "Bạn là Giám đốc Chiến lược Tăng trưởng tối cao. "
                "Dựa trên insight đầu vào, hãy lập kế hoạch thâm nhập thị trường hoàn chỉnh. "
                "Bạn bắt buộc phải trả về định dạng cấu trúc JSON chính xác tuyệt đối gồm: "
                "insights (mảng các chuỗi phân tích sâu), pain_keywords (mảng từ khóa nỗi đau của khách hàng), "
                "value_props (mảng các thông điệp giá trị cốt lõi đánh gục khách hàng)."
            )
            user_prompt = f"Insight nền tảng: {json.dumps(insights)}. Hãy thiết kế bản vẽ chiến lược kinh doanh."

            print(f"🧠 [STRATEGY] Gọi LLM với model: {model}")
            strategy_output = safe_llm_call(model, [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], response_format={"type": "json_object"}, project_id=project_id, worker_name=self.name)

            now = datetime.now(timezone.utc)

            with db.client.start_session() as session:
                with session.start_transaction():
                    # 1. Lưu bản vẽ chiến lược
                    db.strategy_reports.update_one(
                        {"project_id": project_id},
                        {"$set": {
                            "project_name": raw_prod.get("project_name"),
                            "status": "pending_approval",
                            "strategy_data": strategy_output,
                            "created_at": now,
                            "updated_at": now
                        }},
                        upsert=True,
                        session=session
                    )
                    
                    # 2. Xóa lệnh đóng băng ngân sách
                    db.budget_reservations.delete_many({"project_id": project_id, "worker_name": self.name}, session=session)

                    # 3. KỶ LUẬT LÕI: Phát lệnh báo cáo hoàn thành cho T0
                    db.outbox_events.insert_one({
                        "event_type": "STRATEGY_GENERATED",
                        "publisher": self.name,
                        "payload": {
                            "project_id": project_id,
                            "project_name": raw_prod.get("project_name", "Unknown Project")
                        },
                        "status": "pending",
                        "retry_count": 0,
                        "created_at": now,
                        "next_retry_at": now,
                        "claim_timeout": 300
                    }, session=session)

            print(f"✅ [STRATEGY] Đã xuất bản đồ chiến lược thành công cho Dự án {project_id}. Đã bắn Event gọi T0.")

        except Exception as e:
            print(f"🚨 [STRATEGY] Trục trặc hệ thống xử lý mô hình chiến lược: {e}")
            db.sos_queue.insert_one({
                "project_id": project_id,
                "worker_name": self.name,
                "error_message": f"Execution crash: {str(e)}",
                "status": "pending",
                "created_at": datetime.now(timezone.utc)
            })
        finally:
            redis_client.delete(lock_key)

    def run_daemon_loop(self):
        print(f"🤖 Worker {self.name} (Chiến lược gia) đã trực chiến, chờ lệnh kích nổ...")
        self.start_heartbeat()
        wait = 1
        while not self.shutdown_requested:
            now = datetime.now(timezone.utc)
            event = db.outbox_events.find_one_and_update(
                {
                    "status": "pending",
                    "event_type": {"$in": self.interested_events},
                    "next_retry_at": {"$lte": now}
                },
                {"$set": {
                    "status": "processing",
                    "claimed_by": self.instance_id,
                    "claimed_at": now,
                    "claim_timeout": now + timedelta(minutes=30)
                }},
                sort=[("created_at", 1)]
            )
            if not event:
                time.sleep(wait)
                wait = min(10, wait * 2)
                if RUN_ONCE:
                    print("🏁 [RUN_ONCE] Không còn event, thoát.")
                    break
                continue
            wait = 1
            try:
                self.process_event(event)
                db.outbox_events.update_one(
                    {"_id": event["_id"]},
                    {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc)}}
                )
            except Exception as e:
                retry_count = event.get("retry_count", 0) + 1
                if retry_count >= event.get("max_retry", 3):
                    db.dead_events.insert_one({"original_event": event, "error": str(e), "failed_at": datetime.now(timezone.utc)})
                    db.outbox_events.update_one({"_id": event["_id"]}, {"$set": {"status": "dead"}})
                else:
                    db.outbox_events.update_one(
                        {"_id": event["_id"]},
                        {"$inc": {"retry_count": 1}, "$set": {"status": "pending", "claimed_by": None}}
                    )
            if RUN_ONCE:
                print("🏁 [RUN_ONCE] Đã xử lý một event, thoát.")
                break
        self.stop()

if __name__ == "__main__":
    worker = StrategyGeneratorWorker()
    worker.run_daemon_loop()
