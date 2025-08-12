import os
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID

import aiofiles
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import magic

# Add shared modules to path
sys.path.append('/app/shared')

from config import FileServiceSettings
from models import (
    File as FileModel, FileCreate, FileMetadata, 
    BaseResponse, FileUploadResponse, PaginatedResponse
)
from utils import (
    setup_logging, generate_unique_filename, generate_file_hash,
    ensure_directory_exists, get_file_size, is_valid_file_type,
    ServiceError, ValidationError, NotFoundError
)
from database import get_db
from crud import FileCRUD
from metadata_extractor import MetadataExtractor
from auth import get_current_user_from_token


# Setup
logger = setup_logging("file-service")
settings = FileServiceSettings()

# Create FastAPI app
app = FastAPI(
    title="File Management Service",
    description="File upload, storage, and metadata management service",
    version="1.0.0"
)

# Initialize CRUD and metadata extractor
file_crud = FileCRUD()
metadata_extractor = MetadataExtractor()

# Ensure storage directory exists
ensure_directory_exists(settings.storage_path)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "file-service",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "file-service",
        "storage_path": settings.storage_path,
        "storage_available": os.path.exists(settings.storage_path)
    }


@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    project_id: str = Form(...),
    file_type: str = Form(...),
    file: UploadFile = File(...),
    current_user = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """Upload a file and extract metadata"""
    try:
        # Validate project_id format
        try:
            project_uuid = UUID(project_id)
        except ValueError:
            raise ValidationError("Invalid project ID format")
        
        # Validate file type
        if file_type not in ["image", "orthomosaic", "point_cloud", "dsm", "dtm", "satellite"]:
            raise ValidationError("Invalid file type")
        
        # Check file size
        if file.size and file.size > settings.max_file_size:
            raise ValidationError(f"File size exceeds maximum allowed size of {settings.max_file_size} bytes")
        
        # Detect MIME type
        file_content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        mime_type = magic.from_buffer(file_content, mime=True)
        
        # Validate file type
        if not is_valid_file_type(mime_type, settings.allowed_file_types):
            raise ValidationError(f"File type {mime_type} is not allowed")
        
        # Generate unique filename
        unique_filename = generate_unique_filename(file.filename)
        
        # Create project directory if it doesn't exist
        project_dir = Path(settings.storage_path) / str(project_uuid)
        ensure_directory_exists(project_dir)
        
        # Save file to storage
        file_path = project_dir / unique_filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            await file.seek(0)
            content = await file.read()
            await f.write(content)
        
        # Generate file hash
        file_hash = generate_file_hash(file_path)
        
        # Extract metadata
        metadata = await metadata_extractor.extract_metadata(file_path, mime_type)
        
        # Get actual file size
        actual_size = get_file_size(file_path)
        
        # Create file record
        file_data = FileCreate(
            filename=unique_filename,
            original_filename=file.filename,
            file_type=file_type,
            size=actual_size,
            mime_type=mime_type,
            project_id=project_uuid,
            owner_id=current_user.id,
            storage_path=str(file_path),
            checksum=file_hash,
            metadata=metadata
        )
        
        # Save to database
        db_file = file_crud.create(db, file_data)
        
        logger.info(f"File uploaded successfully: {file.filename} -> {unique_filename}")
        
        return FileUploadResponse(
            success=True,
            message="File uploaded successfully",
            file=db_file
        )
    
    except ValidationError as e:
        # Clean up file if it was saved
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        # Clean up file if it was saved
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/files/{file_id}", response_model=FileModel)
async def get_file_info(
    file_id: UUID,
    current_user = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """Get file information"""
    try:
        file_record = file_crud.get(db, file_id)
        if not file_record:
            raise NotFoundError("File not found")
        
        # Check if user has access to this file
        if file_record.owner_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        return file_record
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/files/{file_id}/download")
async def download_file(
    file_id: UUID,
    current_user = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """Download a file"""
    try:
        file_record = file_crud.get(db, file_id)
        if not file_record:
            raise NotFoundError("File not found")
        
        # Check if user has access to this file
        if file_record.owner_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if file exists on disk
        if not os.path.exists(file_record.storage_path):
            raise NotFoundError("File not found on storage")
        
        return FileResponse(
            path=file_record.storage_path,
            filename=file_record.original_filename,
            media_type=file_record.mime_type
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/files/{file_id}", response_model=BaseResponse)
async def delete_file(
    file_id: UUID,
    current_user = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """Delete a file"""
    try:
        file_record = file_crud.get(db, file_id)
        if not file_record:
            raise NotFoundError("File not found")
        
        # Check if user has access to this file
        if file_record.owner_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete file from storage
        if os.path.exists(file_record.storage_path):
            os.remove(file_record.storage_path)
        
        # Delete from database
        file_crud.delete(db, file_id)
        
        logger.info(f"File deleted successfully: {file_record.filename}")
        
        return BaseResponse(
            success=True,
            message="File deleted successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/files", response_model=PaginatedResponse)
async def list_files(
    project_id: Optional[UUID] = None,
    file_type: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    current_user = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """List files with pagination and filtering"""
    try:
        # For non-admin users, only show their own files
        owner_id = None if current_user.role == "admin" else current_user.id
        
        files, total = file_crud.list_files(
            db=db,
            project_id=project_id,
            file_type=file_type,
            owner_id=owner_id,
            skip=(page - 1) * size,
            limit=size
        )
        
        pages = (total + size - 1) // size
        
        return PaginatedResponse(
            success=True,
            message="Files retrieved successfully",
            total=total,
            page=page,
            size=size,
            pages=pages,
            data=files
        )
    
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/projects/{project_id}/files", response_model=PaginatedResponse)
async def list_project_files(
    project_id: UUID,
    file_type: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    current_user = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """List files for a specific project"""
    try:
        # For non-admin users, only show their own files
        owner_id = None if current_user.role == "admin" else current_user.id
        
        files, total = file_crud.list_files(
            db=db,
            project_id=project_id,
            file_type=file_type,
            owner_id=owner_id,
            skip=(page - 1) * size,
            limit=size
        )
        
        pages = (total + size - 1) // size
        
        return PaginatedResponse(
            success=True,
            message="Project files retrieved successfully",
            total=total,
            page=page,
            size=size,
            pages=pages,
            data=files
        )
    
    except Exception as e:
        logger.error(f"Error listing project files: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/files/{file_id}/reprocess", response_model=BaseResponse)
async def reprocess_file_metadata(
    file_id: UUID,
    current_user = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """Reprocess file metadata"""
    try:
        file_record = file_crud.get(db, file_id)
        if not file_record:
            raise NotFoundError("File not found")
        
        # Check if user has access to this file
        if file_record.owner_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if file exists on disk
        if not os.path.exists(file_record.storage_path):
            raise NotFoundError("File not found on storage")
        
        # Extract metadata again
        metadata = await metadata_extractor.extract_metadata(
            file_record.storage_path, 
            file_record.mime_type
        )
        
        # Update file record
        file_crud.update_metadata(db, file_id, metadata)
        
        logger.info(f"File metadata reprocessed: {file_record.filename}")
        
        return BaseResponse(
            success=True,
            message="File metadata reprocessed successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing file metadata: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.service_port,
        reload=settings.debug
    )