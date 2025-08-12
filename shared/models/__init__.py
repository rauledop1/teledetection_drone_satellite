from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class UserRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FileType(str, Enum):
    IMAGE = "image"
    ORTHOMOSAIC = "orthomosaic"
    POINT_CLOUD = "point_cloud"
    DSM = "dsm"
    DTM = "dtm"
    SATELLITE = "satellite"


# Base Models
class BaseResponse(BaseModel):
    success: bool = True
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)


class PaginatedResponse(BaseResponse):
    total: int
    page: int
    size: int
    pages: int


# User Models
class UserBase(BaseModel):
    email: str
    username: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.VIEWER
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Project Models
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[Dict[str, Any]] = None  # GeoJSON
    tags: List[str] = []


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class Project(ProjectBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True


# File Models
class FileMetadata(BaseModel):
    filename: str
    size: int
    mime_type: str
    checksum: str
    exif_data: Optional[Dict[str, Any]] = None
    gps_coordinates: Optional[Dict[str, float]] = None


class FileBase(BaseModel):
    filename: str
    file_type: FileType
    size: int
    mime_type: str
    metadata: Optional[Dict[str, Any]] = None


class FileCreate(FileBase):
    project_id: UUID
    storage_path: str
    checksum: str


class File(FileBase):
    id: UUID
    project_id: UUID
    owner_id: UUID
    storage_path: str
    checksum: str
    created_at: datetime
    is_processed: bool = False

    class Config:
        from_attributes = True


# Processing Models
class ProcessingTaskBase(BaseModel):
    task_type: str
    parameters: Dict[str, Any] = {}
    priority: int = Field(default=5, ge=1, le=10)


class ProcessingTaskCreate(ProcessingTaskBase):
    project_id: UUID
    input_files: List[UUID]


class ProcessingTask(ProcessingTaskBase):
    id: UUID
    project_id: UUID
    owner_id: UUID
    input_files: List[UUID]
    output_files: List[UUID] = []
    status: ProcessingStatus = ProcessingStatus.PENDING
    progress: float = 0.0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# WebODM Models
class WebODMProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class WebODMProject(WebODMProjectBase):
    id: int
    webodm_id: int
    project_id: UUID
    created_at: datetime


class WebODMTaskBase(BaseModel):
    name: str
    options: Dict[str, Any] = {}


class WebODMTask(WebODMTaskBase):
    id: UUID
    webodm_task_id: str
    webodm_project_id: int
    processing_task_id: UUID
    status: ProcessingStatus
    progress: float = 0.0
    created_at: datetime


# Google Earth Engine Models
class GEEImageCollection(BaseModel):
    collection_id: str
    start_date: datetime
    end_date: datetime
    bounds: Dict[str, Any]  # GeoJSON geometry
    filters: Dict[str, Any] = {}


class GEEExportTask(BaseModel):
    id: UUID
    task_id: str
    collection: GEEImageCollection
    export_params: Dict[str, Any]
    status: ProcessingStatus
    created_at: datetime


# Analysis Models
class AnalysisBase(BaseModel):
    analysis_type: str
    parameters: Dict[str, Any] = {}


class AnalysisCreate(AnalysisBase):
    project_id: UUID
    input_files: List[UUID]


class Analysis(AnalysisBase):
    id: UUID
    project_id: UUID
    owner_id: UUID
    input_files: List[UUID]
    results: Optional[Dict[str, Any]] = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Visualization Models
class LayerBase(BaseModel):
    name: str
    layer_type: str
    style: Dict[str, Any] = {}
    is_visible: bool = True
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)


class LayerCreate(LayerBase):
    project_id: UUID
    file_id: Optional[UUID] = None
    data_source: Dict[str, Any]


class Layer(LayerBase):
    id: UUID
    project_id: UUID
    file_id: Optional[UUID] = None
    data_source: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# API Response Models
class FileUploadResponse(BaseResponse):
    file: File


class ProjectResponse(BaseResponse):
    project: Project


class ProjectListResponse(PaginatedResponse):
    projects: List[Project]


class TaskResponse(BaseResponse):
    task: ProcessingTask


class TaskListResponse(PaginatedResponse):
    tasks: List[ProcessingTask]


class AnalysisResponse(BaseResponse):
    analysis: Analysis


class LayerResponse(BaseResponse):
    layer: Layer