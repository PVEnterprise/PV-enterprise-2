"""
Territory database model.
"""
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Territory(BaseModel):
    """
    Territory model representing a named grouping of hospitals (customers),
    optionally covered by one sales person.
    """
    __tablename__ = "territories"

    name = Column(String(255), nullable=False, unique=True, index=True)
    city = Column(String(100))
    sales_person_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    sales_person = relationship("User", back_populates="territories", foreign_keys=[sales_person_id])
    customers = relationship("Customer", back_populates="territory")

    def __repr__(self) -> str:
        return f"<Territory {self.name}>"
