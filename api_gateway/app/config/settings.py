"""
API Gateway configuration
"""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

# Get the root directory path (api_gateway)
ROOT_DIR = Path(__file__).parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"


class GatewaySettings(BaseSettings):
    # Application
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool
    ENVIRONMENT: str

    # API Gateway specific
    API_HOST: str
    API_PORT: int
    API_V1_PREFIX: str

    # Service Discovery - URLs of backend services
    USER_SERVICE_URL: str
    USER_SERVICE_URLS: List[str] = []  # For load balancing
    PRODUCT_SERVICE_URL: str
    ORDER_SERVICE_URL: str
    NOTIFICATION_SERVICE_URL: str

    # Service Health Check URLs
    USER_SERVICE_HEALTH: str
    USER_SERVICE_HEALTH_URLS: List[str] = []  # For load balancing
    PRODUCT_SERVICE_HEALTH: str
    ORDER_SERVICE_HEALTH: str
    NOTIFICATION_SERVICE_HEALTH: str

    # Redis for caching and rate limiting
    REDIS_URL: str

    # Security
    SECRET_KEY: str
    JWT_ALGORITHM: str

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool
    RATE_LIMIT_REQUESTS: int  # requests per minute
    RATE_LIMIT_WINDOW: int  # seconds
    RATE_LIMIT_PER_USER_REQUESTS: int  # requests per hour for authenticated users
    RATE_LIMIT_PER_USER_WINDOW: int  # seconds

    # Circuit Breaker
    CIRCUIT_BREAKER_ENABLED: bool
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int
    CIRCUIT_BREAKER_TIMEOUT: int  # seconds
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int  # seconds

    # Request/Response
    REQUEST_TIMEOUT: int  # seconds
    MAX_REQUEST_SIZE: int  # 10MB
    ENABLE_REQUEST_LOGGING: bool

    # CORS
    CORS_ORIGINS: List[str]
    CORS_CREDENTIALS: bool
    CORS_METHODS: List[str]
    CORS_HEADERS: List[str]

    # Caching
    ENABLE_RESPONSE_CACHING: bool
    CACHE_TTL_DEFAULT: int  # 5 minutes
    CACHE_TTL_STATIC: int  # 1 hour

    # Logging
    LOG_LEVEL: str
    ENABLE_ACCESS_LOGS: bool

    class Config:
        env_file = ENV_FILE  # Path to root .env file
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env file


# Create a singleton instance
_settings_instance = None


def get_settings() -> GatewaySettings:
    """Get settings singleton instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = GatewaySettings()
    return _settings_instance
