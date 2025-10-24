"""
Generic Attachment model for storing file uploads for any entity.
"""
from sqlalchemy import Column, String, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import BaseModel


class Attachment(BaseModel):
    """
    Generic Attachment model for storing files attached to any entity.
    Uses polymorphic pattern - can attach to orders, customers, inventory, etc.
    Supports images, PDFs, Excel, Word, PowerPoint, CSV, and more.
    """
    __tablename__ = "attachments"
    
    # Polymorphic fields - can attach to any entity
    entity_type = Column(String(50), nullable=False, index=True)  # 'order', 'customer', 'inventory', etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # ID of the entity
    
    # File information
    filename = Column(String(255), nullable=False)  # Stored filename (unique)
    original_filename = Column(String(255), nullable=False)  # Original upload filename
    file_path = Column(String(500), nullable=False)  # Path to file on disk/storage
    file_type = Column(String(100), nullable=False)  # MIME type (image/jpeg, application/pdf, etc.)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_extension = Column(String(10))  # .jpg, .pdf, .xlsx, etc.
    
    # Optional metadata
    description = Column(String(500))  # Optional description/note about the file
    
    def __repr__(self) -> str:
        return f"<Attachment {self.original_filename} for {self.entity_type}:{self.entity_id}>"
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in MB."""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def is_image(self) -> bool:
        """Check if attachment is an image."""
        return self.file_type.startswith('image/')
    
    @property
    def is_pdf(self) -> bool:
        """Check if attachment is a PDF."""
        return self.file_type == 'application/pdf'
    
    @property
    def is_document(self) -> bool:
        """Check if attachment is a document (Word, Excel, PowerPoint)."""
        doc_types = [
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        ]
        return self.file_type in doc_types
