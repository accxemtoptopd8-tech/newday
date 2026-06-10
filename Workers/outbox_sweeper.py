import time
from datetime import datetime, timezone, timedelta
from Core.base_worker import BaseWorker
from Core.mongo import db
from Core.redis_client import redis_client

class OutboxSweeper(BaseWorker):
    def __init__(self):
        super().__init__("outbox_sweeper")

    def sweep_stale_events(self):
        now = datetime.now(timezone.utc)
        print("📦 [OUTBOX_SWEEPER] Đang kiểm tra các sự kiện bị kẹt...")

        stale_events = db.outbox_events.find({
            "status": "processing",
            "claim_timeout": {"$lte": now}
        })

        for event in stale_events:
            claimed_by = event.get("claimed_by")
            if claimed_by:
                heartbeat_key = f"worker_heartbeat:{claimed_by}"
                if redis_client.get(heartbeat_key):
                    new_timeout = now + timedelta(minutes=5)
                    db.outbox_events.update_one(
                        {"_id": event["_id"]},
                        {"$set": {"claim_timeout": new_timeout}}
                    )
                    print(f"🔄 [OUTBOX_SWEEPER] Gia hạn timeout cho event {event.get('event_type')} (worker {claimed_by} vẫn sống)")
                    continue

            retry_count = event.get("retry_count", 0) + 1
            max_retry = event.get("max_retry", 3)
            if retry_count >= max_retry:
                db.dead_events.insert_one({
                    "original_event": event,
                    "error": "Claim timeout exceeded maximum retries and worker dead",
                    "failed_at": now
                })
                db.outbox_events.update_one({"_id": event["_id"]}, {"$set": {"status": "dead"}})
                print(f"💀 [OUTBOX_SWEEPER] Event {event.get('event_type')} đã chết sau {retry_count} lần retry.")
            else:
                db.outbox_events.update_one(
                    {"_id": event["_id"]},
                    {"$inc": {"retry_count": 1}, "$set": {"status": "pending", "claimed_by": None}}
                )
                print(f"🔄 [OUTBOX_SWEEPER] Đã reset event {event.get('event_type')} (retry {retry_count}/{max_retry})")

    def run_cron_loop(self):
        print("🤖 Outbox Sweeper đã trực chiến. Chu kỳ tuần tra: 30 giây.")
        while True:
            try:
                self.sweep_stale_events()
            except Exception as e:
                print(f"❌ [OUTBOX_SWEEPER] Lỗi hệ thống: {e}")
            time.sleep(30)

if __name__ == "__main__":
    sweeper = OutboxSweeper()
    sweeper.run_cron_loop()
