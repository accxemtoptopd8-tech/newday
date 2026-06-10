import redis
import json
import time
from bson import ObjectId
from datetime import datetime
from Core.config import REDIS_URL

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

class CustomJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.dict_to_object, *args, **kwargs)
    def dict_to_object(self, d):
        for k, v in d.items():
            if isinstance(v, str):
                try:
                    d[k] = datetime.fromisoformat(v)
                except ValueError:
                    pass
        return d

print("🔄 Đang thiết lập kết nối Redis với Exponential Backoff...")
redis_client = redis.Redis.from_url(
    REDIS_URL, 
    decode_responses=True,
    retry_on_timeout=True,
    socket_timeout=5,
    socket_connect_timeout=5
)

def safe_redis_execute(func, *args, **kwargs):
    retries = 5
    delay = 2
    for i in range(retries):
        try:
            return func(*args, **kwargs)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            if i == retries - 1:
                raise e
            print(f"⚠️ Thất bại kết nối Redis. Đang thử lại sau {delay} giây... (Lần {i+1}/{retries})")
            time.sleep(delay)
            delay *= 2

# ============= Circuit Breaker =============
class RedisCircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.is_open = False

    def call(self, func, *args, **kwargs):
        if self.is_open:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.is_open = False
                self.failure_count = 0
            else:
                raise redis.ConnectionError("Redis circuit breaker is open")
        try:
            result = func(*args, **kwargs)
            self.failure_count = 0
            return result
        except (redis.ConnectionError, redis.TimeoutError) as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.is_open = True
            raise e

_breaker = RedisCircuitBreaker()

def safe_redis_call(func, *args, **kwargs):
    return _breaker.call(func, *args, **kwargs)

def get_cache(key: str):
    try:
        return safe_redis_call(redis_client.get, key)
    except:
        return None

def set_cache(key: str, value: str, ttl: int = 86400):
    try:
        safe_redis_call(redis_client.setex, key, ttl, value)
    except:
        pass
