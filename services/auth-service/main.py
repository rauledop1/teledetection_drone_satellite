import sys
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import redis

# Add shared modules to path
sys.path.append('/app/shared')

from config import AuthServiceSettings
from models import User, UserCreate, UserLogin, Token, BaseResponse
from utils import (
    setup_logging, hash_password, verify_password, 
    create_access_token, verify_token, validate_email
)
from database import get_db, get_redis
from crud import UserCRUD


# Setup
logger = setup_logging("auth-service")
settings = AuthServiceSettings()
security = HTTPBearer()

# Create FastAPI app
app = FastAPI(
    title="Authentication Service",
    description="User authentication and authorization service",
    version="1.0.0"
)

# Initialize CRUD
user_crud = UserCRUD()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "auth-service",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "auth-service"
    }


@app.post("/register", response_model=BaseResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    try:
        # Validate email format
        if not validate_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Check if user already exists
        existing_user = user_crud.get_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        existing_user = user_crud.get_by_username(db, user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create user
        user = user_crud.create(db, user_data)
        
        logger.info(f"User registered successfully: {user.email}")
        
        return BaseResponse(
            success=True,
            message="User registered successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/login", response_model=Token)
async def login_user(
    login_data: UserLogin,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Authenticate user and return access token"""
    try:
        # Get user by username or email
        user = user_crud.get_by_username(db, login_data.username)
        if not user:
            user = user_crud.get_by_email(db, login_data.username)
        
        # Verify user and password
        if not user or not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )
        
        # Create access token
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
        
        expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
        access_token = create_access_token(
            data=token_data,
            secret_key=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
            expires_delta=expires_delta
        )
        
        # Update last login
        user_crud.update_last_login(db, user.id)
        
        # Store token in Redis for session management
        redis_client.setex(
            f"token:{user.id}",
            settings.jwt_expire_minutes * 60,
            access_token
        )
        
        logger.info(f"User logged in successfully: {user.email}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expire_minutes * 60
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/logout", response_model=BaseResponse)
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Logout user and invalidate token"""
    try:
        # Verify token
        token_data = verify_token(
            credentials.credentials,
            settings.jwt_secret,
            settings.jwt_algorithm
        )
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = token_data.get("sub")
        
        # Remove token from Redis
        redis_client.delete(f"token:{user_id}")
        
        logger.info(f"User logged out successfully: {user_id}")
        
        return BaseResponse(
            success=True,
            message="Logged out successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/verify", response_model=User)
async def verify_token_endpoint(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Verify token and return user information"""
    try:
        # Verify token
        token_data = verify_token(
            credentials.credentials,
            settings.jwt_secret,
            settings.jwt_algorithm
        )
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = token_data.get("sub")
        
        # Check if token exists in Redis
        stored_token = redis_client.get(f"token:{user_id}")
        if not stored_token or stored_token.decode() != credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not found or expired"
            )
        
        # Get user from database
        user = user_crud.get(db, UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )
        
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/me", response_model=User)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Get current user information"""
    return await verify_token_endpoint(credentials, db, redis_client)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.service_port,
        reload=settings.debug
    )