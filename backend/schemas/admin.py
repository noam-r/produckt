"""
Schemas for admin operations (user management, roles, etc.).
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

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


class BudgetInfo(BaseModel):
    """Budget information for a user."""
    monthly_budget_usd: Decimal
    current_spending_usd: Decimal
    remaining_budget_usd: Decimal
    utilization_percentage: float
    budget_updated_at: Optional[datetime] = None
    budget_updated_by: Optional[UUID] = None
    # Warning information
    has_warning: bool = False
    warning_message: Optional[str] = None
    is_over_budget: bool = False
    is_near_limit: bool = False


class UserResponse(BaseModel):
    """Response model for a user."""
    id: UUID
    email: EmailStr
    name: str
    is_active: bool
    force_password_change: bool = False
    roles: List[UserRoleInfo] = []
    budget: Optional[BudgetInfo] = None
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


class UpdateBudgetRequest(BaseModel):
    """Request model for updating a user's budget."""
    monthly_budget_usd: Decimal = Field(..., ge=0, le=10000, description="Monthly budget in USD (0.00 to 10,000.00)")

    @field_validator('monthly_budget_usd')
    @classmethod
    def validate_budget_precision(cls, v: Decimal) -> Decimal:
        """Validate budget has at most 2 decimal places."""
        if v.as_tuple().exponent < -2:
            raise ValueError("Budget must have at most 2 decimal places")
        return v


class UpdateBudgetResponse(BaseModel):
    """Response model for budget update."""
    message: str
    user: UserResponse


# Budget monitoring schemas
class BudgetOverviewSummary(BaseModel):
    """Summary statistics for budget overview."""
    total_users: int
    total_budget_usd: float
    total_spending_usd: float
    remaining_budget_usd: float
    overall_utilization_percentage: float
    users_over_budget: int
    users_near_limit: int
    users_within_budget: int


class UserBudgetData(BaseModel):
    """Budget data for a single user."""
    user_id: str
    email: EmailStr
    name: str
    monthly_budget_usd: float
    current_spending_usd: float
    remaining_budget_usd: float
    utilization_percentage: float
    is_over_budget: bool
    is_near_limit: bool
    has_warning: bool
    warning_message: Optional[str] = None


class BudgetOverviewResponse(BaseModel):
    """Response model for budget overview dashboard."""
    summary: BudgetOverviewSummary
    users: List[UserBudgetData]


class SpendingTrendData(BaseModel):
    """Spending trend data for a single month."""
    year: int
    month: int
    month_label: str
    total_spending_usd: float
    active_users: int
    total_budget_usd: float
    utilization_percentage: float


class SpendingTrendsResponse(BaseModel):
    """Response model for spending trends."""
    period_months: int
    start_date: str
    end_date: str
    trends: List[SpendingTrendData]


class BudgetAlert(BaseModel):
    """Budget alert for a single user."""
    user_id: str
    email: EmailStr
    name: str
    alert_level: str  # "critical", "warning", "resolved"
    monthly_budget_usd: float
    current_spending_usd: float
    utilization_percentage: float
    is_over_budget: bool
    warning_message: Optional[str] = None
    last_updated: str


class BudgetAlertsResponse(BaseModel):
    """Response model for budget alerts."""
    total_alerts: int
    critical_alerts: int
    warning_alerts: int
    alerts: List[BudgetAlert]
