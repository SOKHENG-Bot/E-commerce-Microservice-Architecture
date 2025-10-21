from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from user_service.app.models.address import AddressTypeEnum

# --------------------------------------------------------------
# Authentication Schemas
# --------------------------------------------------------------


class UserRegistrationRequest(BaseModel):
    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(
        ..., min_length=8, max_length=128, examples=["strongpassword123"]
    )


class UserRegistrationResponse(BaseModel):
    message: str

    model_config = ConfigDict(from_attributes=True)


class UserVerificationRequest(BaseModel):
    verify_token: str = Field(..., examples=["verification_token_123"])


class UserVerificationResponse(BaseModel):
    verified: bool
    message: str

    model_config = ConfigDict(from_attributes=True)


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(..., examples=["strongpassword123"])


class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(from_attributes=True)


class UserForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., examples=["user@example.com"])


class UserForgotPasswordResponse(BaseModel):
    message: str

    model_config = ConfigDict(from_attributes=True)


class UserResetPasswordRequest(BaseModel):
    email: EmailStr = Field(..., examples=["user@example.com"])
    new_password: str = Field(
        ..., min_length=8, max_length=128, examples=["strongpassword123"]
    )


class UserResetPasswordResponse(BaseModel):
    message: str

    model_config = ConfigDict(from_attributes=True)


class UserChangePasswordRequest(BaseModel):
    current_password: str = Field(..., examples=["currentpassword123"])
    new_password: str = Field(
        ..., min_length=8, max_length=128, examples=["strongpassword123"]
    )


class UserChangePasswordResponse(BaseModel):
    message: str

    model_config = ConfigDict(from_attributes=True)


class UserLogoutResponse(BaseModel):
    message: str

    model_config = ConfigDict(from_attributes=True)


class UserRefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., examples=["refresh_token_123"])


class UserRefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------
# Profile Schemas
# --------------------------------------------------------------


class ProfileUpdateRequest(BaseModel):
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    bio: Optional[str] = None
    preferences: Optional[dict[str, Any]] = {}


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    avatar_url: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    bio: Optional[str] = None
    preferences: Optional[dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserGetProfileResponse(BaseModel):
    profile: ProfileResponse

    model_config = ConfigDict(from_attributes=True)


class UserUpdateProfileRequest(BaseModel):
    profile: ProfileUpdateRequest


class UserUpdateProfileResponse(BaseModel):
    profile: ProfileResponse

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------
# Address Schemas
# --------------------------------------------------------------
class AddressUpdateRequest(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    is_primary: Optional[bool] = None
    is_default: Optional[bool] = None
    type: Optional[AddressTypeEnum] = None


class AddressResponse(BaseModel):
    id: int
    user_id: int
    street: str
    city: str
    state: str
    zip_code: str
    country: str
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserGetAddressesResponse(BaseModel):
    addresses: AddressResponse

    model_config = ConfigDict(from_attributes=True)


class UserUpdateAddressesRequest(BaseModel):
    address: AddressUpdateRequest


class UserUpdateAddressesResponse(BaseModel):
    address: AddressResponse

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------
# User Management Schemas
# --------------------------------------------------------------


class CurrentUserRequest(BaseModel):
    user_id: int


class UserGetAccountInfoResponse(BaseModel):
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


class UserUpdateAccountInfoRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    phone: Optional[str] = None


class UserUpdateAccountInfoResponse(BaseModel):
    message: str

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------
# Health Schemas
# --------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    uptime_seconds: float
    database: Dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)
