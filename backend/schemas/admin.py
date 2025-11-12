"""
Schemas for admin operations (user management, roles, etc.).
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# Role schemas
class RoleResponse(BaseModel):
    """Response model for a role."""
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# User schemas
class UserRoleInfo(BaseModel):
    """Role information for a user."""
    id: UUID
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Response model for a user."""
    id: UUID
    email: EmailStr
    name: str
    is_active: bool
    force_password_change: bool = False
    roles: List[UserRoleInfo] = []
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Response model for list of users."""
    users: List[UserResponse]
    total: int


class CreateUserRequest(BaseModel):
    """Request model for creating a user."""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    password: Optional[str] = None
    generate_password: bool = Field(False, description="Generate a random password")
    role_ids: List[UUID] = Field(default_factory=list, description="List of role IDs to assign")
    is_active: bool = Field(True, description="Whether the user is active")

    @model_validator(mode='after')
    def validate_password(self):
        """Validate that either password is provided or generate_password is True."""
        if not self.generate_password and not self.password:
            raise ValueError("Must provide either password or set generate_password=true")
        if self.password and len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters")
        return self


class CreateUserResponse(BaseModel):
    """Response model for user creation."""
    user: UserResponse
    generated_password: Optional[str] = Field(None, description="Generated password if generate_password was True")


class UpdateUserRequest(BaseModel):
    """Request model for updating a user."""
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    force_password_change: Optional[bool] = None
    role_ids: Optional[List[UUID]] = None


class ChangePasswordRequest(BaseModel):
    """Request model for changing a user's password."""
    password: Optional[str] = None
    generate_password: bool = Field(False, description="Generate a random password")

    @model_validator(mode='after')
    def validate_password(self):
        """Validate that either password is provided or generate_password is True."""
        if not self.generate_password and not self.password:
            raise ValueError("Must provide either password or set generate_password=true")
        if self.password and len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters")
        return self


class ChangePasswordResponse(BaseModel):
    """Response model for password change."""
    message: str
    generated_password: Optional[str] = Field(None, description="Generated password if generate_password was True")
