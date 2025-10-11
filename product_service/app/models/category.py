from sqlalchemy import TEXT, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import ProductServiceBaseModel


class Category(ProductServiceBaseModel):
    __tablename__ = "categories"

    # Remove id, created_at, updated_at as they're inherited from BaseModel
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )

    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
