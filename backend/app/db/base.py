"""
Database base configuration and session management.
"""
import uuid
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""
    
    # Generate __tablename__ automatically from class name
    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name (convert CamelCase to snake_case)."""
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


class BaseModel(Base):
    """
    Base model with common fields for all tables.
    Provides UUID primary key, timestamp fields, and audit tracking.
    """
    __abstract__ = True
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    # Audit fields - track who created and last updated
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    
    def dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def set_audit_fields(self, user_id: Optional[uuid.UUID], is_create: bool = False):
        """
        Set audit fields for create or update operations.
        
        Args:
            user_id: ID of the user performing the operation
            is_create: True if this is a create operation, False for update
        """
        if is_create:
            self.created_by = user_id
            self.updated_by = user_id  # Default to created_by on creation
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
        else:
            self.updated_by = user_id
            self.updated_at = datetime.utcnow()
