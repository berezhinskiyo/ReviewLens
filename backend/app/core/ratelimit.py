"""Простой rate-limit на Redis (защита от подбора и автоматизированных атак).

Fail-open: при недоступности Redis запрос пропускается, чтобы не ронять сервис.
"""

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import logger

_redis: Redis | None = None


def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url)
    return _redis


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )


def rate_limit(scope: str, *, limit: int, window_seconds: int):
    """Фабрика FastAPI-зависимостей: не более `limit` запросов с IP за окно."""

    async def dependency(request: Request) -> None:
        ip = _client_ip(request)
        key = f"rl:{scope}:{ip}"
        try:
            redis = _get_redis()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window_seconds)
            if count > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Слишком много запросов. Попробуйте позже.",
                )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 — недоступность Redis не должна ронять auth
            logger.warning("ratelimit.unavailable", scope=scope, error=str(exc))

    return dependency
