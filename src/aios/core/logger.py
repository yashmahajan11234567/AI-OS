"""
Structured Logger for AI-OS Hermes Kernel.

Provides structured logging with context, correlation IDs, and event bus integration.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from aios.events.bus import get_event_bus
from aios.events.types import Event

logger = logging.getLogger("aios")


@dataclass
class LogContext:
    """Context for structured logging."""

    correlation_id: str | None = None
    service: str = "unknown"
    operation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "service": self.service,
            "operation": self.operation,
            **self.metadata,
        }


class StructuredLogger:
    """
    Structured logger with correlation ID support and event bus integration.

    Features:
    - JSON structured logging
    - Correlation ID propagation
    - Service-scoped loggers
    - Event bus integration for log events
    - Multiple output formats
    """

    def __init__(
        self,
        name: str = "aios",
        level: int = logging.INFO,
        json_format: bool = True,
        log_file: Path | None = None,
        event_bus_integration: bool = True,
    ):
        """
        Initialize the structured logger.

        Args:
            name: Logger name
            level: Logging level
            json_format: Whether to use JSON format
            log_file: Optional log file path
            event_bus_integration: Whether to publish logs to event bus
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._json_format = json_format
        self._event_bus_integration = event_bus_integration
        self._event_bus = get_event_bus() if event_bus_integration else None

        # Clear existing handlers
        self._logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        if json_format:
            console_handler.setFormatter(JsonFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
        self._logger.addHandler(console_handler)

        # File handler
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            if json_format:
                file_handler.setFormatter(JsonFormatter())
            self._logger.addHandler(file_handler)

        # Correlation ID context
        self._context: LogContext | None = None

    def set_context(self, context: LogContext) -> None:
        """Set logging context."""
        self._context = context

    def clear_context(self) -> None:
        """Clear logging context."""
        self._context = None

    def _log(
        self,
        level: int,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Internal log method with context."""
        extra = {}

        if self._context:
            extra.update(self._context.to_dict())

        extra.update(kwargs)

        # Add standard fields
        extra["timestamp"] = datetime.utcnow().isoformat()
        extra["level"] = logging.getLevelName(level)

        # Log
        self._logger.log(level, message, extra=extra)

        # Publish to event bus for significant events
        if self._event_bus_integration and self._event_bus and level >= logging.WARNING:
            self._publish_log_event(level, message, extra)

    def _publish_log_event(
        self, level: int, message: str, extra: dict[str, Any]
    ) -> None:
        """Publish log as event for monitoring."""
        try:
            log_event = Event(
                event_type="log.warning" if level == logging.WARNING else "log.error",
                source_service="logger",
                correlation_id=extra.get("correlation_id"),
                payload={
                    "level": logging.getLevelName(level),
                    "message": message,
                    "service": extra.get("service", "unknown"),
                    "operation": extra.get("operation", ""),
                },
            )
            self._event_bus.publish(log_event)
        except Exception:
            pass  # Don't let logging errors break the application

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, message, **kwargs)

    def bind(self, **kwargs: Any) -> "BoundLogger":
        """Create a bound logger with additional context."""
        return BoundLogger(self, kwargs)


class BoundLogger:
    """Logger with pre-bound context."""

    def __init__(self, logger: StructuredLogger, context: dict[str, Any]):
        self._logger = logger
        self._context = context

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        merged = {**self._context, **kwargs}
        self._logger._log(level, message, **merged)

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, message, **kwargs)


class JsonFormatter(logging.Formatter):
    """JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info",
            ]:
                log_data[key] = value

        return json.dumps(log_data, default=str)


def get_logger(name: str = "aios") -> StructuredLogger:
    """Get or create a structured logger."""
    return StructuredLogger(name)


__all__ = [
    "StructuredLogger",
    "BoundLogger",
    "LogContext",
    "JsonFormatter",
    "get_logger",
]