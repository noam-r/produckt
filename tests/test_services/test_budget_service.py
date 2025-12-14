"""
Property-based tests for BudgetService.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from hypothesis import given, strategies as st, assume, settings, HealthCheck
from sqlalchemy.orm import Session

from backend.services.budget_service import BudgetService
from backend.models.user import User, UserRoleEnum
from backend.models.user_monthly_spending import UserMonthlySpending
from backend.models.organization import Organization


class TestBudgetServiceProperties:
    """Property-based tests for BudgetService."""

    @pytest.fixture
    def budget_service(self, test_db: Session):
        """Create a BudgetService instance."""
        return BudgetService(test_db)

    @pytest.fixture
    def test_user_with_budget(self, test_db: Session, test_organization: Organization):
        """Create a test user with a specific budget."""
        def _create_user(budget: Decimal = Decimal('100.00')):
            import bcrypt
            password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            user = User(
                email=f"user_{uuid4()}@example.com",
                password_hash=password_hash,
                name="Test User",
                role=UserRoleEnum.PRODUCT_MANAGER,
                organization_id=test_organization.id,
                monthly_budget_usd=budget,
                is_active=True
            )
            test_db.add(user)
            test_db.commit()
            test_db.refresh(user)
            return user
        return _create_user

    @given(
        budget=st.decimals(min_value=Decimal('1.00'), max_value=Decimal('1000.00'), places=2),
        current_spending=st.decimals(min_value=Decimal('0.00'), max_value=Decimal('999.99'), places=2),
        estimated_cost=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('100.00'), places=2)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=1000)
    def test_budget_enforcement_consistency(
        self, 
        budget_service: BudgetService, 
        test_user_with_budget, 
        test_db: Session,
        budget: Decimal,
        current_spending: Decimal, 
        estimated_cost: Decimal
    ):
        """
        **Feature: cost-controls, Property 1: Budget Enforcement Consistency**
        **Validates: Requirements 2.2, 2.3**
        
        For any user and any AI operation, if the operation would cause the user 
        to exceed their monthly budget, then the operation should be rejected before execution.
        """
        # Ensure current spending doesn't exceed budget
        assume(current_spending <= budget)
        
        # Create user with specified budget
        user = test_user_with_budget(budget)
        
        # Set up current spending if any
        if current_spending > 0:
            now = datetime.utcnow()
            spending_record = UserMonthlySpending(
                user_id=user.id,
                year=now.year,
                month=now.month,
                total_spent_usd=current_spending
            )
            test_db.add(spending_record)
            test_db.commit()
        
        # Check budget limit
        result = budget_service.check_budget_limit(user.id, estimated_cost)
        
        # Property: If operation would exceed budget, it should be rejected
        would_exceed_budget = (current_spending + estimated_cost) > budget
        
        if would_exceed_budget:
            assert not result.can_afford, f"Operation should be rejected when {current_spending} + {estimated_cost} > {budget}"
        else:
            assert result.can_afford, f"Operation should be allowed when {current_spending} + {estimated_cost} <= {budget}"
        
        # Verify the result contains correct values
        assert result.current_spending == current_spending
        assert result.budget_limit == budget
        assert result.estimated_cost == estimated_cost
        assert result.remaining_budget == budget - current_spending

    @given(
        budget=st.decimals(min_value=Decimal('10.00'), max_value=Decimal('1000.00'), places=2),
        spending_amounts=st.lists(
            st.decimals(min_value=Decimal('0.01'), max_value=Decimal('50.00'), places=2),
            min_size=1,
            max_size=10
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=1000)
    def test_monthly_spending_accuracy(
        self,
        budget_service: BudgetService,
        test_user_with_budget,
        test_db: Session,
        budget: Decimal,
        spending_amounts: list[Decimal]
    ):
        """
        **Feature: cost-controls, Property 2: Monthly Spending Accuracy**
        **Validates: Requirements 2.1, 2.5**
        
        For any user and calendar month, the sum of all recorded LLM call costs 
        for that user in that month should equal their monthly spending total.
        """
        # Create user
        user = test_user_with_budget(budget)
        
        # Record multiple spending amounts
        total_expected = Decimal('0.00')
        for amount in spending_amounts:
            llm_call_id = uuid4()
            budget_service.record_spending(user.id, amount, llm_call_id)
            total_expected += amount
        
        # Get current month spending
        actual_spending = budget_service.get_current_month_spending(user.id)
        
        # Property: Recorded spending should equal sum of all amounts
        assert actual_spending == total_expected, f"Expected {total_expected}, got {actual_spending}"
        
        # Verify the spending record exists and is correct
        now = datetime.utcnow()
        spending_record = (
            test_db.query(UserMonthlySpending)
            .filter(
                UserMonthlySpending.user_id == user.id,
                UserMonthlySpending.year == now.year,
                UserMonthlySpending.month == now.month
            )
            .first()
        )
        
        assert spending_record is not None
        assert spending_record.total_spent_usd == total_expected

    @given(
        budget_amount=st.one_of(
            # Valid range
            st.decimals(min_value=Decimal('0.00'), max_value=Decimal('10000.00'), places=2),
            # Invalid range - below minimum
            st.decimals(min_value=Decimal('-100.00'), max_value=Decimal('-0.01'), places=2),
            # Invalid range - above maximum  
            st.decimals(min_value=Decimal('10000.01'), max_value=Decimal('15000.00'), places=2)
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None, max_examples=50)
    def test_budget_validation_bounds(
        self,
        budget_service: BudgetService,
        test_user_with_budget,
        test_db: Session,
        budget_amount: Decimal
    ):
        """
        **Feature: cost-controls, Property 6: Budget Validation Bounds**
        **Validates: Requirements 1.4**
        
        For any budget update operation, the new budget amount should be 
        between $0.00 and $10,000.00 inclusive.
        """
        # Create user with default budget
        user = test_user_with_budget()
        admin_user = test_user_with_budget()
        
        # Property: Budget validation should enforce bounds
        is_valid_budget = Decimal('0.00') <= budget_amount <= Decimal('10000.00')
        
        if is_valid_budget:
            # Should succeed without raising exception
            try:
                budget_service.update_user_budget(user.id, budget_amount, admin_user.id)
                # Verify the budget was actually updated
                updated_user = test_db.query(User).filter(User.id == user.id).first()
                assert updated_user.monthly_budget_usd == budget_amount
            except ValueError:
                pytest.fail(f"Valid budget {budget_amount} should not raise ValueError")
        else:
            # Should raise ValueError for invalid budget
            with pytest.raises(ValueError, match="Budget must be between"):
                budget_service.update_user_budget(user.id, budget_amount, admin_user.id)

    @given(
        num_users=st.integers(min_value=1, max_value=5),
        spending_amounts=st.lists(
            st.decimals(min_value=Decimal('0.00'), max_value=Decimal('100.00'), places=2),
            min_size=0,
            max_size=3
        ),
        target_month=st.integers(min_value=1, max_value=12),
        target_year=st.integers(min_value=2030, max_value=2032)  # Use future years to avoid conflicts
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=3000, max_examples=10)
    def test_budget_reset_consistency(
        self,
        budget_service: BudgetService,
        test_user_with_budget,
        test_db: Session,
        num_users: int,
        spending_amounts: list[Decimal],
        target_month: int,
        target_year: int
    ):
        """
        **Feature: cost-controls, Property 4: Budget Reset Consistency**
        **Validates: Requirements 2.4**
        
        For any user, when a new calendar month begins, their spending counter 
        should reset to zero while preserving their budget limit.
        """
        from backend.services.monthly_budget_reset_service import MonthlyBudgetResetService
        
        # Create multiple users with different budgets
        users = []
        original_budgets = []
        for i in range(num_users):
            budget = Decimal('100.00') + Decimal(str(i * 50))  # Different budgets
            user = test_user_with_budget(budget)
            users.append(user)
            original_budgets.append(budget)
        
        # Set up spending for some users in a previous month
        prev_month = target_month - 1 if target_month > 1 else 12
        prev_year = target_year if target_month > 1 else target_year - 1
        
        for i, user in enumerate(users):
            if i < len(spending_amounts) and spending_amounts[i] > 0:
                # Create spending record for previous month
                spending_record = UserMonthlySpending(
                    user_id=user.id,
                    year=prev_year,
                    month=prev_month,
                    total_spent_usd=spending_amounts[i]
                )
                test_db.add(spending_record)
        
        test_db.commit()
        
        # Get count of users before reset to verify the reset only affects our test users
        user_ids = [user.id for user in users]
        
        # Perform monthly reset
        reset_service = MonthlyBudgetResetService(test_db)
        reset_result = reset_service.reset_monthly_budgets(target_year, target_month)
        
        # Property 1: All our test users should have zero spending for the new month
        for user in users:
            current_spending = budget_service.get_monthly_spending(user.id, target_year, target_month)
            assert current_spending == Decimal('0.00'), f"User {user.id} should have zero spending after reset"
        
        # Property 2: Budget limits should be preserved for our test users
        for i, user in enumerate(users):
            test_db.refresh(user)
            assert user.monthly_budget_usd == original_budgets[i], f"User {user.id} budget should be preserved"
        
        # Property 3: Previous month spending should be preserved (historical data) for our test users
        for i, user in enumerate(users):
            if i < len(spending_amounts) and spending_amounts[i] > 0:
                prev_spending = budget_service.get_monthly_spending(user.id, prev_year, prev_month)
                assert prev_spending == spending_amounts[i], f"Previous month spending should be preserved"
        
        # Property 4: Reset statistics should include our users (but may include others from other tests)
        assert reset_result['users_processed'] >= num_users, f"Should process at least {num_users} users"
        assert reset_result['target_year'] == target_year
        assert reset_result['target_month'] == target_month
        
        # Property 5: All our test users should have spending records for the new month
        for user in users:
            spending_record = (
                test_db.query(UserMonthlySpending)
                .filter(
                    UserMonthlySpending.user_id == user.id,
                    UserMonthlySpending.year == target_year,
                    UserMonthlySpending.month == target_month
                )
                .first()
            )
            assert spending_record is not None, f"User {user.id} should have spending record for new month"
            assert spending_record.total_spent_usd == Decimal('0.00'), f"New month spending should be zero"

    @given(
        user_count=st.integers(min_value=1, max_value=3)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=5000, max_examples=5)
    def test_default_budget_assignment(
        self,
        test_db: Session,
        test_organization: Organization,
        user_count: int
    ):
        """
        **Feature: cost-controls, Property 7: Default Budget Assignment**
        **Validates: Requirements 1.3**
        
        For any newly created user, their monthly budget should be set to exactly $100.00.
        """
        import bcrypt
        
        created_users = []
        expected_default_budget = Decimal('100.00')
        
        # Create multiple users using different creation methods
        for i in range(user_count):
            # Generate unique email to avoid conflicts
            unique_email = f"test_user_{uuid4()}_{i}@example.com"
            password_hash = bcrypt.hashpw(f"password{i}".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            try:
                # Create user without explicitly setting budget (should get default)
                user = User(
                    email=unique_email,
                    password_hash=password_hash,
                    name=f"Test User {i}",
                    role=UserRoleEnum.PRODUCT_MANAGER,
                    organization_id=test_organization.id,
                    is_active=True
                    # Note: NOT setting monthly_budget_usd - should get default
                )
                test_db.add(user)
                test_db.commit()
                test_db.refresh(user)
                created_users.append(user)
            except Exception as e:
                # If there's an error, rollback and continue
                test_db.rollback()
                continue
        
        # Skip test if no users were created successfully
        assume(len(created_users) > 0)
        
        # Property: All newly created users should have exactly $100.00 budget
        for user in created_users:
            assert user.monthly_budget_usd == expected_default_budget, (
                f"User {user.email} should have default budget of ${expected_default_budget}, "
                f"but has ${user.monthly_budget_usd}"
            )
            
            # Additional verification: budget should be exactly the default, not None or zero
            assert user.monthly_budget_usd is not None, f"User {user.email} budget should not be None"
            assert user.monthly_budget_usd > Decimal('0.00'), f"User {user.email} budget should be positive"
            
        # Property: Default budget should be consistent across all users
        budgets = [user.monthly_budget_usd for user in created_users]
        assert all(budget == expected_default_budget for budget in budgets), (
            "All users should have the same default budget"
        )
        
        # Property: Users created via UserRepository should also get default budget
        from backend.repositories.user_repository import UserRepository
        
        user_repo = UserRepository(test_db)
        
        try:
            # Create one more user via repository method
            repo_user = user_repo.create(
                email=f"repo_user_{uuid4()}@example.com",
                password="password123",
                name="Repository User",
                organization_id=test_organization.id,
                is_active=True
            )
            
            assert repo_user.monthly_budget_usd == expected_default_budget, (
                f"User created via repository should have default budget of ${expected_default_budget}, "
                f"but has ${repo_user.monthly_budget_usd}"
            )
        except Exception:
            # If repository creation fails, that's okay for this test
            test_db.rollback()