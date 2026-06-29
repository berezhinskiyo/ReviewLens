"""Тарифные планы и их лимиты в одном месте."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    code: str
    title: str
    price_kopecks: int
    # None == безлимит
    analyses_limit: int | None


# free: 1 бесплатный анализ при регистрации
FREE = Plan(code="free", title="Бесплатный", price_kopecks=0, analyses_limit=1)
STARTER = Plan(code="starter", title="Старт", price_kopecks=99000, analyses_limit=10)
PRO = Plan(code="pro", title="Безлимит", price_kopecks=299000, analyses_limit=None)

PLANS: dict[str, Plan] = {p.code: p for p in (FREE, STARTER, PRO)}

# Платные планы, доступные к покупке
PURCHASABLE = {STARTER.code, PRO.code}


def get_plan(code: str) -> Plan:
    return PLANS.get(code, FREE)


def limit_for_plan(code: str) -> int | None:
    return get_plan(code).analyses_limit
