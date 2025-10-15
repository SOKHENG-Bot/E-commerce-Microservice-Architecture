"""
Notification Service Logging Middleware
====================================
Self-contained logging setup for Notification Service.
No external dependencies on shared modules.
"""

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional


class NotificationJSONFormatter(logging.Formatter):
    """Custom JSON formatter for Notification Service structured logging"""

    def __init__(self, exclude_fields: Optional[List[str]] = None):
        super().__init__()
        self.exclude_fields = exclude_fields or []

    def format(self, record: logging.LogRecord) -> str:
        # Create log entry with standard fields
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "service": "notification_service",
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields from record
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if (
                    key
                    not in [
                        "name",
                        "msg",
                        "args",
                        "levelname",
                        "levelno",
                        "pathname",
                        "filename",
                        "module",
                        "lineno",
                        "funcName",
                        "created",
                        "msecs",
                        "relativeCreated",
                        "thread",
                        "threadName",
                        "processName",
                        "process",
                        "getMessage",
                        "exc_info",
                        "exc_text",
                        "stack_info",
                    ]
                    + self.exclude_fields
                ):
                    log_entry[key] = value

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str, ensure_ascii=False)


def create_enhanced_logger(
    service_name: str,
    log_level: str = "INFO",
    enable_file_logging: bool = False,
    log_dir: Optional[str] = None,
    max_file_size: int = 100 * 1024 * 1024,  # 100MB
    backup_count: int = 5,
    exclude_fields: Optional[List[str]] = None,
) -> logging.Logger:
    """
    Create an enhanced logger for Notification Service components

    Args:
        service_name: Name of the service/component
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Whether to enable file logging
        log_dir: Directory for log files
        max_file_size: Maximum size of log files in bytes
        backup_count: Number of backup files to keep
        exclude_fields: Fields to exclude from JSON logs

    Returns:
        Configured logger instance
    """

    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers to avoid duplication
    logger.handlers.clear()

    # Create JSON formatter
    json_formatter = NotificationJSONFormatter(exclude_fields=exclude_fields)

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)

    # File handler if enabled
    if enable_file_logging:
        if log_dir is None:
            log_dir_path = Path(__file__).parent.parent / "logs"
        else:
            log_dir_path = Path(log_dir)

        log_dir_path.mkdir(exist_ok=True)

        # Main log file
        log_file = log_dir_path / f"{service_name}.log"
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_file_size, backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)

        # Error log file
        error_log_file = log_dir_path / f"{service_name}_errors.log"
        error_handler = RotatingFileHandler(
            error_log_file, maxBytes=max_file_size, backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)
        logger.addHandler(error_handler)

    return logger
