import threading
import time
import os
from Core.base_worker import BaseWorker
from Core.redis_client import redis_client

class EventWorker(BaseWorker):
    def __init__(self, name: str):
        super().__init__(name)
        self.shutdown_requested = False
        self.instance_id = f"{self.name}_{os.getpid()}_{int(time.time())}"

    def start_heartbeat(self):
        heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        print(f"💚 [HEARTBEAT] Đã kích hoạt Thread tuần tra độc lập cho {self.instance_id}")

    def _heartbeat_loop(self):
        while not self.shutdown_requested:
            try:
                redis_client.set(f"worker_heartbeat:{self.name}", self.instance_id, ex=15)
            except Exception as e:
                print(f"⚠️ [HEARTBEAT] Lỗi ghi tín hiệu nhịp tim lên Redis: {e}")
            time.sleep(5)

    def stop(self):
        print(f"🛑 [SHUTDOWN] Đang kích hoạt quy trình dọn dẹp hạ tầng cho {self.name}...")
        self.shutdown_requested = True

    # ========== PHƯƠNG THỨC MỚI ==========
    def is_worker_alive(self, worker_name: str) -> bool:
        """Kiểm tra heartbeat của worker khác"""
        key = f"worker_heartbeat:{worker_name}"
        return bool(redis_client.get(key))
