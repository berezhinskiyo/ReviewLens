"""Entrypoint воркера: python -m app.workers.worker."""

from rq import Worker

from app.core.logging import setup_logging
from app.workers.queue import analysis_queue, redis_conn


def main() -> None:
    setup_logging()
    worker = Worker([analysis_queue], connection=redis_conn)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
