"""
Cost estimation service for AI operations.
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.initiative import Initiative
from backend.models.question import Question
from backend.llm.client import AnthropicClient


class CostEstimator:
    """Service for estimating costs of AI operations."""

    # Average tokens per question generation (based on typical prompts and responses)
    # These are conservative estimates based on typical question generation patterns
    QUESTION_GENERATION_TOKENS = {
        "input_tokens_per_question": 2000,   # System prompt + context + existing questions
        "output_tokens_per_question": 500,   # Generated question content
    }

    def __init__(self, db: Session):
        self.db = db
        self.anthropic_client = AnthropicClient()

    def estimate_question_generation_cost(self, initiative_id: UUID, question_count: int) -> Decimal:
        """
        Estimate cost for generating N questions for an initiative.
        
        Args:
            initiative_id: Initiative to generate questions for
            question_count: Number of questions to generate
            
        Returns:
            Estimated cost in USD as Decimal
            
        Raises:
            ValueError: If initiative not found or invalid question count
        """
        if question_count <= 0:
            raise ValueError("Question count must be positive")
            
        # Get initiative to determine context size
        initiative = self.db.query(Initiative).filter(Initiative.id == initiative_id).first()
        if not initiative:
            raise ValueError(f"Initiative {initiative_id} not found")
        
        # Get existing questions count to estimate context size
        existing_questions_count = (
            self.db.query(Question)
            .filter(Question.initiative_id == initiative_id)
            .count()
        )
        
        # Estimate tokens based on context size and questions to generate
        base_input_tokens = self.QUESTION_GENERATION_TOKENS["input_tokens_per_question"]
        base_output_tokens = self.QUESTION_GENERATION_TOKENS["output_tokens_per_question"]
        
        # Add context overhead for existing questions (roughly 50 tokens per existing question)
        context_overhead = existing_questions_count * 50
        
        # Total tokens for the operation
        total_input_tokens = (base_input_tokens + context_overhead) * question_count
        total_output_tokens = base_output_tokens * question_count
        
        # Use default model for estimation (from settings or fallback to Sonnet)
        model = "claude-sonnet-4-5"  # Default model for cost estimation
        
        return self.estimate_llm_call_cost(model, total_input_tokens, total_output_tokens)

    def estimate_llm_call_cost(self, model: str, input_tokens: int, output_tokens: int = 0) -> Decimal:
        """
        Estimate cost for an LLM call with given token counts.
        
        Args:
            model: Model name (e.g., "claude-sonnet-4-5")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens (default: 0)
            
        Returns:
            Estimated cost in USD as Decimal
            
        Raises:
            ValueError: If invalid token counts
        """
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("Token counts must be non-negative")
        
        # Use the existing pricing calculation from AnthropicClient
        cost_float = self.anthropic_client._calculate_cost(model, input_tokens, output_tokens)
        
        # Convert to Decimal for precise monetary calculations
        return Decimal(str(cost_float))

    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """
        Get pricing information for a specific model.
        
        Args:
            model: Model name
            
        Returns:
            Dictionary with 'input' and 'output' pricing per million tokens
            
        Raises:
            ValueError: If model not found
        """
        if model not in self.anthropic_client.PRICING:
            raise ValueError(f"Pricing not available for model: {model}")
        
        return self.anthropic_client.PRICING[model].copy()

    def get_available_models(self) -> Dict[str, Dict[str, float]]:
        """
        Get all available models and their pricing.
        
        Returns:
            Dictionary mapping model names to pricing information
        """
        return self.anthropic_client.PRICING.copy()

    def estimate_tokens_for_text(self, text: str) -> int:
        """
        Rough estimation of tokens for a given text.
        Uses a simple heuristic: ~4 characters per token for English text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Simple heuristic: roughly 4 characters per token
        # This is a conservative estimate for English text
        return max(1, len(text) // 4)

    def estimate_question_generation_tokens(self, initiative_id: UUID, question_count: int) -> Dict[str, int]:
        """
        Estimate token breakdown for question generation.
        
        Args:
            initiative_id: Initiative to generate questions for
            question_count: Number of questions to generate
            
        Returns:
            Dictionary with 'input_tokens' and 'output_tokens' estimates
            
        Raises:
            ValueError: If initiative not found or invalid question count
        """
        if question_count <= 0:
            raise ValueError("Question count must be positive")
            
        # Get initiative to determine context size
        initiative = self.db.query(Initiative).filter(Initiative.id == initiative_id).first()
        if not initiative:
            raise ValueError(f"Initiative {initiative_id} not found")
        
        # Get existing questions count to estimate context size
        existing_questions_count = (
            self.db.query(Question)
            .filter(Question.initiative_id == initiative_id)
            .count()
        )
        
        # Estimate tokens based on context size and questions to generate
        base_input_tokens = self.QUESTION_GENERATION_TOKENS["input_tokens_per_question"]
        base_output_tokens = self.QUESTION_GENERATION_TOKENS["output_tokens_per_question"]
        
        # Add context overhead for existing questions
        context_overhead = existing_questions_count * 50
        
        # Total tokens for the operation
        total_input_tokens = (base_input_tokens + context_overhead) * question_count
        total_output_tokens = base_output_tokens * question_count
        
        return {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens
        }