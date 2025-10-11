"""
API Gateway Independent Logging Module
====================================
Self-contained logging setup for API Gateway service.
No external dependencies on shared modules.
"""

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def __init__(self, exclude_fields: Optional[List[str]] = None):
        super().__init__()
        self.exclude_fields = exclude_fields or []

    def format(self, record: logging.LogRecord) -> str:
        # Create log entry with standard fields
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "service": "api_gateway",
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


def setup_api_gateway_logging(
    service_name: str = "api_gateway",
    log_level: str = "INFO",
    enable_file_logging: bool = False,
    log_dir: Optional[Union[str, Path]] = None,
    max_file_size: int = 100 * 1024 * 1024,  # 100MB
    backup_count: int = 5,
    exclude_fields: Optional[List[str]] = None,
    enable_performance_logging: bool = True,
) -> logging.Logger:
    """
    Setup independent logging for API Gateway service

    Args:
        service_name: Name of the service for logging context
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Whether to log to files
        log_dir: Directory for log files (default: ./logs)
        max_file_size: Maximum size of each log file in bytes
        backup_count: Number of backup files to keep
        exclude_fields: List of fields to exclude from JSON logs
        enable_performance_logging: Whether to enable performance metrics

    Returns:
        Configured logger instance
    """

    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers to avoid duplication
    logger.handlers.clear()

    # Create JSON formatter
    json_formatter = JSONFormatter(exclude_fields=exclude_fields)

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)

    # File handler if enabled
    if enable_file_logging:
        log_path: Path
        if log_dir is None:
            log_path = Path(__file__).parent.parent / "logs"
        else:
            log_path = Path(log_dir) if isinstance(log_dir, str) else log_dir

        log_path.mkdir(exist_ok=True)

        # Main log file
        log_file = log_path / f"{service_name}.log"
        file_handler = RotatingFileHandler(
            str(log_file), maxBytes=max_file_size, backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)

        # Error log file
        error_log_file = log_path / f"{service_name}_errors.log"
        error_handler = RotatingFileHandler(
            str(error_log_file), maxBytes=max_file_size, backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)
        logger.addHandler(error_handler)

    # Log startup message
    logger.info(
        "API Gateway logging configured",
        extra={
            "service": service_name,
            "log_level": log_level,
            "file_logging": enable_file_logging,
            "performance_logging": enable_performance_logging,
            "handlers": len(logger.handlers),
        },
    )

    return logger


class APIGatewayLogger:
    """
    Specialized logger class for API Gateway operations
    Provides convenience methods for different types of logging
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_routing_decision(
        self,
        correlation_id: str,
        path: str,
        target_service: str,
        routing_success: bool,
        **kwargs: Any,
    ) -> None:
        """Log API Gateway routing decisions"""
        extra_data: Dict[str, Any] = {
            "correlation_id": correlation_id,
            "event_type": "routing_decision",
            "path": path,
            "target_service": target_service,
            "routing_success": routing_success,
        }
        extra_data.update(kwargs)
        self.logger.info(
            "API Gateway routing decision",
            extra=extra_data,
        )

    def log_auth_event(
        self,
        correlation_id: str,
        auth_result: str,
        user_id: str = "anonymous",
        **kwargs: Any,
    ) -> None:
        """Log authentication events"""
        extra_data: Dict[str, Any] = {
            "correlation_id": correlation_id,
            "event_type": "auth_event",
            "auth_result": auth_result,
            "user_id": user_id,
        }
        extra_data.update(kwargs)
        self.logger.info(
            "API Gateway authentication event",
            extra=extra_data,
        )

    def log_rate_limit_event(
        self,
        correlation_id: str,
        rate_limit_status: str,
        rate_limit_key: str,
        **kwargs: Any,
    ) -> None:
        """Log rate limiting events"""
        extra_data: Dict[str, Any] = {
            "correlation_id": correlation_id,
            "event_type": "rate_limit_event",
            "rate_limit_status": rate_limit_status,
            "rate_limit_key": rate_limit_key,
        }
        extra_data.update(kwargs)
        self.logger.info(
            "API Gateway rate limit event",
            extra=extra_data,
        )

    def log_performance_metric(
        self, correlation_id: str, operation: str, duration_ms: float, **kwargs: Any
    ) -> None:
        """Log performance metrics"""
        extra_data: Dict[str, Any] = {
            "correlation_id": correlation_id,
            "event_type": "performance_metric",
            "operation": operation,
            "duration_ms": duration_ms,
        }
        extra_data.update(kwargs)
        self.logger.info(
            "API Gateway performance metric",
            extra=extra_data,
        )

    def log_error(
        self, correlation_id: str, error_type: str, error_message: str, **kwargs: Any
    ) -> None:
        """Log errors with context"""
        extra_data: Dict[str, Any] = {
            "correlation_id": correlation_id,
            "event_type": "error",
            "error_type": error_type,
            "error_message": error_message,
        }
        extra_data.update(kwargs)
        self.logger.error(
            f"API Gateway error: {error_message}",
            extra=extra_data,
        )


def get_api_gateway_logger(service_name: str = "api_gateway") -> APIGatewayLogger:
    """
    Get configured API Gateway logger instance

    Returns:
        APIGatewayLogger instance with convenience methods
    """
    base_logger = setup_api_gateway_logging(service_name)
    return APIGatewayLogger(base_logger)


# Default logger instance for convenience
default_logger = None


def get_default_logger() -> APIGatewayLogger:
    """Get the default API Gateway logger instance"""
    global default_logger
    if default_logger is None:
        default_logger = get_api_gateway_logger()
    return default_logger
