"""RQ-задачи. RQ синхронный — внутри запускаем async через свой event loop."""

import asyncio
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.services.analysis import process_analysis


def run_analysis_task(analysis_id: str) -> None:
    """Точка входа RQ. Создаёт собственный engine/loop на время задачи."""
    setup_logging()
    logger.info("worker.task.start", analysis_id=analysis_id)
    asyncio.run(_run(analysis_id))


async def _run(analysis_id: str) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as db:
            await process_analysis(db, uuid.UUID(analysis_id))
    finally:
        await engine.dispose()
