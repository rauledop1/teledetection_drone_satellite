import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from pathlib import Path

import jwt
from passlib.context import CryptContext


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


# JWT utilities
def create_access_token(
    data: Dict[str, Any], 
    secret_key: str, 
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def verify_token(
    token: str, 
    secret_key: str, 
    algorithm: str = "HS256"
) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except jwt.PyJWTError:
        return None


# File utilities
def generate_file_hash(file_path: Union[str, Path]) -> str:
    """Generate SHA-256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    
    return hash_sha256.hexdigest()


def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving the extension"""
    file_path = Path(original_filename)
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{file_path.suffix}"


def ensure_directory_exists(directory: Union[str, Path]) -> None:
    """Ensure a directory exists, create if it doesn't"""
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_file_size(file_path: Union[str, Path]) -> int:
    """Get file size in bytes"""
    return os.path.getsize(file_path)


def is_valid_file_type(mime_type: str, allowed_types: list) -> bool:
    """Check if file type is allowed"""
    return mime_type in allowed_types


# Logging utilities
def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    log_format: str = "json"
) -> logging.Logger:
    """Setup logging for a service"""
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler()
    
    if log_format.lower() == "json":
        import json
        
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "service": service_name,
                    "level": record.levelname,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                
                return json.dumps(log_entry)
        
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


# Validation utilities
def validate_uuid(uuid_string: str) -> bool:
    """Validate if string is a valid UUID"""
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


# Pagination utilities
def calculate_pagination(page: int, size: int, total: int) -> Dict[str, int]:
    """Calculate pagination metadata"""
    pages = (total + size - 1) // size  # Ceiling division
    
    return {
        "page": page,
        "size": size,
        "total": total,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1
    }


# Coordinate utilities
def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate latitude and longitude coordinates"""
    return -90 <= lat <= 90 and -180 <= lon <= 180


def calculate_bounding_box(coordinates: list) -> Dict[str, float]:
    """Calculate bounding box from list of coordinates"""
    if not coordinates:
        return {}
    
    lats = [coord[1] for coord in coordinates]
    lons = [coord[0] for coord in coordinates]
    
    return {
        "min_lat": min(lats),
        "max_lat": max(lats),
        "min_lon": min(lons),
        "max_lon": max(lons)
    }


# Error handling utilities
class ServiceError(Exception):
    """Base exception for service errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(ServiceError):
    """Exception for validation errors"""
    def __init__(self, message: str):
        super().__init__(message, 400)


class AuthenticationError(ServiceError):
    """Exception for authentication errors"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, 401)


class AuthorizationError(ServiceError):
    """Exception for authorization errors"""
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, 403)


class NotFoundError(ServiceError):
    """Exception for resource not found errors"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)


# Health check utilities
def check_database_health(database_url: str) -> bool:
    """Check if database is healthy"""
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_redis_health(redis_url: str) -> bool:
    """Check if Redis is healthy"""
    try:
        import redis
        r = redis.from_url(redis_url)
        r.ping()
        return True
    except Exception:
        return False


# Async utilities
async def async_retry(
    func,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0
):
    """Retry an async function with exponential backoff"""
    import asyncio
    
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            await asyncio.sleep(delay * (backoff ** attempt))
    
    return None