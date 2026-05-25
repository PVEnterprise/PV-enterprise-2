"""
QuotationLog model — central audit log and counter for all quotation generations.
quotation_number is driven by a PostgreSQL sequence (atomic, no race conditions).
"""
from sqlalchemy import Column, Integer, Numeric, Date, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class QuotationLog(BaseModel):
    """
    One row per quotation PDF generated.
    - quotation_number: auto-assigned by DB sequence (global, ever-incrementing)
    - generated_by: the user who triggered the generation
    - order_id: the order this quotation was generated for
    - discount_percentage: discount applied at time of generation
    - valid_until: expiry date shown on the PDF
    - created_at (from BaseModel): timestamp of generation
    """
    __tablename__ = "quotation_logs"

    quotation_number = Column(
        Integer,
        server_default=text("nextval('quotation_number_seq')"),
        nullable=False,
        unique=True,
        index=True,
    )
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    discount_percentage = Column(Numeric(5, 2), nullable=True)
    valid_until = Column(Date, nullable=True)

    # Relationships
    order = relationship("Order", foreign_keys=[order_id], backref="quotation_logs")
    user = relationship("User", foreign_keys=[generated_by])
