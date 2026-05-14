import logging
import sys
import json
from typing import Any
import os
import logfire


class JSONFormatter(logging.Formatter):
    """Simple JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_object: dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
        }
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_object)


def configure_logging(level: str = "INFO") -> None:
    """Configure application-wide logging and Logfire instrumentation."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers = [handler]

    # Initialize Logfire if available (API key can be in env or default config)
    try:
        logfire.configure()
        # Instrument common libraries
        try:
            logfire.instrument_asyncpg()
        except Exception:
            pass
        try:
            logfire.instrument_logging()
        except Exception:
            pass
    except Exception:
        # Logfire is optional; continue without it
        pass
