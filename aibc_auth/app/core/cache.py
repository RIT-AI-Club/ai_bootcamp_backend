"""
Production-grade Redis caching layer for performance optimization
"""

import json
import pickle
from typing import Any, Optional, Union, List, Dict
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio import Redis
import logging
from functools import wraps
import hashlib
import ssl
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """Production-grade Redis cache manager with connection pooling"""

    def __init__(self):
        self._redis: Optional[Redis] = None
        self._connection_pool = None

    async def get_redis(self) -> Redis:
        """Get Redis connection with connection pooling"""
        if self._redis is None:
            try:
                # Create connection pool for production scalability
                pool_kwargs = {
                    "host": settings.REDIS_HOST,
                    "port": settings.REDIS_PORT,
                    "db": settings.REDIS_DB,
                    "decode_responses": False,  # Handle binary data
                    "max_connections": 20,      # Production connection limit
                    "retry_on_timeout": True,
                    "socket_connect_timeout": 5,
                    "socket_timeout": 5,
                    "health_check_interval": 30
                }

                # Add password only if provided (production security)
                if settings.REDIS_PASSWORD:
                    pool_kwargs["password"] = settings.REDIS_PASSWORD

                # Add SSL support for production environments
                if settings.ENVIRONMENT == "production":
                    pool_kwargs["ssl"] = True
                    pool_kwargs["ssl_cert_reqs"] = ssl.CERT_REQUIRED
                    pool_kwargs["ssl_check_hostname"] = True

                self._connection_pool = redis.ConnectionPool(**pool_kwargs)
                self._redis = Redis(connection_pool=self._connection_pool)

                # Test connection
                await self._redis.ping()
                logger.info("Redis cache connection established")

            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                # Graceful degradation - continue without cache
                self._redis = None

        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with error handling"""
        redis_client = await self.get_redis()
        if not redis_client:
            return None

        try:
            value = await redis_client.get(key)
            if value is None:
                return None

            # Try JSON first (for simple data), then pickle (for complex objects)
            try:
                return json.loads(value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return pickle.loads(value)

        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache with TTL"""
        redis_client = await self.get_redis()
        if not redis_client:
            return False

        try:
            # Serialize data efficiently
            if isinstance(value, (dict, list, str, int, float, bool)):
                serialized = json.dumps(value, default=str)
            else:
                serialized = pickle.dumps(value)

            await redis_client.setex(key, expire, serialized)
            return True

        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        redis_client = await self.get_redis()
        if not redis_client:
            return False

        try:
            await redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        redis_client = await self.get_redis()
        if not redis_client:
            return 0

        try:
            keys = await redis_client.keys(pattern)
            if keys:
                return await redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return 0

# Global cache manager instance
cache_manager = CacheManager()

def cache_key(*args, **kwargs) -> str:
    """Generate consistent cache key from arguments"""
    key_parts = []

    # Add positional args
    for arg in args:
        if hasattr(arg, 'hex'):  # UUID objects
            key_parts.append(arg.hex)
        else:
            key_parts.append(str(arg))

    # Add keyword args
    for k, v in sorted(kwargs.items()):
        if hasattr(v, 'hex'):  # UUID objects
            key_parts.append(f"{k}:{v.hex}")
        else:
            key_parts.append(f"{k}:{v}")

    # Create hash for consistent length
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

def cached(expire: int = 3600, key_prefix: str = "default"):
    """Production-grade caching decorator with graceful degradation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_str = f"{key_prefix}:{cache_key(*args, **kwargs)}"

            # Try to get from cache
            cached_result = await cache_manager.get(cache_key_str)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key_str}")
                return cached_result

            # Cache miss - execute function
            logger.debug(f"Cache miss: {cache_key_str}")
            result = await func(*args, **kwargs)

            # Cache the result
            await cache_manager.set(cache_key_str, result, expire)

            return result
        return wrapper
    return decorator

async def invalidate_user_cache(user_id: str):
    """Invalidate all cache entries for a specific user"""
    patterns = [
        f"user_progress:{user_id}:*",
        f"user_dashboard:{user_id}:*",
        f"user_summary:{user_id}:*"
    ]

    for pattern in patterns:
        await cache_manager.delete_pattern(pattern)

    logger.info(f"Invalidated cache for user: {user_id}")

async def invalidate_pathway_cache(pathway_id: str):
    """Invalidate pathway-related cache entries"""
    patterns = [
        f"pathway:{pathway_id}:*",
        f"pathway_modules:{pathway_id}:*"
    ]

    for pattern in patterns:
        await cache_manager.delete_pattern(pattern)

    logger.info(f"Invalidated cache for pathway: {pathway_id}")