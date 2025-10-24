"""
User and Role database models.
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import BaseModel


class Role(BaseModel):
    """
    Role model for RBAC system.
    Defines user roles and their permissions.
    """
    __tablename__ = "roles"
    
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text)
    permissions = Column(JSONB, nullable=False, default=dict)
    
    # Relationships
    users = relationship("User", back_populates="role", foreign_keys="User.role_id")
    
    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class User(BaseModel):
    """
    User model for authentication and authorization.
    Stores user credentials, profile, and role information.
    """
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    role = relationship("Role", back_populates="users", foreign_keys=[role_id])
    created_orders = relationship(
        "Order",
        back_populates="sales_rep",
        foreign_keys="Order.sales_rep_id"
    )
    decoded_items = relationship(
        "OrderItem",
        back_populates="decoder",
        foreign_keys="OrderItem.decoded_by"
    )
    created_quotations = relationship(
        "Quotation",
        back_populates="creator",
        foreign_keys="Quotation.created_by"
    )
    created_invoices = relationship(
        "Invoice",
        back_populates="creator",
        foreign_keys="Invoice.created_by"
    )
    approvals = relationship("Approval", back_populates="approver", foreign_keys="Approval.approver_id")
    audit_logs = relationship("AuditLog", back_populates="user", foreign_keys="AuditLog.user_id")
    notifications = relationship("Notification", back_populates="user", foreign_keys="Notification.user_id")
    created_customers = relationship(
        "Customer",
        back_populates="creator",
        foreign_keys="Customer.created_by"
    )
    created_dispatches = relationship(
        "Dispatch",
        back_populates="creator",
        foreign_keys="Dispatch.created_by"
    )
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
    
    @property
    def role_name(self) -> str:
        """Get the role name."""
        return self.role.name if self.role else None
