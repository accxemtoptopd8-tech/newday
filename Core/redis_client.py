# Circuit breaker cho Redis
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

# Hàm lấy cache (dùng chung)
def get_cache(key: str) -> Optional[str]:
    try:
        return safe_redis_call(redis_client.get, key)
    except:
        return None

def set_cache(key: str, value: str, ttl: int = 86400):
    try:
        safe_redis_call(redis_client.setex, key, ttl, value)
    except:
        pass
