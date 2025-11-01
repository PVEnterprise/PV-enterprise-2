"""
API endpoints for managing attachments.
Generic attachment system that works for any entity type.
"""
import os
import uuid
import shutil
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import UUID

from app.api import deps
from app.models import Attachment, User
from app.schemas.attachment import Attachment as AttachmentSchema, AttachmentUpdate
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Test endpoint to debug
@router.post("/test-upload")
async def test_upload(
    file: UploadFile = File(...),
):
    """Simple test endpoint to verify file upload works"""
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(await file.read())
    }

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
    description: Optional[str] = Form(None),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Attachment:
    """
    Upload a file attachment for any entity.
    
    Supported entity types: order, customer, inventory, quotation, invoice, etc.
    Supported file types: images, PDF, Word, Excel, PowerPoint, CSV, JSON, TXT
    Max file size: 10MB
    """
    try:
        logger.info(f"Upload request received - entity_type: {entity_type}, entity_id: {entity_id}")
        logger.info(f"File info - filename: {file.filename}, content_type: {file.content_type}, description: {description}")
    except Exception as e:
        logger.error(f"Error logging file info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid file upload request: {str(e)}"
        )
    
    # Validate file type
    if file.content_type not in ALLOWED_MIME_TYPES:
        logger.error(f"Invalid file type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not allowed. Supported types: images, PDF, Word, Excel, PowerPoint, CSV"
        )
    
    try:
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ''
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Create entity-specific directory
        entity_dir = os.path.join(UPLOAD_DIR, entity_type, str(entity_id))
        os.makedirs(entity_dir, exist_ok=True)
        logger.info(f"Saving file to: {entity_dir}/{unique_filename}")
        
        # Save file directly using shutil to avoid reading into memory
        file_path = os.path.join(entity_dir, unique_filename)
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file size after writing
        file_size = os.path.getsize(file_path)
        logger.info(f"File saved successfully: {file_path}, size: {file_size} bytes")
        
        # Validate file size
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path)  # Delete the file
            logger.error(f"File too large: {file_size} bytes")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size {file_size} bytes exceeds maximum allowed size of {MAX_FILE_SIZE} bytes (10MB)"
            )
        
        if file_size == 0:
            os.remove(file_path)  # Delete empty file
            logger.error("File is empty")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty"
            )
        
        # Create database record
        db_attachment = Attachment(
            entity_type=entity_type,
            entity_id=entity_id,
            filename=unique_filename,
            original_filename=file.filename or 'unknown',
            file_path=file_path,
            file_type=file.content_type,
            file_size=file_size,
            file_extension=file_extension,
            description=description or file.filename,
            created_by=current_user.id,
        )
        
        db.add(db_attachment)
        db.commit()
        db.refresh(db_attachment)
        
        logger.info(f"Attachment record created: {db_attachment.id}")
        return db_attachment
    except Exception as e:
        logger.error(f"Error uploading attachment: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload attachment: {str(e)}"
        )


# IMPORTANT: Download route must come BEFORE the generic /{entity_type}/{entity_id} route
# Otherwise FastAPI will match /download/{id} as entity_type="download"
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
        logger.error(f"File not found on disk: {attachment.file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server"
        )
    
    # Log file info
    actual_size = os.path.getsize(attachment.file_path)
    logger.info(f"Downloading file: {attachment.file_path}")
    logger.info(f"File size on disk: {actual_size} bytes, DB size: {attachment.file_size} bytes")
    logger.info(f"Original filename: {attachment.original_filename}, Content-Type: {attachment.file_type}")
    
    return FileResponse(
        path=attachment.file_path,
        filename=attachment.original_filename,
        media_type=attachment.file_type
    )


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
