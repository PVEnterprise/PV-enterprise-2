"""
SalesAttendance database model — tracks a sales rep's daily attendance status
(present/leave/holiday), separate from field visit records.
"""
from sqlalchemy import Column, String, Text, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class SalesAttendance(BaseModel):
    """
    SalesAttendance model representing a sales rep's attendance status for a given day.
    """
    __tablename__ = "sales_attendance"

    sales_rep_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False)  # present, leave, holiday
    notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("sales_rep_id", "attendance_date", name="uq_sales_attendance_rep_date"),
    )

    # Relationships
    sales_rep = relationship("User", back_populates="attendance_records", foreign_keys=[sales_rep_id])

    def __repr__(self) -> str:
        return f"<SalesAttendance rep={self.sales_rep_id} date={self.attendance_date} status={self.status}>"
