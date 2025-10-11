from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .address import Address
from .base import UserServiceBaseModel
from .profile import Profile


class User(UserServiceBaseModel):
    __tablename__ = "users"

    # Authentication fields
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Personal info
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=True)

    # Status flags
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)

    # Timestamps
    date_joined: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Many-to-many relationship with roles
    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="user_roles", back_populates="users"
    )

    # One-to-one relationship with profile
    profile: Mapped[Profile] = relationship(
        "Profile", uselist=False, back_populates="user"
    )
    addresses: Mapped[list[Address]] = relationship(
        "Address", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def permissions(self) -> set[str]:
        # Aggregate permissions from roles
        return {perm.name for role in self.roles for perm in role.permissions}


class Role(UserServiceBaseModel):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(
        String(255), nullable=True, default="The default role for a user is customer."
    )

    # Many-to-many relationship with permissions
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary="role_permissions", back_populates="roles"
    )
    # Many-to-many relationship with users
    users: Mapped[list["User"]] = relationship(
        "User", secondary="user_roles", back_populates="roles"
    )


class RolePermission(UserServiceBaseModel):
    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )


class UserRole(UserServiceBaseModel):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )


class Permission(UserServiceBaseModel):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(
        String(255), nullable=True, default="Custom permission description."
    )

    # Many-to-many relationship with roles
    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="role_permissions", back_populates="permissions"
    )
