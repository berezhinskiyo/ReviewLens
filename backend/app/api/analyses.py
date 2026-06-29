import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import Analysis, User
from app.db.session import get_db
from app.schemas.api import AnalysisListItem, AnalysisOut, CreateAnalysisRequest
from app.scrapers.registry import detect_marketplace
from app.scrapers.base import ScraperError
from app.services.subscription import can_run_analysis
from app.workers.queue import enqueue_analysis

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


@router.post("", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    payload: CreateAnalysisRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisOut:
    # Проверяем, что URL валиден и маркетплейс поддерживается
    try:
        marketplace = detect_marketplace(payload.url)
    except ScraperError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if marketplace != "wb":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пока поддерживается только Wildberries. Ozon — скоро.",
        )

    # Проверяем лимит тарифа
    if not can_run_analysis(user):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Исчерпан лимит анализов по вашему тарифу. Оформите подписку.",
        )

    analysis = Analysis(user_id=user.id, input_url=payload.url, status="pending")
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    enqueue_analysis(str(analysis.id))
    return AnalysisOut.model_validate(analysis)


@router.get("", response_model=list[AnalysisListItem])
async def list_analyses(
    limit: int = Query(default=10, le=50),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AnalysisListItem]:
    result = await db.execute(
        select(Analysis)
        .where(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [AnalysisListItem.model_validate(a) for a in result.scalars().all()]


@router.get("/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(
    analysis_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisOut:
    analysis = await db.get(Analysis, analysis_id)
    if analysis is None or analysis.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Анализ не найден")
    return AnalysisOut.model_validate(analysis)


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(
    analysis_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    analysis = await db.get(Analysis, analysis_id)
    if analysis is None or analysis.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Анализ не найден")
    await db.delete(analysis)
    await db.commit()
