from slowapi.util import get_remote_address
from slowapi import Limiter
from app.config import REDIS_URI

# Initialize limiter (IP-based by default)
limiter = Limiter(key_func=get_remote_address, 
                  storage_uri=REDIS_URI, 
                  in_memory_fallback_enabled=True, 
                  default_limits=["30/minute"])