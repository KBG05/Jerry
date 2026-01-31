"""Logging configuration for the application."""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict

from app.core.config import get_settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = getattr(record, "request_id")
        if hasattr(record, "method"):
            log_data["method"] = getattr(record, "method")
        if hasattr(record, "path"):
            log_data["path"] = getattr(record, "path")
        if hasattr(record, "status_code"):
            log_data["status_code"] = getattr(record, "status_code")
        if hasattr(record, "duration"):
            log_data["duration_ms"] = getattr(record, "duration")
        if hasattr(record, "client_ip"):
            log_data["client_ip"] = getattr(record, "client_ip")

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Custom text formatter for human-readable logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as text."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        base_msg = f"[{timestamp}] {record.levelname:8s} | {record.name:20s} | {record.getMessage()}"

        # Add request details if available
        if hasattr(record, "method") and hasattr(record, "path"):
            base_msg += f" | {getattr(record, 'method')} {getattr(record, 'path')}"
        if hasattr(record, "status_code"):
            base_msg += f" | Status: {getattr(record, 'status_code')}"
        if hasattr(record, "duration"):
            base_msg += f" | {getattr(record, 'duration'):.2f}ms"

        if record.exc_info:
            base_msg += f"\n{self.formatException(record.exc_info)}"

        return base_msg


def setup_logging() -> None:
    """Configure application logging."""
    settings = get_settings()

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level.upper()))

    # Set formatter based on configuration
    if settings.log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Set levels for third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
