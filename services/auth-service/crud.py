from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

import sys
sys.path.append('/app/shared')

from models import User, UserCreate, UserUpdate
from utils import hash_password


class UserCRUD:
    """CRUD operations for User model"""
    
    def get(self, db: Session, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    def get_by_username(self, db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()
    
    def create(self, db: Session, user_data: UserCreate) -> User:
        """Create new user"""
        # Hash password
        password_hash = hash_password(user_data.password)
        
        # Create user object
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            password_hash=password_hash,
            role=user_data.role,
            is_active=user_data.is_active,
            created_at=datetime.utcnow()
        )
        
        # Add to database
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    def update(self, db: Session, user_id: UUID, user_data: UserUpdate) -> Optional[User]:
        """Update user"""
        db_user = self.get(db, user_id)
        if not db_user:
            return None
        
        # Update fields
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db_user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    def update_last_login(self, db: Session, user_id: UUID) -> None:
        """Update user's last login timestamp"""
        db_user = self.get(db, user_id)
        if db_user:
            db_user.last_login = datetime.utcnow()
            db.commit()
    
    def delete(self, db: Session, user_id: UUID) -> bool:
        """Delete user"""
        db_user = self.get(db, user_id)
        if not db_user:
            return False
        
        db.delete(db_user)
        db.commit()
        
        return True
    
    def list_users(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> list[User]:
        """List users with pagination"""
        query = db.query(User)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        return query.offset(skip).limit(limit).all()
    
    def count_users(self, db: Session, is_active: Optional[bool] = None) -> int:
        """Count total users"""
        query = db.query(User)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        return query.count()