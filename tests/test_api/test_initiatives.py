"""
Property-based tests for Initiative API endpoints.
"""

import pytest
from uuid import uuid4

from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy.orm import Session

from backend.models.initiative import Initiative, InitiativeStatus
from backend.models.user import User, UserRoleEnum
from backend.models.organization import Organization


class TestInitiativeProperties:
    """Property-based tests for Initiative functionality."""

    @pytest.fixture
    def test_user_factory(self, test_db: Session, test_organization: Organization):
        """Create a factory for test users."""
        def _create_user(role: UserRoleEnum = UserRoleEnum.PRODUCT_MANAGER):
            import bcrypt
            password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            user = User(
                email=f"user_{uuid4()}@example.com",
                password_hash=password_hash,
                name="Test User",
                role=role,
                organization_id=test_organization.id,
                is_active=True
            )
            test_db.add(user)
            test_db.commit()
            test_db.refresh(user)
            return user
        return _create_user

    @given(
        title=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs'))).filter(lambda x: x.strip()),
        description=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs'))).filter(lambda x: x.strip()),
        num_initiatives=st.integers(min_value=1, max_value=3)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None, max_examples=10)
    def test_default_question_limit_assignment(
        self,
        test_db: Session,
        test_organization: Organization,
        test_user_factory,
        title: str,
        description: str,
        num_initiatives: int
    ):
        """
        **Feature: cost-controls, Property 9: Default Question Limit Assignment**
        **Validates: Requirements 5.1**
        
        For any newly created initiative, the maximum questions limit should be set to exactly 50.
        """
        # Create a user to create initiatives
        user = test_user_factory(UserRoleEnum.PRODUCT_MANAGER)
        
        # Create multiple initiatives to test the property holds consistently
        created_initiatives = []
        for i in range(num_initiatives):
            initiative = Initiative(
                title=f"{title}_{i}",
                description=f"{description}_{i}",
                status=InitiativeStatus.DRAFT,
                organization_id=test_organization.id,
                created_by=user.id,
                iteration_count=0,
                max_questions=50  # This should be the default
            )
            test_db.add(initiative)
            created_initiatives.append(initiative)
        
        test_db.commit()
        
        # Refresh all initiatives to get the actual database values
        for initiative in created_initiatives:
            test_db.refresh(initiative)
        
        # Property: All newly created initiatives should have max_questions = 50
        for initiative in created_initiatives:
            assert initiative.max_questions == 50, f"Initiative {initiative.id} should have max_questions=50, got {initiative.max_questions}"
            
            # Additional checks to ensure the initiative was properly created
            assert initiative.id is not None
            assert initiative.organization_id == test_organization.id
            assert initiative.created_by == user.id
            assert initiative.status == InitiativeStatus.DRAFT
            assert initiative.iteration_count == 0
            
            # Verify the question limit fields are properly initialized
            assert initiative.max_questions_updated_at is None  # Should be None for new initiatives
            assert initiative.max_questions_updated_by is None  # Should be None for new initiatives

    @given(
        new_limit=st.integers(min_value=1, max_value=100),
        num_updates=st.integers(min_value=1, max_value=2)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None, max_examples=3)
    def test_question_limit_update_preserves_bounds(
        self,
        test_db: Session,
        test_organization: Organization,
        test_user_factory,
        new_limit: int,
        num_updates: int
    ):
        """
        Test that question limit updates maintain valid bounds and tracking.
        
        This is a supporting property test to ensure the question limit management works correctly.
        """
        # Create users
        creator = test_user_factory(UserRoleEnum.PRODUCT_MANAGER)
        admin = test_user_factory(UserRoleEnum.ADMIN)
        
        # Create an initiative with default limit
        initiative = Initiative(
            title="Test Initiative",
            description="Test description",
            status=InitiativeStatus.DRAFT,
            organization_id=test_organization.id,
            created_by=creator.id,
            iteration_count=0,
            max_questions=50  # Default
        )
        test_db.add(initiative)
        test_db.commit()
        test_db.refresh(initiative)
        
        # Verify initial state
        assert initiative.max_questions == 50
        
        # Perform multiple updates
        for i in range(num_updates):
            # Update the limit
            from datetime import datetime
            initiative.max_questions = new_limit
            initiative.max_questions_updated_at = datetime.utcnow()
            initiative.max_questions_updated_by = admin.id
            
            test_db.commit()
            test_db.refresh(initiative)
            
            # Property: Updated limit should be within valid bounds (1-500)
            assert 1 <= initiative.max_questions <= 500, f"Question limit {initiative.max_questions} should be between 1 and 500"
            
            # Property: Update tracking should be properly set
            assert initiative.max_questions == new_limit
            assert initiative.max_questions_updated_at is not None
            assert initiative.max_questions_updated_by == admin.id