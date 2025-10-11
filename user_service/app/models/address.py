from enum import Enum

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import UserServiceBaseModel


class AddressTypeEnum(Enum):
    BILLING = "billing"
    SHIPPING = "shipping"


class Address(UserServiceBaseModel):
    __tablename__ = "addresses"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    type: Mapped[AddressTypeEnum] = mapped_column(
        SQLEnum(AddressTypeEnum, name="address_type_enum"),
        nullable=False,
        default=AddressTypeEnum.BILLING,
    )

    street_address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    apartment: Mapped[str] = mapped_column(String(100), nullable=True, default="")
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    state: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    is_default: Mapped[bool] = mapped_column(default=False)

    # relationships
    user = relationship("User", back_populates="addresses")
