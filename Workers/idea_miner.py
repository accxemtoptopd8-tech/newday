import time
import os
import json
from datetime import datetime, timezone
from Core.base_worker import BaseWorker
from Core.event_worker import EventWorker
from Core.mongo import db
from Core.litellm_client import safe_llm_call
import litellm

class IdeaMinerWorker(EventWorker):
    def __init__(self):
        super().__init__("idea_miner")
        self.interested_events = ["PROJECT_CREATED", "RESET_IDEA_MINING"]

    def execute_continuation_loop(self, model: str, system_prompt: str, user_prompt: str, project_id: str) -> dict:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        print(f"🤖 [LLM] Đang kích hoạt cuộc gọi phân tích tri thức bằng model: {model}")
        response_data = safe_llm_call(model, messages, response_format={"type": "json_object"}, project_id=project_id, worker_name=self.name)
        if "is_truncated" in response_data and response_data["is_truncated"] is True:
            print("🔄 [CONTINUATION] Phát hiện AI bị đứt dòng giữa chừng! Đang kích hoạt lệnh nối dòng...")
            messages.append({"role": "assistant", "content": json.dumps(response_data)})
            messages.append({"role": "user", "content": "Tiếp tục hoàn thiện cấu trúc JSON đang dở dang từ trường cuối cùng, không viết lại từ đầu."})
            second_response = safe_llm_call(model, messages, response_format={"type": "json_object"}, project_id=project_id, worker_name=self.name)
            if isinstance(second_response, dict):
                response_data.update(second_response)
        return response_data

    def process_event(self, event: dict):
        payload = event["payload"]
        project_id = payload.get("project_id")
        print(f"🚀 [IDEA_MINER] Tiếp nhận khai thác ý tưởng cho Dự án ID: {project_id}")

        if not self.validate_project_id(project_id):
            print(f"❌ [IDEA_MINER] Project ID không hợp lệ (Vi phạm an toàn Regex): {project_id}")
            return

        product_doc = db.raw_products.find_one({"project_id": project_id})
        if not product_doc:
            print(f"⚠️ [IDEA_MINER] Không tìm thấy dữ liệu raw_product cho ID: {project_id}")
            return

        system_prompt = (
            "Bạn là Giám đốc Nghiên cứu Thị trường cấp cao. Nhiệm vụ của bạn là bóc tách ý tưởng sản phẩm thô "
            "thành các Insight cốt lõi. Bạn bắt buộc phải trả về định dạng JSON chứa các trường sau: "
            "core_concept (chuỗi), target_audiences (mảng), market_pain_points (mảng), unique_selling_points (mảng)."
        )
        user_prompt = f"Ý tưởng thô: {product_doc.get('raw_input', '')}. Hãy bóc tách cấu trúc."

        model = product_doc.get("model_assignment", "gpt-3.5-turbo")
        now = datetime.now(timezone.utc)
        db.job_run_log.update_one(
            {"project_id": project_id, "worker_name": self.name},
            {"$set": {"status": "running", "started_at": now}},
            upsert=True
        )

        try:
            insights = self.execute_continuation_loop(model, system_prompt, user_prompt, project_id)

            with db.client.start_session() as session:
                with session.start_transaction():
                    db.product_phase_1.update_one(
                        {"project_id": project_id},
                        {"$set": {
                            "project_name": product_doc.get("project_name"),
                            "refined_insights": insights,
                            "processed_at": now
                        }},
                        upsert=True,
                        session=session
                    )
                    db.raw_products.update_one(
                        {"project_id": project_id},
                        {"$set": {"status": "completed", "phase1_ended_at": now}},
                        session=session
                    )
                    db.outbox_events.insert_one({
                        "event_type": "PHASE_1_COMPLETED",
                        "publisher": self.name,
                        "payload": {
                            "project_id": project_id,
                            "completed_at": now.isoformat()
                        },
                        "status": "pending",
                        "retry_count": 0,
                        "created_at": now,
                        "next_retry_at": now,
                        "claim_timeout": 300
                    }, session=session)
                    db.job_run_log.update_one(
                        {"project_id": project_id, "worker_name": self.name},
                        {"$set": {"status": "success", "ended_at": datetime.now(timezone.utc)}},
                        session=session
                    )
            print(f"🎉 [IDEA_MINER] Đã hoàn thành sơ chế tri thức cho Dự án {project_id}. Đã publish PHASE_1_COMPLETED.")

        except Exception as e:
            print(f"🚨 [IDEA_MINER] Crash luồng phân tích AI: {e}")
            db.job_run_log.update_one(
                {"project_id": project_id, "worker_name": self.name},
                {"$set": {"status": "failed", "error_log": str(e), "failed_at": datetime.now(timezone.utc)}}
            )
            db.sos_queue.insert_one({
                "project_id": project_id,
                "worker_name": self.name,
                "error_message": str(e),
                "status": "pending",
                "created_at": datetime.now(timezone.utc)
            })

    def run_daemon_loop(self):
        print(f"🤖 Worker {self.name} đã lên đèn, sẵn sàng bóc tách tri thức nhân loại...")
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
                    "claim_timeout": now + os.timedelta(minutes=5)
                }},
                sort=[("created_at", 1)]
            )
            if not event:
                time.sleep(wait)
                wait = min(10, wait * 2)
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
        self.stop()

if __name__ == "__main__":
    worker = IdeaMinerWorker()
    worker.run_daemon_loop()
