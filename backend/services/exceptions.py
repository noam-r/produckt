"""
Custom exceptions for cost control services.
"""

from decimal import Decimal
from typing import Optional


class BudgetExceededError(Exception):
    """
    Raised when an operation would exceed a user's monthly budget.
    
    This exception is raised when the estimated cost of an operation
    plus the user's current monthly spending would exceed their budget limit.
    """
    
    def __init__(
        self, 
        current_spending: Decimal, 
        budget_limit: Decimal, 
        estimated_cost: Decimal,
        user_id: Optional[str] = None
    ):
        self.current_spending = current_spending
        self.budget_limit = budget_limit
        self.estimated_cost = estimated_cost
        self.user_id = user_id
        
        message = (
            f"Operation would exceed budget: "
            f"${estimated_cost} + ${current_spending} > ${budget_limit}"
        )
        super().__init__(message)


class QuestionGenerationThrottledError(Exception):
    """
    Raised when question generation is throttled due to too many unanswered questions.
    
    This exception is raised when an initiative has reached the limit of
    unanswered questions (default: 5) and cannot generate more questions
    until some are answered.
    """
    
    def __init__(
        self, 
        unanswered_count: int, 
        limit: int = 5,
        initiative_id: Optional[str] = None
    ):
        self.unanswered_count = unanswered_count
        self.limit = limit
        self.initiative_id = initiative_id
        
        message = (
            f"Cannot generate questions: {unanswered_count} unanswered questions "
            f"(limit: {limit}). Please answer existing questions first."
        )
        super().__init__(message)


class InitiativeQuestionLimitError(Exception):
    """
    Raised when an initiative has reached its maximum question limit.
    
    This exception is raised when an initiative has reached the maximum
    total number of questions allowed (both answered and unanswered).
    """
    
    def __init__(
        self,
        current_count: int,
        max_limit: int,
        initiative_id: Optional[str] = None
    ):
        self.current_count = current_count
        self.max_limit = max_limit
        self.initiative_id = initiative_id
        
        message = (
            f"Cannot generate questions: initiative has {current_count} questions "
            f"(limit: {max_limit}). Maximum questions per initiative exceeded."
        )
        super().__init__(message)