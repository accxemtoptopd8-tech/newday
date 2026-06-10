import time
from datetime import datetime, timezone, timedelta
from Core.base_worker import BaseWorker
from Core.event_worker import EventWorker
from Core.mongo import db
from Core.redis_client import redis_client
from Core.config import BUDGET_WARNING_THRESHOLD
from Core.event_bus import publish_event

class CostTrackerWorker(EventWorker):
    def __init__(self):
        super().__init__("cost_tracker")
        self.interested_events = ["LLM_CALL_COMPLETED"]

    def process_event(self, event: dict):
        payload = event["payload"]
        project_id = payload.get("project_id")
        cost = payload.get("cost", 0.0)
        model = payload.get("model", "unknown")

        if not project_id:
            return

        now = datetime.now(timezone.utc)
        today_key = now.strftime("daily_api_cost:%Y%m%d")
        project_budget_key = f"project_budget:{project_id}"

        # Cập nhật Redis
        redis_client.incrbyfloat(project_budget_key, cost)
        total_spent = float(redis_client.get(project_budget_key) or 0)

        redis_client.incrbyfloat(today_key, cost)
        daily_total = float(redis_client.get(today_key) or 0)

        # Lấy ngưỡng budget từ MongoDB
        budget_doc = db.project_budgets.find_one({"project_id": project_id})
        allocated = budget_doc.get("allocated_budget", 0.0) if budget_doc else 0.0

        if allocated > 0:
            spent_ratio = total_spent / allocated
            if spent_ratio >= BUDGET_WARNING_THRESHOLD:
                db.sos_queue.insert_one({
                    "project_id": project_id,
                    "worker_name": self.name,
                    "error_message": f"Budget warning: used {total_spent:.2f}/{allocated:.2f} ({spent_ratio:.1%})",
                    "status": "pending",
                    "created_at": now
                })
            if spent_ratio >= 1.0:
                with db.client.start_session() as session:
                    with session.start_transaction():
                        publish_event(
                            session,
                            "CRITICAL_ALERT",
                            self.name,
                            {
                                "project_id": project_id,
                                "worker_name": self.name,
                                "error": f"Budget exceeded: {total_spent:.2f} > {allocated:.2f}",
                                "timestamp": now.isoformat()
                            }
                        )

        # Ghi log
        db.model_usage_log.insert_one({
            "project_id": project_id,
            "worker_name": payload.get("worker_name", self.name),
            "model": model,
            "cost": cost,
            "prompt_tokens": payload.get("prompt_tokens"),
            "completion_tokens": payload.get("completion_tokens"),
            "timestamp": now
        })

        print(f"💰 [COST_TRACKER] Project {project_id} spent {cost:.6f}, total={total_spent:.2f}")

    def run_daemon_loop(self):
        print("💰 CostTrackerWorker đã trực chiến...")
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
                    "claim_timeout": now + timedelta(minutes=5)
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
    worker = CostTrackerWorker()
    worker.run_daemon_loop()
