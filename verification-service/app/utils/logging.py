import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_record.update(record.extra)

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def setup_logging(log_level: str = "INFO", json_format: bool = False) -> logging.Logger:
    """Configures structured root logging."""
    logger = logging.getLogger("freshguard")
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)

        if json_format:
            handler.setFormatter(JSONFormatter())
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s (%(module)s:%(lineno)d): %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


logger = setup_logging()
