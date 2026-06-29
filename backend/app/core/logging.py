import sys

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """Логи в JSON на проде, человекочитаемые в dev."""
    logger.remove()
    serialize = settings.env != "development"
    logger.add(
        sys.stdout,
        serialize=serialize,
        level="DEBUG" if settings.env == "development" else "INFO",
        backtrace=False,
        diagnose=False,
    )


__all__ = ["logger", "setup_logging"]
