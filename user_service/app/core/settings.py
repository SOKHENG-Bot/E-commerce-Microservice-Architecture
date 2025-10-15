"""
User Service configuration using shared patterns
"""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

# Get the root directory path (ecommerce-microservices)
ROOT_DIR = Path(__file__).parent.parent.parent.parent
# Load from user_service/.env
ENV_FILE = ROOT_DIR / "user_service" / ".env"


class UserServiceSettings(BaseSettings):
    # Application
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool
    ENVIRONMENT: str

    # Service specific
    SERVICE_NAME: str
    USER_SERVICE_URL: str
    USER_SERVICE_HEALTH: str

    # Database
    USER_DATABASE_URL: str
    TEST_DATABASE_URL: str

    # PostgreSQL connection details (for Docker)
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Redis for caching and sessions
    REDIS_URL: str

    # Kafka for events
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_GROUP_ID: str
    KAFKA_TOPIC_USER_EVENTS: str
    KAFKA_TOPIC_USER_REGISTRATION: str
    KAFKA_TOPIC_USER_LOGIN: str

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool
    RATE_LIMIT_REQUESTS: int
    RATE_LIMIT_WINDOW: int
    RATE_LIMIT_PER_USER_REQUESTS: int
    RATE_LIMIT_PER_USER_WINDOW: int

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


def get_settings() -> UserServiceSettings:
    """Get settings singleton instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = UserServiceSettings()
    return _settings_instance
