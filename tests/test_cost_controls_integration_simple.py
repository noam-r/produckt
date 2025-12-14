"""
Simplified end-to-end integration tests for cost control system.

This test suite validates the complete cost control workflow using service-level integration
without requiring the full FastAPI client setup.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.models.user import User, UserRoleEnum
from backend.models.organization import Organization
from backend.models.initiative import Initiative, InitiativeStatus
from backend.models.question import Question, QuestionCategory, QuestionPriority
from backend.models.answer import Answer, AnswerStatus
from backend.models.user_monthly_spending import UserMonthlySpending
from backend.models.context import Context
from backend.services.budget_service import BudgetService
from backend.services.question_throttle_service import QuestionThrottleService
from backend.services.cost_estimator import CostEstimator
from backend.services.exceptions import BudgetExceededError, QuestionGenerationThrottledError, InitiativeQuestionLimitError
from backend.repositories.user_repository import UserRepository


class TestCostControlsIntegrationSimple:
    """Simplified integration tests for cost control system."""

    @pytest.fixture
    def test_initiative_with_questions(self, test_db: Session, test_organization: Organization, test_user: User):
        """Create a test initiative with various questions."""
        # Create initiative
        initiative = Initiative(
            title="Test Initiative",
            description="Test initiative description",
            status=InitiativeStatus.DRAFT,
            organization_id=test_organization.id,
            created_by=test_user.id,
            iteration_count=1,
            max_questions=50
        )
        test_db.add(initiative)
        test_db.flush()

        # Create 3 unanswered questions
        unanswered_questions = []
        for i in range(3):
            question = Question(
                initiative_id=initiative.id,
                iteration=1,
                category=QuestionCategory.BUSINESS_DEV,
                priority=QuestionPriority.P1,
                question_text=f"Unanswered question {i+1}",
                rationale=f"Test rationale {i+1}"
            )
            test_db.add(question)
            unanswered_questions.append(question)

        # Create 2 answered questions
        answered_questions = []
        for i in range(2):
            question = Question(
                initiative_id=initiative.id,
                iteration=1,
                category=QuestionCategory.BUSINESS_DEV,
                priority=QuestionPriority.P1,
                question_text=f"Answered question {i+1}",
                rationale=f"Test rationale {i+1}"
            )
            test_db.add(question)
            test_db.flush()

            # Add answer
            answer = Answer(
                question_id=question.id,
                answer_status=AnswerStatus.ANSWERED,
                answer_text=f"Answer to question {i+1}",
                answered_by=test_user.id
            )
            test_db.add(answer)
            answered_questions.append(question)

        test_db.commit()
        test_db.refresh(initiative)

        return {
            'initiative': initiative,
            'unanswered_questions': unanswered_questions,
            'answered_questions': answered_questions
        }

    def test_budget_enforcement_workflow(
        self, 
        test_db: Session,
        test_user: User,
        test_initiative_with_questions
    ):
        """
        Test complete budget enforcement workflow.
        
        Requirements: 2.2, 2.3 - Budget enforcement
        """
        initiative = test_initiative_with_questions['initiative']
        
        # Set user budget to a low amount
        test_user.monthly_budget_usd = Decimal('5.00')
        test_db.commit()

        budget_service = BudgetService(test_db)
        cost_estimator = CostEstimator(test_db)
        
        # Estimate a high cost that exceeds budget
        estimated_cost = Decimal('10.00')  # Higher than budget
        
        # Check budget limit - should fail
        result = budget_service.check_budget_limit(test_user.id, estimated_cost)
        assert not result.can_afford
        assert result.current_spending == Decimal('0.00')
        assert result.budget_limit == Decimal('5.00')
        assert result.estimated_cost == estimated_cost
        
        # Test exception-raising version
        with pytest.raises(BudgetExceededError) as exc_info:
            budget_service.check_budget_limit_or_raise(test_user.id, estimated_cost)
        
        assert exc_info.value.current_spending == Decimal('0.00')
        assert exc_info.value.budget_limit == Decimal('5.00')
        assert exc_info.value.estimated_cost == estimated_cost

        # Increase budget and try again
        test_user.monthly_budget_usd = Decimal('20.00')
        test_db.commit()

        # Now it should pass
        result = budget_service.check_budget_limit(test_user.id, estimated_cost)
        assert result.can_afford
        assert result.budget_limit == Decimal('20.00')
        assert result.remaining_budget == Decimal('20.00')

        # Should not raise exception
        budget_service.check_budget_limit_or_raise(test_user.id, estimated_cost)

    def test_question_throttling_workflow(
        self,
        test_db: Session,
        test_user: User,
        test_initiative_with_questions
    ):
        """
        Test question throttling prevents generation when too many unanswered questions exist.
        
        Requirements: 3.2, 3.3 - Question generation throttling
        """
        initiative = test_initiative_with_questions['initiative']
        
        # Add 3 more unanswered questions to reach the limit (total 6, limit is 5)
        for i in range(3):
            question = Question(
                initiative_id=initiative.id,
                iteration=1,
                category=QuestionCategory.BUSINESS_DEV,
                priority=QuestionPriority.P1,
                question_text=f"Extra unanswered question {i+1}",
                rationale=f"Test rationale {i+1}"
            )
            test_db.add(question)
        test_db.commit()

        throttle_service = QuestionThrottleService(test_db)
        
        # Check throttling - should fail
        result = throttle_service.can_generate_questions(initiative.id)
        assert not result.can_generate
        assert result.unanswered_count == 6
        assert "unanswered questions" in result.reason.lower()
        
        # Test exception-raising version
        with pytest.raises(QuestionGenerationThrottledError) as exc_info:
            throttle_service.check_question_limits_or_raise(initiative.id)
        
        assert exc_info.value.unanswered_count == 6
        assert exc_info.value.limit == 5

        # Answer some questions to get below limit
        unanswered_questions = test_initiative_with_questions['unanswered_questions']
        for question in unanswered_questions[1:]:  # Answer all but first
            answer = Answer(
                question_id=question.id,
                answer_status=AnswerStatus.ANSWERED,
                answer_text="Test answer",
                answered_by=test_user.id
            )
            test_db.add(answer)
        test_db.commit()

        # Now it should pass (4 unanswered questions, below limit of 5)
        result = throttle_service.can_generate_questions(initiative.id)
        assert result.can_generate
        assert result.unanswered_count == 4

        # Should not raise exception
        throttle_service.check_question_limits_or_raise(initiative.id)

    def test_initiative_question_limit_workflow(
        self,
        test_db: Session,
        test_user: User,
        test_initiative_with_questions
    ):
        """
        Test initiative question limit enforcement.
        
        Requirements: 5.3 - Initiative question limit enforcement
        """
        initiative = test_initiative_with_questions['initiative']
        
        # Set initiative to have only 6 questions max (currently has 5)
        initiative.max_questions = 6
        test_db.commit()

        throttle_service = QuestionThrottleService(test_db)
        
        # Answer questions to avoid throttling (keep only 2 unanswered)
        unanswered_questions = test_initiative_with_questions['unanswered_questions']
        for question in unanswered_questions[1:]:  # Answer all but first
            answer = Answer(
                question_id=question.id,
                answer_status=AnswerStatus.ANSWERED,
                answer_text="Test answer",
                answered_by=test_user.id
            )
            test_db.add(answer)
        test_db.commit()

        # Check question limits - should fail due to total question limit
        result = throttle_service.check_question_limits(initiative.id, 2)  # Try to add 2 more
        assert not result.can_add
        assert result.total_count == 5
        assert result.max_questions == 6
        assert "maximum limit" in result.reason.lower()
        
        # Test exception-raising version
        with pytest.raises(InitiativeQuestionLimitError) as exc_info:
            throttle_service.check_question_limits_or_raise(initiative.id, 2)
        
        assert exc_info.value.current_count == 5
        assert exc_info.value.max_limit == 6

        # Try adding just 1 question - should pass
        result = throttle_service.check_question_limits(initiative.id, 1)
        assert result.can_add

        # Should not raise exception
        throttle_service.check_question_limits_or_raise(initiative.id, 1)

    def test_budget_management_workflow(
        self,
        test_db: Session,
        test_user: User,
        admin_user: User
    ):
        """
        Test budget management workflow.
        
        Requirements: 1.1, 1.2, 1.4, 1.5 - Admin budget management
        """
        budget_service = BudgetService(test_db)
        
        # Verify initial budget
        assert test_user.monthly_budget_usd == Decimal('100.00')  # Default budget
        
        # Update user budget
        budget_service.update_user_budget(
            user_id=test_user.id,
            new_budget=Decimal('250.50'),
            updated_by=admin_user.id
        )
        
        test_db.refresh(test_user)
        assert test_user.monthly_budget_usd == Decimal('250.50')
        assert test_user.budget_updated_by == admin_user.id
        assert test_user.budget_updated_at is not None

        # Test budget validation - invalid amount (too high)
        with pytest.raises(ValueError, match="Budget must be between"):
            budget_service.update_user_budget(
                user_id=test_user.id,
                new_budget=Decimal('15000.00'),  # Above $10,000 limit
                updated_by=admin_user.id
            )

        # Test budget validation - invalid amount (negative)
        with pytest.raises(ValueError, match="Budget must be between"):
            budget_service.update_user_budget(
                user_id=test_user.id,
                new_budget=Decimal('-50.00'),
                updated_by=admin_user.id
            )

        # Verify budget wasn't changed by invalid attempts
        test_db.refresh(test_user)
        assert test_user.monthly_budget_usd == Decimal('250.50')

    def test_budget_monitoring_workflow(
        self,
        test_db: Session,
        test_organization: Organization
    ):
        """
        Test budget monitoring workflow.
        
        Requirements: 4.1, 4.2, 4.3, 4.4 - Budget monitoring and reporting
        """
        # Create users with different spending patterns
        import bcrypt
        users_data = [
            {"email": "user1@test.com", "budget": Decimal("100.00"), "spending": Decimal("50.00")},
            {"email": "user2@test.com", "budget": Decimal("200.00"), "spending": Decimal("180.00")},  # Near limit
            {"email": "user3@test.com", "budget": Decimal("150.00"), "spending": Decimal("160.00")},  # Over budget
        ]
        
        created_users = []
        for user_data in users_data:
            password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            user = User(
                email=user_data["email"],
                password_hash=password_hash,
                name=f"Test User {user_data['email']}",
                role=UserRoleEnum.PRODUCT_MANAGER,
                organization_id=test_organization.id,
                is_active=True,
                monthly_budget_usd=user_data["budget"]
            )
            test_db.add(user)
            test_db.flush()
            
            # Create spending record
            now = datetime.utcnow()
            spending_record = UserMonthlySpending(
                user_id=user.id,
                year=now.year,
                month=now.month,
                total_spent_usd=user_data["spending"]
            )
            test_db.add(spending_record)
            created_users.append(user)
        
        test_db.commit()

        budget_service = BudgetService(test_db)
        
        # Test budget status for each user
        user_statuses = []
        for user in created_users:
            status = budget_service.get_budget_status_with_warnings(user.id)
            user_statuses.append(status)
        
        # Verify user1 (50% utilization)
        assert user_statuses[0]["utilization_percentage"] == 50.0
        assert not user_statuses[0]["is_over_budget"]
        assert not user_statuses[0]["is_near_limit"]
        assert not user_statuses[0]["has_warning"]
        
        # Verify user2 (90% utilization - near limit)
        assert user_statuses[1]["utilization_percentage"] == 90.0
        assert not user_statuses[1]["is_over_budget"]
        assert user_statuses[1]["is_near_limit"]
        assert user_statuses[1]["has_warning"]
        assert "90.0%" in user_statuses[1]["warning_message"]
        
        # Verify user3 (over budget)
        assert user_statuses[2]["utilization_percentage"] > 100.0
        assert user_statuses[2]["is_over_budget"]
        assert user_statuses[2]["has_warning"]
        assert "106.7%" in user_statuses[2]["warning_message"]

    def test_monthly_budget_reset_workflow(
        self,
        test_db: Session,
        test_organization: Organization
    ):
        """
        Test monthly budget reset functionality.
        
        Requirements: 2.4 - Monthly budget reset
        """
        from backend.services.monthly_budget_reset_service import MonthlyBudgetResetService
        
        # Create users with spending in previous month
        import bcrypt
        users = []
        for i in range(3):
            password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            user = User(
                email=f"reset_user_{i}@test.com",
                password_hash=password_hash,
                name=f"Reset User {i}",
                role=UserRoleEnum.PRODUCT_MANAGER,
                organization_id=test_organization.id,
                is_active=True,
                monthly_budget_usd=Decimal('100.00')
            )
            test_db.add(user)
            users.append(user)
        
        test_db.flush()

        # Add spending for previous month
        prev_month = datetime.utcnow().replace(day=1) - timedelta(days=1)
        for i, user in enumerate(users):
            spending_record = UserMonthlySpending(
                user_id=user.id,
                year=prev_month.year,
                month=prev_month.month,
                total_spent_usd=Decimal(f'{(i+1)*25}.00')  # $25, $50, $75
            )
            test_db.add(spending_record)
        
        test_db.commit()

        # Perform reset for current month
        reset_service = MonthlyBudgetResetService(test_db)
        current_date = datetime.utcnow()
        result = reset_service.reset_monthly_budgets(current_date.year, current_date.month)

        # Verify reset results
        assert result['users_processed'] >= 3
        assert result['target_year'] == current_date.year
        assert result['target_month'] == current_date.month

        # Verify all users have zero spending for current month
        budget_service = BudgetService(test_db)
        for user in users:
            current_spending = budget_service.get_current_month_spending(user.id)
            assert current_spending == Decimal('0.00')

        # Verify previous month spending is preserved
        for i, user in enumerate(users):
            prev_spending = budget_service.get_monthly_spending(user.id, prev_month.year, prev_month.month)
            expected_spending = Decimal(f'{(i+1)*25}.00')
            assert prev_spending == expected_spending

    def test_default_values_workflow(
        self,
        test_db: Session,
        test_organization: Organization
    ):
        """
        Test that default values are properly assigned during user and initiative creation.
        
        Requirements: 1.3, 5.1 - Default budget and question limit assignment
        """
        # Test user creation with default budget
        user_repo = UserRepository(test_db)
        new_user = user_repo.create(
            email="default_test@example.com",
            password="password123",
            name="Default Test User",
            organization_id=test_organization.id,
            is_active=True
        )
        
        # Verify default budget
        assert new_user.monthly_budget_usd == Decimal('100.00')
        
        # Test initiative creation with default question limit
        initiative = Initiative(
            title="Default Test Initiative",
            description="Test description",
            status=InitiativeStatus.DRAFT,
            organization_id=test_organization.id,
            created_by=new_user.id,
            iteration_count=0
            # max_questions should get default value from model
        )
        test_db.add(initiative)
        test_db.commit()
        test_db.refresh(initiative)
        
        # Verify default question limit
        assert initiative.max_questions == 50

    def test_cost_estimation_workflow(
        self,
        test_db: Session,
        test_initiative_with_questions
    ):
        """
        Test cost estimation functionality.
        
        Requirements: 2.1, 2.3 - Cost estimation
        """
        initiative = test_initiative_with_questions['initiative']
        cost_estimator = CostEstimator(test_db)
        
        # Test question generation cost estimation
        estimated_cost = cost_estimator.estimate_question_generation_cost(initiative.id, 5)
        assert estimated_cost > Decimal('0')
        assert estimated_cost < Decimal('1.00')  # Should be reasonable
        
        # Test LLM call cost estimation
        llm_cost = cost_estimator.estimate_llm_call_cost("claude-sonnet-4-5", 1000, 500)
        expected_cost = Decimal('0.010500')  # (1000/1M * $3) + (500/1M * $15)
        assert llm_cost == expected_cost
        
        # Test token estimation
        tokens = cost_estimator.estimate_tokens_for_text("Hello world")
        assert tokens >= 1
        
        # Test with existing questions (should be higher due to context)
        cost_with_context = cost_estimator.estimate_question_generation_cost(initiative.id, 3)
        
        # Create new initiative without questions for comparison
        new_initiative = Initiative(
            title="New Initiative",
            description="New Description",
            status=InitiativeStatus.DRAFT,
            organization_id=initiative.organization_id,
            created_by=initiative.created_by,
            iteration_count=0,
            max_questions=50
        )
        test_db.add(new_initiative)
        test_db.commit()
        test_db.refresh(new_initiative)
        
        cost_without_context = cost_estimator.estimate_question_generation_cost(new_initiative.id, 3)
        
        # Cost with existing questions should be higher due to context overhead
        assert cost_with_context > cost_without_context

    def test_error_scenarios_workflow(
        self,
        test_db: Session,
        test_user: User
    ):
        """
        Test error scenarios and edge cases.
        
        Requirements: All - Error handling validation
        """
        budget_service = BudgetService(test_db)
        cost_estimator = CostEstimator(test_db)
        throttle_service = QuestionThrottleService(test_db)
        
        # Test with non-existent initiative
        fake_initiative_id = uuid4()
        
        with pytest.raises(ValueError, match="Initiative .* not found"):
            cost_estimator.estimate_question_generation_cost(fake_initiative_id, 5)
        
        with pytest.raises(ValueError, match="Question count must be positive"):
            cost_estimator.estimate_question_generation_cost(fake_initiative_id, 0)

        # Test budget service with invalid amounts
        with pytest.raises(ValueError, match="Budget must be between"):
            budget_service.update_user_budget(test_user.id, Decimal('-10.00'), test_user.id)
        
        with pytest.raises(ValueError, match="Budget must be between"):
            budget_service.update_user_budget(test_user.id, Decimal('15000.00'), test_user.id)

        # Test question throttle service with invalid data
        # Non-existent initiative should return 0 counts
        assert throttle_service.count_unanswered_questions(fake_initiative_id) == 0
        assert throttle_service.count_total_questions(fake_initiative_id) == 0

        # Test cost estimator with invalid inputs
        with pytest.raises(ValueError, match="Token counts must be non-negative"):
            cost_estimator.estimate_llm_call_cost("claude-sonnet-4-5", -1, 0)
        
        with pytest.raises(ValueError, match="Pricing not available for model"):
            cost_estimator.get_model_pricing("invalid-model")