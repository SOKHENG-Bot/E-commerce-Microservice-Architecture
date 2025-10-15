from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from user_service.app.schemas.address import AddressResponse
from user_service.app.schemas.profile import ProfileResponse


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

    # @field_validator("password")
    # def validate_password(cls, value: str) -> str:
    #     if len(value) < 8:
    #         raise ValueError("Password must be at least 8 characters long")
    #     if not any(char.isupper() for char in value):
    #         raise ValueError("Password must contain at least one uppercase letter")
    #     if not any(char.islower() for char in value):
    #         raise ValueError("Password must contain at least one lowercase letter")
    #     if not any(char.isdigit() for char in value):
    #         raise ValueError("Password must contain at least one digit")
    #     return value


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    phone: Optional[str] = Field(None, min_length=10, max_length=15)


class PermissionResponse(BaseModel):
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Optional[list[PermissionResponse]] = []

    model_config = ConfigDict(from_attributes=True)


class UserLoginResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    date_joined: datetime
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    date_joined: datetime
    last_login: Optional[datetime] = None
    profile: Optional[ProfileResponse] = None
    addresses: Optional[list[AddressResponse]] = []
    roles: Optional[list[RoleResponse]] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Request/Response Models
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class VerificationResponse(BaseModel):
    verified: bool
    message: str = ""


class ValidationResponse(BaseModel):
    valid: bool
    message: str = ""


class PasswordValidationRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Password to validate")


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    uptime_seconds: float
    database: Dict[str, Any] = {}


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(
        ..., description="Refresh token for generating new access token"
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Request/Response Models
class DeactivationRequest(BaseModel):
    reason: Optional[str] = Field(
        default=None, description="Optional reason for account deactivation"
    )


class ReactivationRequest(BaseModel):
    email: str = Field(..., description="Email address of account to reactivate")


class AccountInfoResponse(BaseModel):
    """Comprehensive account information response"""

    user_id: str
    email: str
    is_active: bool
    is_verified: bool
    date_joined: str
    last_login: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    profile: Optional[ProfileResponse] = None
    addresses: Optional[list[AddressResponse]] = []
    roles: Optional[list[str]] = []
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    verify_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    new_password: str = Field(..., min_length=8, max_length=128)


class PermissionCheckResponse(BaseModel):
    user_id: int
    permission: str
    has_permission: bool


class UserPermissionsResponse(BaseModel):
    user_id: int
    permissions: list[str]


class UserRolesResponse(BaseModel):
    user_id: int
    roles: list[str]


class AvailablePermissionsResponse(BaseModel):
    permissions: list[str]
    roles: list[str]
