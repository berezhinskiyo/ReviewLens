"""Зафиксированная Pydantic-схема результата анализа (analyses.result).

Эти типы — контракт между LLM-пайплайном, API и фронтендом.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ProductInfo(BaseModel):
    title: str | None = None
    brand: str | None = None
    rating: float | None = None
    reviews_analyzed: int = 0


class Complaint(BaseModel):
    topic: str
    frequency: int = 0
    severity: Literal["low", "medium", "high"] = "medium"
    description: str = ""
    sample_quotes: list[str] = Field(default_factory=list)


class Praise(BaseModel):
    topic: str
    frequency: int = 0
    description: str = ""
    sample_quotes: list[str] = Field(default_factory=list)


class Opportunity(BaseModel):
    category: Literal["product", "card", "infographic", "description"]
    title: str
    rationale: str = ""


class AnalysisResult(BaseModel):
    summary: str = ""
    product_info: ProductInfo = Field(default_factory=ProductInfo)
    complaints: list[Complaint] = Field(default_factory=list)
    praises: list[Praise] = Field(default_factory=list)
    opportunities: list[Opportunity] = Field(default_factory=list)
    demographic_hints: str = ""
    generated_at: str = ""
