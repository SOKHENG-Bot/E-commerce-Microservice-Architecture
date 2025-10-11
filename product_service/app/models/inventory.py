from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import ProductServiceBaseModel


class Inventory(ProductServiceBaseModel):
    __tablename__ = "inventories"

    # Remove id, created_at, updated_at as they're inherited from BaseModel
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_variants.id"), nullable=True
    )

    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_level: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
    warehouse_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "(product_id IS NOT NULL AND variant_id IS NULL) OR "
            "(product_id IS NULL AND variant_id IS NOT NULL)",
            name="inventory_product_or_variant",
        ),
    )
