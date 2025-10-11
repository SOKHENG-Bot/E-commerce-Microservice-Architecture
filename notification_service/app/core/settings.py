"""
Notification Service configuration using shared patterns
"""

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings

# Get the root directory path (ecommerce-microservices)
ROOT_DIR = Path(__file__).parent.parent.parent.parent
ENV_FILE = ROOT_DIR / "notification_service" / ".env"


class NotificationServiceSettings(BaseSettings):
    # Application
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool
    ENVIRONMENT: str

    # Service specific
    SERVICE_NAME: str
    NOTIFICATION_SERVICE_URL: str
    NOTIFICATION_SERVICE_HEALTH: str

    # Database
    NOTIFICATION_DATABASE_URL: str

    # PostgreSQL connection details (for Docker)
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str

    # Redis for caching and rate limiting
    REDIS_URL: str

    # Kafka for events
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_GROUP_ID: str
    KAFKA_TOPIC_NOTIFICATION_EVENTS: Optional[str] = None
    KAFKA_TOPIC_EMAIL_EVENTS: Optional[str] = None
    KAFKA_TOPIC_SMS_EVENTS: Optional[str] = None

    # Email Configuration
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[str] = None  # Changed to str to handle empty strings
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    FROM_EMAIL: Optional[str] = None
    FROM_NAME: str = "E-Commerce Platform"

    # SMS Configuration (Twilio)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None

    # Rate Limiting
    EMAIL_RATE_LIMIT: int = 100  # emails per hour per user
    SMS_RATE_LIMIT: int = 10  # SMS per hour per user

    # Retry Configuration
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 60  # seconds

    # CORS
    CORS_ORIGINS: List[str]
    CORS_CREDENTIALS: bool
    CORS_METHODS: List[str]
    CORS_HEADERS: List[str]

    # Logging
    LOG_LEVEL: str
    ENABLE_ACCESS_LOGS: bool

    class Config:
        env_file = ENV_FILE  # Path to root .env file
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env file


# Create a singleton instance
_settings_instance = None


def get_settings() -> NotificationServiceSettings:
    """Get settings singleton instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = NotificationServiceSettings()
    return _settings_instance
