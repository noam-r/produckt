"""
User monthly spending model for tracking AI costs.
"""

import uuid
from sqlalchemy import Column, Integer, Numeric, ForeignKey, UniqueConstraint, Index
from backend.models.utils import GUID
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models.base import TimestampMixin


class UserMonthlySpending(Base, TimestampMixin):
    """
    Track monthly AI spending per user for budget enforcement.
    """
    __tablename__ = "user_monthly_spending"

    # Primary key
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # User and time period
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12

    # Spending amount
    total_spent_usd = Column(Numeric(10, 2), nullable=False, default=0.00)

    # Relationships
    user = relationship("User", back_populates="monthly_spending")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'year', 'month', name='uq_user_month'),
        Index('ix_user_monthly_spending_user_month', 'user_id', 'year', 'month'),
    )

    def __repr__(self):
        return f"<UserMonthlySpending(user_id={self.user_id}, year={self.year}, month={self.month}, spent=${self.total_spent_usd})>"