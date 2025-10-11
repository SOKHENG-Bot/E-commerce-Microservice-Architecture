from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from user_service.app.models.address import AddressTypeEnum


class AddressBase(BaseModel):
    type: AddressTypeEnum
    street_address: str = Field(..., max_length=255)
    apartment: Optional[str] = Field(None, max_length=100)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    postal_code: str = Field(..., max_length=20)
    country: str = Field(..., max_length=100)
    is_default: bool = False


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    type: Optional[AddressTypeEnum] = None
    street_address: Optional[str] = Field(None, max_length=255)
    apartment: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    is_default: Optional[bool] = None


class AddressResponse(AddressBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Request/Response Models
class MessageResponse(BaseModel):
    message: str
