"""
User Service Independent Logging Module
====================================
Self-contained logging setup for User Service.
No external dependencies on shared modules.
"""

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List, Optional


class UserJSONFormatter(logging.Formatter):
    """Custom JSON formatter for User Service structured logging"""

    def __init__(self, exclude_fields: Optional[List[str]] = None):
        super().__init__()
        self.exclude_fields = exclude_fields or []

    def format(self, record: logging.LogRecord) -> str:
        # Create log entry with standard fields
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "service": "user_service",
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


def setup_user_logging(
    service_name: str = "user_service",
    log_level: str = "INFO",
    enable_file_logging: bool = False,
    log_dir: Optional[str] = None,
    max_file_size: int = 100 * 1024 * 1024,  # 100MB
    backup_count: int = 5,
    exclude_fields: Optional[List[str]] = None,
    enable_performance_logging: bool = True,
) -> logging.Logger:
    """
    Setup independent logging for User Service

    Returns:
        Configured logger instance
    """

    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers to avoid duplication
    logger.handlers.clear()

    # Create JSON formatter
    json_formatter = UserJSONFormatter(exclude_fields=exclude_fields)

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

    # Log startup message
    logger.info(
        "User Service logging configured",
        extra={
            "service": service_name,
            "log_level": log_level,
            "file_logging": enable_file_logging,
            "performance_logging": enable_performance_logging,
            "handlers": len(logger.handlers),
        },
    )

    return logger


# Default logger instance for convenience
default_user_logger = None


def get_default_user_logger() -> logging.Logger:
    """Get the default User Service logger instance"""
    global default_user_logger
    if default_user_logger is None:
        default_user_logger = setup_user_logging()
    return default_user_logger
