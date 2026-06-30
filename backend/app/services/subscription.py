"""Логика тарифов и лимитов."""

from datetime import datetime, timezone

from app.core.plans import limit_for_plan
from app.db.models import User


def is_subscription_active(user: User) -> bool:
    if user.plan == "free":
        return True
    if user.subscription_until is None:
        return False
    return user.subscription_until > datetime.now(timezone.utc)


def effective_plan(user: User) -> str:
    """Если платная подписка истекла — откатываемся на free."""
    if user.plan != "free" and not is_subscription_active(user):
        return "free"
    return user.plan


def analyses_limit(user: User) -> int | None:
    if user.is_admin:
        return None  # администраторы — без лимитов
    return limit_for_plan(effective_plan(user))


def analyses_remaining(user: User) -> int | None:
    limit = analyses_limit(user)
    if limit is None:
        return None  # безлимит
    return max(0, limit - user.analyses_used_this_period)


def can_run_analysis(user: User) -> bool:
    remaining = analyses_remaining(user)
    return remaining is None or remaining > 0
