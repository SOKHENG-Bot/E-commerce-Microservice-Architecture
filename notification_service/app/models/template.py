from typing import Any

from sqlalchemy import JSON, TEXT, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import NotificationServiceBaseModel


class Template(NotificationServiceBaseModel):
    __tablename__ = "templates"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="text/html"
    )
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(TEXT, nullable=False)

    variables: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # File storage fields
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_content: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    file_format: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # 'json' or 'md'
