"""
Product Service configuration using shared patterns
"""

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the product service directory path
PRODUCT_SERVICE_DIR = Path(__file__).parent.parent.parent
ENV_FILE = PRODUCT_SERVICE_DIR / ".env"


class ProductSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool
    ENVIRONMENT: str
    LOG_LEVEL: str

    # Service specific
    SERVICE_NAME: str
    PRODUCT_SERVICE_URL: str
    PRODUCT_SERVICE_HEALTH: str

    # Database
    PRODUCT_DATABASE_URL: str
    DATABASE_POOL_SIZE: int
    DATABASE_MAX_OVERFLOW: int

    # PostgreSQL connection details (for Docker)
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: str

    # Redis for caching
    REDIS_URL: str

    # Kafka for events
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_GROUP_ID: str

    # Product specific Kafka topics (optional)
    KAFKA_TOPIC_PRODUCT_EVENTS: Optional[str] = None
    KAFKA_TOPIC_INVENTORY_EVENTS: Optional[str] = None
    KAFKA_TOPIC_PRODUCT_CATALOG: Optional[str] = None

    # External Service URLs
    USER_SERVICE_URL: str
    ORDER_SERVICE_URL: str
    NOTIFICATION_SERVICE_URL: str

    # CORS
    CORS_ORIGINS: List[str]
    CORS_CREDENTIALS: bool
    CORS_METHODS: List[str]
    CORS_HEADERS: List[str]

    # Logging
    ENABLE_ACCESS_LOGS: bool

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool
    RATE_LIMIT_REQUESTS: int
    RATE_LIMIT_WINDOW: int
    RATE_LIMIT_PER_USER_REQUESTS: int
    RATE_LIMIT_PER_USER_WINDOW: int

    # Request/Response Settings
    REQUEST_TIMEOUT: int
    RESPONSE_TIMEOUT: int
    MAX_REQUEST_SIZE: int
    ENABLE_REQUEST_LOGGING: bool

    # Circuit Breaker
    CIRCUIT_BREAKER_ENABLED: bool
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int
    CIRCUIT_BREAKER_TIMEOUT: int
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int

    # Caching
    ENABLE_RESPONSE_CACHING: bool
    CACHE_TTL_DEFAULT: int
    CACHE_TTL_STATIC: int


# Create a singleton instance
_settings_instance = None


def get_settings() -> ProductSettings:
    """Get settings singleton instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = ProductSettings()
    return _settings_instance
