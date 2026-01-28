import redis.asyncio as redis
from typing import Optional, Any
import json
from app.core.config import settings

# Redis client
redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get Redis client"""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client


async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


# Cache functions
async def cache_set(key: str, value: Any, expire: int = 3600):
    """Set cache with expiration (default 1 hour)"""
    client = await get_redis()
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    await client.setex(key, expire, value)


async def cache_get(key: str) -> Optional[Any]:
    """Get cache value"""
    client = await get_redis()
    value = await client.get(key)
    if value:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return None


async def cache_delete(key: str):
    """Delete cache"""
    client = await get_redis()
    await client.delete(key)


async def cache_delete_pattern(pattern: str):
    """Delete all keys matching pattern"""
    client = await get_redis()
    keys = await client.keys(pattern)
    if keys:
        await client.delete(*keys)


# Verification code storage
async def store_verification_code(email: str, code: str, expire_minutes: int = 15):
    """Store email verification code"""
    await cache_set(f"verification:{email}", code, expire_minutes * 60)


async def get_verification_code(email: str) -> Optional[str]:
    """Get verification code"""
    return await cache_get(f"verification:{email}")


async def delete_verification_code(email: str):
    """Delete verification code"""
    await cache_delete(f"verification:{email}")


# Password reset token storage
async def store_reset_token(email: str, token: str, expire_minutes: int = 30):
    """Store password reset token"""
    await cache_set(f"reset_token:{token}", email, expire_minutes * 60)


async def get_reset_token_email(token: str) -> Optional[str]:
    """Get email from reset token"""
    return await cache_get(f"reset_token:{token}")


async def delete_reset_token(token: str):
    """Delete reset token"""
    await cache_delete(f"reset_token:{token}")


# User online status
async def set_user_online(user_id: int):
    """Mark user as online"""
    await cache_set(f"online:{user_id}", "1", 300)  # 5 minutes


async def is_user_online(user_id: int) -> bool:
    """Check if user is online"""
    value = await cache_get(f"online:{user_id}")
    return value is not None


# Rate limiting
async def check_rate_limit(key: str, limit: int = 60, window: int = 60) -> bool:
    """
    Check rate limit
    Returns True if within limit, False if exceeded
    """
    client = await get_redis()
    current = await client.incr(key)
    if current == 1:
        await client.expire(key, window)
    return current <= limit