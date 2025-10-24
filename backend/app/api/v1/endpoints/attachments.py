"""
API endpoints for managing attachments.
Generic attachment system that works for any entity type.
"""
import os
import uuid
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID

from app.api import deps
from app.models import Attachment, User
from app.schemas.attachment import Attachment as AttachmentSchema, AttachmentUpdate
from app.core.config import settings

router = APIRouter()

# Allowed file types
ALLOWED_MIME_TYPES = {
    # Images
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
    # Documents
    'application/pdf',
    'application/msword',  # .doc
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
    'application/vnd.ms-excel',  # .xls
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
    'application/vnd.ms-powerpoint',  # .ppt
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
    # Data files
    'text/csv',
    'application/json',
    'text/plain',
}

# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '../../../../uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/{entity_type}/{entity_id}", response_model=AttachmentSchema, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    entity_type: str,
    entity_id: UUID,
    file: UploadFile = File(...),
    description: str = Form(None),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Attachment:
    """
    Upload a file attachment for any entity.
    
    Supported entity types: order, customer, inventory, quotation, invoice, etc.
    Supported file types: images, PDF, Word, Excel, PowerPoint, CSV, JSON, TXT
    Max file size: 10MB
    """
    # Validate file type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not allowed. Supported types: images, PDF, Word, Excel, PowerPoint, CSV"
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Validate file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size {file_size} bytes exceeds maximum allowed size of {MAX_FILE_SIZE} bytes (10MB)"
        )
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Create entity-specific directory
    entity_dir = os.path.join(UPLOAD_DIR, entity_type, str(entity_id))
    os.makedirs(entity_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(entity_dir, unique_filename)
    with open(file_path, 'wb') as f:
        f.write(content)
    
    # Create database record
    db_attachment = Attachment(
        entity_type=entity_type,
        entity_id=entity_id,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_type=file.content_type,
        file_size=file_size,
        file_extension=file_extension,
        description=description,
        created_by=current_user.id,
    )
    
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    
    return db_attachment


@router.get("/{entity_type}/{entity_id}", response_model=List[AttachmentSchema])
def get_attachments(
    entity_type: str,
    entity_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> List[Attachment]:
    """Get all attachments for a specific entity."""
    attachments = db.query(Attachment).filter(
        Attachment.entity_type == entity_type,
        Attachment.entity_id == entity_id
    ).order_by(Attachment.created_at.desc()).all()
    
    return attachments


@router.get("/download/{attachment_id}")
def download_attachment(
    attachment_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Download an attachment file."""
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found"
        )
    
    if not os.path.exists(attachment.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server"
        )
    
    return FileResponse(
        path=attachment.file_path,
        filename=attachment.original_filename,
        media_type=attachment.file_type
    )


@router.patch("/{attachment_id}", response_model=AttachmentSchema)
def update_attachment(
    attachment_id: UUID,
    attachment_update: AttachmentUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Attachment:
    """Update attachment metadata (description only)."""
    db_attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    
    if not db_attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found"
        )
    
    if attachment_update.description is not None:
        db_attachment.description = attachment_update.description
    
    db_attachment.updated_by = current_user.id
    db.commit()
    db.refresh(db_attachment)
    
    return db_attachment


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Delete an attachment (file and database record)."""
    db_attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    
    if not db_attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found"
        )
    
    # Delete file from disk
    if os.path.exists(db_attachment.file_path):
        os.remove(db_attachment.file_path)
    
    # Delete database record
    db.delete(db_attachment)
    db.commit()
    
    return None
