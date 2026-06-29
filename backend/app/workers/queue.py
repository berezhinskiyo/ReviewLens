"""Подключение к Redis и очередь RQ."""

from redis import Redis
from rq import Queue

from app.core.config import settings

redis_conn = Redis.from_url(settings.redis_url)
analysis_queue = Queue("analyses", connection=redis_conn, default_timeout=600)


def enqueue_analysis(analysis_id: str) -> None:
    analysis_queue.enqueue("app.workers.tasks.run_analysis_task", analysis_id)
