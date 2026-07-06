"""
FieldVisit database model — logs a sales rep's visit to a customer or lead.
"""
from sqlalchemy import Column, String, Text, Date, Time, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class FieldVisit(BaseModel):
    """
    FieldVisit model representing a single sales rep visit to a hospital
    (existing Customer) or a prospect (Lead). Exactly one of customer_id/lead_id
    must be set.
    """
    __tablename__ = "field_visits"

    visit_date = Column(Date, nullable=False, index=True)
    sales_rep_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True, index=True)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True, index=True)
    in_time = Column(Time, nullable=True)
    out_time = Column(Time, nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "(customer_id IS NOT NULL AND lead_id IS NULL) OR (customer_id IS NULL AND lead_id IS NOT NULL)",
            name="check_field_visit_exactly_one_target",
        ),
        Index("ix_field_visits_rep_date", "sales_rep_id", "visit_date"),
    )

    # Relationships
    sales_rep = relationship("User", back_populates="field_visits", foreign_keys=[sales_rep_id])
    customer = relationship("Customer", back_populates="field_visits", foreign_keys=[customer_id])
    lead = relationship("Lead", back_populates="field_visits", foreign_keys=[lead_id])

    def __repr__(self) -> str:
        return f"<FieldVisit rep={self.sales_rep_id} date={self.visit_date}>"
