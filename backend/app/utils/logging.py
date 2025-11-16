"""Structured logging configuration"""

import logging
import sys
from typing import Any
import structlog
from pythonjsonlogger import jsonlogger


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure structured logging with JSON output

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


# JSON formatter for standard logging
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)

        # Add custom fields
        log_record['service'] = 'recommendation-engine'
        log_record['environment'] = 'production'  # Should come from env var
        log_record['logger_name'] = record.name

        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)


def configure_uvicorn_logging():
    """Configure Uvicorn logging to use JSON format"""

    # Get uvicorn loggers
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_error = logging.getLogger("uvicorn.error")

    # Create JSON formatter
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )

    # Configure handlers
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    uvicorn_access.handlers = [handler]
    uvicorn_error.handlers = [handler]
