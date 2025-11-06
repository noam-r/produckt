"""
Authentication schemas for request/response validation.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
import uuid


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    name: str = Field(..., min_length=1, max_length=255, description="User full name")
    organization_name: Optional[str] = Field(None, max_length=255, description="Organization name (creates new org if provided)")
    organization_id: Optional[uuid.UUID] = Field(None, description="Existing organization ID to join")

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets minimum strength requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "email": "user@example.com",
                "password": "SecurePass123",
                "name": "John Doe",
                "organization_name": "Acme Corp"
            }]
        }
    }


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "email": "user@example.com",
                "password": "SecurePass123"
            }]
        }
    }


class SessionResponse(BaseModel):
    """Response schema containing session information."""

    session_id: str = Field(..., description="Session identifier")
    user_id: uuid.UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User name")
    role: str = Field(..., description="User role")
    organization_id: uuid.UUID = Field(..., description="Organization ID")
    organization_name: str = Field(..., description="Organization name")
    expires_at: datetime = Field(..., description="Session expiration timestamp")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "session_id": "sess_abc123xyz",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "name": "John Doe",
                "role": "PRODUCT_MANAGER",
                "organization_id": "123e4567-e89b-12d3-a456-426614174001",
                "organization_name": "Acme Corp",
                "expires_at": "2025-11-01T12:00:00Z"
            }]
        }
    }


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str = Field(..., description="Response message")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "message": "Operation completed successfully"
            }]
        }
    }
