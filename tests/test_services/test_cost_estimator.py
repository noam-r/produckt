"""
Unit tests for CostEstimator service.
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.services.cost_estimator import CostEstimator
from backend.models.initiative import Initiative
from backend.models.question import Question, QuestionCategory, QuestionPriority
from backend.models.answer import Answer, AnswerStatus
from backend.models.organization import Organization
from backend.models.user import User, UserRoleEnum


class TestCostEstimator:
    """Unit tests for CostEstimator service."""

    @pytest.fixture
    def cost_estimator(self, test_db: Session):
        """Create a CostEstimator instance."""
        return CostEstimator(test_db)

    @pytest.fixture
    def test_initiative(self, test_db: Session, test_organization: Organization):
        """Create a test initiative."""
        # Create a user first
        import bcrypt
        password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user = User(
            email=f"user_{uuid4()}@example.com",
            password_hash=password_hash,
            name="Test User",
            role=UserRoleEnum.PRODUCT_MANAGER,
            organization_id=test_organization.id,
            is_active=True
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create initiative
        initiative = Initiative(
            title="Test Initiative",
            description="Test Description",
            organization_id=test_organization.id,
            created_by=user.id
        )
        test_db.add(initiative)
        test_db.commit()
        test_db.refresh(initiative)
        return initiative

    def test_estimate_llm_call_cost_accuracy(self, cost_estimator: CostEstimator):
        """Test cost calculation accuracy for different models."""
        # Test with known model and token counts
        model = "claude-sonnet-4-5"
        input_tokens = 1000
        output_tokens = 500
        
        cost = cost_estimator.estimate_llm_call_cost(model, input_tokens, output_tokens)
        
        # Expected cost: (1000/1M * $3) + (500/1M * $15) = $0.003 + $0.0075 = $0.0105
        expected_cost = Decimal('0.010500')
        assert cost == expected_cost, f"Expected {expected_cost}, got {cost}"

    def test_estimate_llm_call_cost_different_models(self, cost_estimator: CostEstimator):
        """Test cost calculation for different model pricing."""
        input_tokens = 1000
        output_tokens = 500
        
        # Test Sonnet model
        sonnet_cost = cost_estimator.estimate_llm_call_cost("claude-sonnet-4-5", input_tokens, output_tokens)
        
        # Test Haiku model (should be cheaper)
        haiku_cost = cost_estimator.estimate_llm_call_cost("claude-haiku-4-5", input_tokens, output_tokens)
        
        # Haiku should be cheaper than Sonnet
        assert haiku_cost < sonnet_cost, f"Haiku ({haiku_cost}) should be cheaper than Sonnet ({sonnet_cost})"
        
        # Verify Haiku cost calculation
        # Expected: (1000/1M * $1) + (500/1M * $5) = $0.001 + $0.0025 = $0.0035
        expected_haiku_cost = Decimal('0.003500')
        assert haiku_cost == expected_haiku_cost, f"Expected {expected_haiku_cost}, got {haiku_cost}"

    def test_estimate_llm_call_cost_zero_tokens(self, cost_estimator: CostEstimator):
        """Test cost calculation with zero tokens."""
        cost = cost_estimator.estimate_llm_call_cost("claude-sonnet-4-5", 0, 0)
        assert cost == Decimal('0.000000'), f"Expected zero cost for zero tokens, got {cost}"

    def test_estimate_llm_call_cost_input_only(self, cost_estimator: CostEstimator):
        """Test cost calculation with only input tokens."""
        input_tokens = 1000
        cost = cost_estimator.estimate_llm_call_cost("claude-sonnet-4-5", input_tokens, 0)
        
        # Expected: 1000/1M * $3 = $0.003
        expected_cost = Decimal('0.003000')
        assert cost == expected_cost, f"Expected {expected_cost}, got {cost}"

    def test_estimate_llm_call_cost_invalid_tokens(self, cost_estimator: CostEstimator):
        """Test error handling for invalid token counts."""
        with pytest.raises(ValueError, match="Token counts must be non-negative"):
            cost_estimator.estimate_llm_call_cost("claude-sonnet-4-5", -1, 0)
        
        with pytest.raises(ValueError, match="Token counts must be non-negative"):
            cost_estimator.estimate_llm_call_cost("claude-sonnet-4-5", 0, -1)

    def test_estimate_question_generation_cost_basic(self, cost_estimator: CostEstimator, test_initiative: Initiative):
        """Test basic question generation cost estimation."""
        question_count = 5
        cost = cost_estimator.estimate_question_generation_cost(test_initiative.id, question_count)
        
        # Should return a positive cost
        assert cost > Decimal('0'), f"Expected positive cost, got {cost}"
        
        # Cost should be reasonable (not too high or too low)
        assert cost < Decimal('1.00'), f"Cost seems too high: {cost}"
        assert cost > Decimal('0.001'), f"Cost seems too low: {cost}"

    def test_estimate_question_generation_cost_with_existing_questions(
        self, 
        cost_estimator: CostEstimator, 
        test_initiative: Initiative,
        test_db: Session
    ):
        """Test question generation cost with existing questions (context overhead)."""
        # Add some existing questions
        for i in range(10):
            question = Question(
                question_text=f"Test question {i}",
                initiative_id=test_initiative.id,
                iteration=1,
                category=QuestionCategory.BUSINESS_DEV,
                priority=QuestionPriority.P1,
                rationale=f"Test rationale {i}"
            )
            test_db.add(question)
        test_db.commit()
        
        # Estimate cost for new questions
        question_count = 3
        cost_with_context = cost_estimator.estimate_question_generation_cost(test_initiative.id, question_count)
        
        # Create a new initiative without existing questions for comparison
        new_initiative = Initiative(
            title="New Initiative",
            description="New Description",
            organization_id=test_initiative.organization_id,
            created_by=test_initiative.created_by
        )
        test_db.add(new_initiative)
        test_db.commit()
        test_db.refresh(new_initiative)
        
        cost_without_context = cost_estimator.estimate_question_generation_cost(new_initiative.id, question_count)
        
        # Cost with existing questions should be higher due to context overhead
        assert cost_with_context > cost_without_context, \
            f"Cost with context ({cost_with_context}) should be higher than without context ({cost_without_context})"

    def test_estimate_question_generation_cost_scaling(self, cost_estimator: CostEstimator, test_initiative: Initiative):
        """Test that question generation cost scales with question count."""
        cost_1 = cost_estimator.estimate_question_generation_cost(test_initiative.id, 1)
        cost_5 = cost_estimator.estimate_question_generation_cost(test_initiative.id, 5)
        cost_10 = cost_estimator.estimate_question_generation_cost(test_initiative.id, 10)
        
        # Cost should scale roughly linearly
        assert cost_5 > cost_1, f"Cost for 5 questions ({cost_5}) should be higher than 1 question ({cost_1})"
        assert cost_10 > cost_5, f"Cost for 10 questions ({cost_10}) should be higher than 5 questions ({cost_5})"
        
        # Rough linearity check (allowing for some overhead)
        ratio_5_to_1 = cost_5 / cost_1
        ratio_10_to_5 = cost_10 / cost_5
        
        # Ratios should be reasonably close to expected scaling
        assert 3 < ratio_5_to_1 < 7, f"5x scaling ratio seems off: {ratio_5_to_1}"
        assert 1.5 < ratio_10_to_5 < 2.5, f"2x scaling ratio seems off: {ratio_10_to_5}"

    def test_estimate_question_generation_cost_invalid_inputs(self, cost_estimator: CostEstimator):
        """Test error handling for invalid inputs."""
        fake_initiative_id = uuid4()
        
        # Test with non-existent initiative
        with pytest.raises(ValueError, match="Initiative .* not found"):
            cost_estimator.estimate_question_generation_cost(fake_initiative_id, 5)
        
        # Test with invalid question count
        with pytest.raises(ValueError, match="Question count must be positive"):
            cost_estimator.estimate_question_generation_cost(fake_initiative_id, 0)
        
        with pytest.raises(ValueError, match="Question count must be positive"):
            cost_estimator.estimate_question_generation_cost(fake_initiative_id, -1)

    def test_get_model_pricing(self, cost_estimator: CostEstimator):
        """Test getting model pricing information."""
        # Test valid model
        pricing = cost_estimator.get_model_pricing("claude-sonnet-4-5")
        assert "input" in pricing
        assert "output" in pricing
        assert pricing["input"] == 3.00
        assert pricing["output"] == 15.00
        
        # Test invalid model
        with pytest.raises(ValueError, match="Pricing not available for model"):
            cost_estimator.get_model_pricing("invalid-model")

    def test_get_available_models(self, cost_estimator: CostEstimator):
        """Test getting all available models."""
        models = cost_estimator.get_available_models()
        
        # Should contain known models
        assert "claude-sonnet-4-5" in models
        assert "claude-haiku-4-5" in models
        
        # Each model should have pricing info
        for model_name, pricing in models.items():
            assert "input" in pricing
            assert "output" in pricing
            assert isinstance(pricing["input"], (int, float))
            assert isinstance(pricing["output"], (int, float))

    def test_estimate_tokens_for_text(self, cost_estimator: CostEstimator):
        """Test token estimation logic."""
        # Empty text
        assert cost_estimator.estimate_tokens_for_text("") == 0
        
        # Short text
        short_text = "Hello"
        tokens = cost_estimator.estimate_tokens_for_text(short_text)
        assert tokens >= 1, "Should return at least 1 token for non-empty text"
        
        # Longer text should have more tokens
        long_text = "This is a much longer text that should result in more tokens being estimated."
        long_tokens = cost_estimator.estimate_tokens_for_text(long_text)
        assert long_tokens > tokens, f"Longer text should have more tokens: {long_tokens} vs {tokens}"
        
        # Rough validation of the 4-char-per-token heuristic
        expected_tokens = max(1, len(long_text) // 4)
        assert long_tokens == expected_tokens, f"Expected {expected_tokens} tokens, got {long_tokens}"

    def test_estimate_question_generation_tokens(self, cost_estimator: CostEstimator, test_initiative: Initiative):
        """Test token breakdown estimation for question generation."""
        question_count = 3
        tokens = cost_estimator.estimate_question_generation_tokens(test_initiative.id, question_count)
        
        # Should return dictionary with input and output tokens
        assert "input_tokens" in tokens
        assert "output_tokens" in tokens
        assert isinstance(tokens["input_tokens"], int)
        assert isinstance(tokens["output_tokens"], int)
        
        # Both should be positive
        assert tokens["input_tokens"] > 0
        assert tokens["output_tokens"] > 0
        
        # Input tokens should generally be higher than output tokens for question generation
        assert tokens["input_tokens"] > tokens["output_tokens"], \
            f"Input tokens ({tokens['input_tokens']}) should be higher than output tokens ({tokens['output_tokens']})"

    def test_estimate_question_generation_tokens_invalid_inputs(self, cost_estimator: CostEstimator):
        """Test error handling for token estimation."""
        fake_initiative_id = uuid4()
        
        # Test with non-existent initiative
        with pytest.raises(ValueError, match="Initiative .* not found"):
            cost_estimator.estimate_question_generation_tokens(fake_initiative_id, 5)
        
        # Test with invalid question count
        with pytest.raises(ValueError, match="Question count must be positive"):
            cost_estimator.estimate_question_generation_tokens(fake_initiative_id, 0)