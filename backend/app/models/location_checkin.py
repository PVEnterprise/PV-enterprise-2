"""
Location Check-in database model for employee location tracking.
"""
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class LocationCheckin(BaseModel):
    """
    A single GPS location captured from an employee's device at one of the
    scheduled reminder slots (see app.services.location_reminder_scheduler).
    """
    __tablename__ = "location_checkins"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    slot = Column(String(20), nullable=False, index=True)  # "10:00", "12:00", "14:30", "17:00"
    hospital_name = Column(String(255), nullable=False)  # free text, not linked to the customers table
    # timezone=True so the stored value carries its UTC offset — without it,
    # the API serializes recorded_at with no offset suffix at all, and any
    # viewer (e.g. the admin Location Tracking page) parses that as if it
    # were already in their own local time instead of converting from UTC.
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)  # device timestamp when GPS was captured
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)  # meters, from the browser Geolocation API
    status = Column(String(20), nullable=False, default="pending", server_default="pending", index=True)  # pending, verified, rejected

    # Relationships
    user = relationship("User", back_populates="location_checkins", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<LocationCheckin {self.user_id} {self.slot} @ {self.recorded_at}>"
