"""
End-to-end integration tests for cost control system.

This test suite validates the complete cost control workflow including:
- Question generation flow with budget checks
- Admin budget management workflows  
- User experience with budget limits
- All error scenarios and edge cases
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
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
from backend.repositories.user_repository import UserRepository


class TestCostControlsEndToEnd:
    """End-to-end integration tests for cost control system."""

    @pytest.fixture
    def admin_client(self, client, admin_user, test_organization):
        """Create an authenticated admin client."""
        from backend.auth.session import session_manager

        # Create session for admin user
        session = session_manager.create_session(
            user_id=admin_user.id,
            email=admin_user.email,
            name=admin_user.name,
            role=admin_user.role,
            organization_id=test_organization.id,
            organization_name=test_organization.name
        )

        # Set session cookie on client
        client.cookies.set("session_id", session.session_id)
        return client

    @pytest.fixture
    def test_context(self, test_db: Session, test_organization: Organization, test_user: User):
        """Create a test organizational context."""
        context = Context(
            organization_id=test_organization.id,
            company_mission="Test company mission",
            strategic_objectives="Test strategic objectives",
            target_markets="Test target markets",
            competitive_landscape="Test competitive landscape",
            technical_constraints="Test technical constraints",
            version=1,
            is_current=True,
            created_by=test_user.id
        )
        test_db.add(context)
        test_db.commit()
        test_db.refresh(context)
        return context

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

    def test_complete_question_generation_flow_with_budget_checks(
        self, 
        test_client: TestClient, 
        test_db: Session,
        test_user: User,
        test_context: Context,
        test_initiative_with_questions
    ):
        """
        Test complete question generation flow with budget checks.
        
        Requirements: All - Complete workflow validation
        """
        initiative = test_initiative_with_questions['initiative']
        
        # Set user budget to a low amount
        test_user.monthly_budget_usd = Decimal('5.00')
        test_db.commit()

        # Mock cost estimator to return high cost
        with patch('backend.services.cost_estimator.CostEstimator.estimate_question_generation_cost') as mock_cost:
            mock_cost.return_value = Decimal('10.00')  # Higher than budget
            
            # Attempt question generation - should fail due to budget
            response = test_client.post(f"/api/agents/initiatives/{initiative.id}/generate-questions")
            
            assert response.status_code == 402  # Payment Required
            assert "Budget limit exceeded" in response.json()["detail"]["error"]
            assert "$5.00" in response.json()["detail"]["budget_limit"]
            assert "$10.00" in response.json()["detail"]["estimated_cost"]

        # Increase budget and try again
        test_user.monthly_budget_usd = Decimal('20.00')
        test_db.commit()

        with patch('backend.services.cost_estimator.CostEstimator.estimate_question_generation_cost') as mock_cost:
            mock_cost.return_value = Decimal('2.00')  # Within budget
            
            # Mock the background job execution
            with patch('backend.routers.agents.execute_job_in_background') as mock_execute:
                response = test_client.post(f"/api/agents/initiatives/{initiative.id}/generate-questions")
                
                assert response.status_code == 200
                assert "job_id" in response.json()
                mock_execute.assert_called_once()

    def test_question_throttling_in_generation_flow(
        self,
        test_client: TestClient,
        test_db: Session,
        test_user: User,
        test_context: Context,
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

        # Set high budget to avoid budget issues
        test_user.monthly_budget_usd = Decimal('100.00')
        test_db.commit()

        # Attempt question generation - should fail due to throttling
        response = test_client.post(f"/api/agents/initiatives/{initiative.id}/generate-questions")
        
        assert response.status_code == 429  # Too Many Requests
        assert "Question generation throttled" in response.json()["detail"]["error"]
        assert response.json()["detail"]["unanswered_count"] == 6
        assert response.json()["detail"]["unanswered_limit"] == 5

    def test_initiative_question_limit_enforcement(
        self,
        test_client: TestClient,
        test_db: Session,
        test_user: User,
        test_context: Context,
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

        # Set high budget to avoid budget issues
        test_user.monthly_budget_usd = Decimal('100.00')
        test_db.commit()

        # Answer some questions to avoid throttling (keep only 2 unanswered)
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

        # Attempt question generation - should fail due to question limit
        response = test_client.post(f"/api/agents/initiatives/{initiative.id}/generate-questions")
        
        assert response.status_code == 400
        assert "Question limit exceeded" in response.json()["detail"]["error"]
        assert response.json()["detail"]["current_count"] == 5
        assert response.json()["detail"]["max_questions"] == 6

    def test_admin_budget_management_workflow(
        self,
        admin_client: TestClient,
        test_db: Session,
        test_user: User,
        admin_user: User
    ):
        """
        Test complete admin budget management workflow.
        
        Requirements: 1.1, 1.2, 1.4, 1.5 - Admin budget management
        """
        # 1. List users and verify budget display
        response = admin_client.get("/api/admin/users")
        assert response.status_code == 200
        
        users_data = response.json()
        assert "users" in users_data
        assert len(users_data["users"]) >= 1
        
        # Find our test user
        test_user_data = None
        for user_data in users_data["users"]:
            if user_data["id"] == str(test_user.id):
                test_user_data = user_data
                break
        
        assert test_user_data is not None
        assert "budget" in test_user_data
        assert test_user_data["budget"]["monthly_budget_usd"] == 100.00  # Default budget

        # 2. Update user budget
        update_data = {
            "monthly_budget_usd": 250.50
        }
        response = admin_client.put(f"/api/admin/users/{test_user.id}/budget", json=update_data)
        assert response.status_code == 200
        
        response_data = response.json()
        assert "Budget updated successfully" in response_data["message"]
        assert response_data["user"]["budget"]["monthly_budget_usd"] == 250.50

        # 3. Verify budget validation - invalid amount (too high)
        invalid_data = {
            "monthly_budget_usd": 15000.00  # Above $10,000 limit
        }
        response = admin_client.put(f"/api/admin/users/{test_user.id}/budget", json=invalid_data)
        assert response.status_code == 400
        assert "Budget must be between" in response.json()["detail"]

        # 4. Verify budget validation - invalid amount (negative)
        invalid_data = {
            "monthly_budget_usd": -50.00
        }
        response = admin_client.put(f"/api/admin/users/{test_user.id}/budget", json=invalid_data)
        assert response.status_code == 400
        assert "Budget must be between" in response.json()["detail"]

        # 5. Get individual user and verify budget update
        response = admin_client.get(f"/api/admin/users/{test_user.id}")
        assert response.status_code == 200
        
        user_data = response.json()
        assert user_data["budget"]["monthly_budget_usd"] == 250.50
        assert user_data["budget"]["budget_updated_by"] == str(admin_user.id)
        assert user_data["budget"]["budget_updated_at"] is not None

    def test_budget_monitoring_dashboard(
        self,
        admin_client: TestClient,
        test_db: Session,
        test_organization: Organization
    ):
        """
        Test admin budget monitoring dashboard functionality.
        
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

        # 1. Test budget overview
        response = admin_client.get("/api/admin/budget/overview")
        assert response.status_code == 200
        
        overview_data = response.json()
        assert "summary" in overview_data
        assert "users" in overview_data
        
        summary = overview_data["summary"]
        assert summary["users_over_budget"] == 1  # user3
        assert summary["users_near_limit"] == 1   # user2 (90% utilization)
        assert summary["total_budget_usd"] >= 450.0  # At least our test users
        assert summary["total_spending_usd"] >= 390.0  # At least our test users

        # 2. Test budget alerts
        response = admin_client.get("/api/admin/budget/alerts")
        assert response.status_code == 200
        
        alerts_data = response.json()
        assert alerts_data["critical_alerts"] == 1  # user3 over budget
        assert alerts_data["warning_alerts"] == 1   # user2 near limit
        assert len(alerts_data["alerts"]) == 2
        
        # Verify alert details
        critical_alerts = [a for a in alerts_data["alerts"] if a["alert_level"] == "critical"]
        warning_alerts = [a for a in alerts_data["alerts"] if a["alert_level"] == "warning"]
        
        assert len(critical_alerts) == 1
        assert critical_alerts[0]["is_over_budget"] is True
        
        assert len(warning_alerts) == 1
        assert warning_alerts[0]["utilization_percentage"] >= 80.0

        # 3. Test spending trends (basic functionality)
        response = admin_client.get("/api/admin/budget/spending-trends?months=3")
        assert response.status_code == 200
        
        trends_data = response.json()
        assert "trends" in trends_data
        assert trends_data["period_months"] == 3

    def test_user_budget_visibility_and_experience(
        self,
        test_client: TestClient,
        test_db: Session,
        test_user: User
    ):
        """
        Test user budget visibility and experience with limits.
        
        Requirements: 5.1, 5.2, 5.3 - User budget visibility
        """
        # Set user budget and spending
        test_user.monthly_budget_usd = Decimal('100.00')
        test_db.commit()
        
        # Add some spending (80% of budget)
        now = datetime.utcnow()
        spending_record = UserMonthlySpending(
            user_id=test_user.id,
            year=now.year,
            month=now.month,
            total_spent_usd=Decimal('80.00')
        )
        test_db.add(spending_record)
        test_db.commit()

        # Test user profile endpoint (assuming it exists)
        # Note: This would need to be implemented in the actual API
        # For now, we'll test the budget service directly
        budget_service = BudgetService(test_db)
        budget_status = budget_service.get_budget_status_with_warnings(test_user.id)
        
        assert budget_status["budget_limit"] == Decimal('100.00')
        assert budget_status["current_spending"] == Decimal('80.00')
        assert budget_status["remaining_budget"] == Decimal('20.00')
        assert budget_status["utilization_percentage"] == 80.0
        assert budget_status["is_near_limit"] is True
        assert budget_status["has_warning"] is True
        assert "80%" in budget_status["warning_message"]

    def test_error_scenarios_and_edge_cases(
        self,
        test_client: TestClient,
        admin_client: TestClient,
        test_db: Session,
        test_user: User,
        test_context: Context
    ):
        """
        Test all error scenarios and edge cases.
        
        Requirements: All - Error handling validation
        """
        # 1. Test question generation with non-existent initiative
        fake_initiative_id = uuid4()
        response = test_client.post(f"/api/agents/initiatives/{fake_initiative_id}/generate-questions")
        assert response.status_code == 404
        assert "Initiative not found" in response.json()["detail"]

        # 2. Test budget update with non-existent user
        fake_user_id = uuid4()
        update_data = {"monthly_budget_usd": 150.00}
        response = admin_client.put(f"/api/admin/users/{fake_user_id}/budget", json=update_data)
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

        # 3. Test cost estimation with invalid data
        cost_estimator = CostEstimator(test_db)
        
        with pytest.raises(ValueError, match="Initiative .* not found"):
            cost_estimator.estimate_question_generation_cost(fake_initiative_id, 5)
        
        with pytest.raises(ValueError, match="Question count must be positive"):
            cost_estimator.estimate_question_generation_cost(fake_initiative_id, 0)

        # 4. Test budget service with invalid amounts
        budget_service = BudgetService(test_db)
        
        with pytest.raises(ValueError, match="Budget must be between"):
            budget_service.update_user_budget(test_user.id, Decimal('-10.00'), test_user.id)
        
        with pytest.raises(ValueError, match="Budget must be between"):
            budget_service.update_user_budget(test_user.id, Decimal('15000.00'), test_user.id)

        # 5. Test question throttle service with invalid data
        throttle_service = QuestionThrottleService(test_db)
        
        # Non-existent initiative should return 0 counts
        assert throttle_service.count_unanswered_questions(fake_initiative_id) == 0
        assert throttle_service.count_total_questions(fake_initiative_id) == 0

    def test_monthly_budget_reset_integration(
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

    def test_concurrent_budget_operations(
        self,
        test_db: Session,
        test_organization: Organization
    ):
        """
        Test concurrent budget operations for race condition handling.
        
        Requirements: 2.1, 2.5 - Concurrent spending tracking
        """
        import bcrypt
        from concurrent.futures import ThreadPoolExecutor
        import threading
        
        # Create a user
        password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user = User(
            email="concurrent_user@test.com",
            password_hash=password_hash,
            name="Concurrent User",
            role=UserRoleEnum.PRODUCT_MANAGER,
            organization_id=test_organization.id,
            is_active=True,
            monthly_budget_usd=Decimal('100.00')
        )
        test_db.add(user)
        test_db.commit()

        # Function to record spending
        def record_spending(amount):
            # Create new session for each thread
            from backend.database import SessionLocal
            db = SessionLocal()
            try:
                budget_service = BudgetService(db)
                budget_service.record_spending(user.id, Decimal(str(amount)), uuid4())
                db.commit()
            finally:
                db.close()

        # Record multiple spending amounts concurrently
        amounts = [5.00, 10.00, 15.00, 20.00, 25.00]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(record_spending, amount) for amount in amounts]
            
            # Wait for all to complete
            for future in futures:
                future.result()

        # Verify total spending is correct
        budget_service = BudgetService(test_db)
        total_spending = budget_service.get_current_month_spending(user.id)
        expected_total = sum(Decimal(str(amount)) for amount in amounts)
        
        assert total_spending == expected_total

    def test_default_values_integration(
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

    def test_audit_logging_integration(
        self,
        admin_client: TestClient,
        test_db: Session,
        test_user: User,
        admin_user: User
    ):
        """
        Test that budget changes are properly logged for audit purposes.
        
        Requirements: 1.5 - Audit logging for budget changes
        """
        from backend.models.audit_log import AuditLog
        
        # Record initial audit log count
        initial_count = test_db.query(AuditLog).count()
        
        # Update user budget
        update_data = {"monthly_budget_usd": 175.00}
        response = admin_client.put(f"/api/admin/users/{test_user.id}/budget", json=update_data)
        assert response.status_code == 200
        
        # Verify audit log was created
        final_count = test_db.query(AuditLog).count()
        assert final_count > initial_count
        
        # Find the budget change log entry
        budget_log = (
            test_db.query(AuditLog)
            .filter(
                AuditLog.action == "budget_change",
                AuditLog.user_id == test_user.id,
                AuditLog.actor_id == admin_user.id
            )
            .order_by(AuditLog.created_at.desc())
            .first()
        )
        
        assert budget_log is not None
        assert budget_log.details["old_budget"] == 100.0  # Original default
        assert budget_log.details["new_budget"] == 175.0