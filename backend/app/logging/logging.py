"""
Infralytix — Structured Logging Setup.

Configures Python's standard logging module with:
  - JSON formatter for production (machine-parseable, works with CloudWatch/Datadog)
  - Human-readable formatter for development (colored, easy to read)
  - Log level control via settings
  - Request ID support (added per-request via middleware)

Design Decisions:
    - Use stdlib `logging` — no additional dependency required
    - JSON format in production enables log aggregation and alerting
    - Single `setup_logging()` call during app lifespan startup
    - All loggers use the same handler to avoid duplicate log lines
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """
    Format log records as single-line JSON objects.

    Example output:
        {"timestamp": "2025-01-15T10:30:45Z", "level": "INFO",
         "logger": "app.api.v1.endpoints.health", "message": "Health check called",
         "module": "health", "line": 42}
    """

    # Fields we want to include in every log line
    _ALWAYS_INCLUDED: frozenset[str] = frozenset(
        {"timestamp", "level", "logger", "message", "module", "line"}
    )

    def format(self, record: logging.LogRecord) -> str:  # noqa: ANN201
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": self.formatMessage(record),
            "module": record.module,
            "line": record.lineno,
        }

        # Include exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include any extra fields passed via logger.info("msg", extra={...})
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key not in self._ALWAYS_INCLUDED:
                log_entry[key] = value

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """
    Human-readable formatter for development with optional colors.

    Example output:
        2025-01-15 10:30:45 | INFO     | app.health:42 | Health check called
    """

    # ANSI color codes
    _COLORS: dict[str, str] = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: ANN201
        color = self._COLORS.get(record.levelname, self._COLORS["RESET"])
        reset = self._COLORS["RESET"]

        timestamp = datetime.fromtimestamp(record.created, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
        level = f"{color}{record.levelname:<8}{reset}"
        location = f"{record.name}:{record.lineno}"
        message = self.formatMessage(record)

        formatted = f"{timestamp} | {level} | {location} | {message}"

        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """
    Configure the root logger for the application.

    Called once during application startup (lifespan context).

    Args:
        log_level:  Minimum severity to log. One of DEBUG/INFO/WARNING/ERROR/CRITICAL.
        log_format: Output format. "json" for production, "text" for development.
    """
    # Remove all existing handlers (avoids duplicate log lines from uvicorn defaults)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Build handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JSONFormatter() if log_format == "json" else TextFormatter()
    )

    # Configure root logger
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(handler)

    # Quiet down noisy third-party loggers
    for noisy_logger in ("uvicorn.access", "uvicorn.error", "sqlalchemy.engine"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    # Re-enable uvicorn.error at ERROR level minimum
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)


def get_logger(name: str) -> logging.Logger:
    """
    Retrieve a named logger.

    Usage:
        logger = get_logger(__name__)
        logger.info("Processing request", extra={"user_id": 42, "action": "create"})

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        A configured logging.Logger instance.
    """
    return logging.getLogger(name)
