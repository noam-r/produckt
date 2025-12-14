"""
Integration tests for admin budget monitoring functionality.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.models.user import User, UserRoleEnum
from backend.models.organization import Organization
from backend.models.user_monthly_spending import UserMonthlySpending
from backend.models.llmcall import LLMCall, LLMCallStatus
from backend.services.budget_service import BudgetService
from backend.repositories.user_repository import UserRepository


class TestBudgetMonitoringServices:
    """Integration tests for budget monitoring services and logic."""

    @pytest.fixture
    def users_with_spending(self, test_db: Session, test_organization: Organization):
        """Create test users with various spending patterns."""
        import bcrypt
        
        users = []
        spending_patterns = [
            {"budget": Decimal("100.00"), "spending": Decimal("50.00")},  # 50% utilization
            {"budget": Decimal("200.00"), "spending": Decimal("180.00")}, # 90% utilization (near limit)
            {"budget": Decimal("150.00"), "spending": Decimal("160.00")}, # Over budget
            {"budget": Decimal("300.00"), "spending": Decimal("30.00")},  # 10% utilization
        ]
        
        for i, pattern in enumerate(spending_patterns):
            password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            user = User(
                email=f"user{i}@example.com",
                password_hash=password_hash,
                name=f"Test User {i}",
                role=UserRoleEnum.PRODUCT_MANAGER,
                organization_id=test_organization.id,
                is_active=True,
                monthly_budget_usd=pattern["budget"]
            )
            test_db.add(user)
            test_db.flush()  # Get the ID without committing
            
            # Create monthly spending record
            now = datetime.utcnow()
            spending_record = UserMonthlySpending(
                user_id=user.id,
                year=now.year,
                month=now.month,
                total_spent_usd=pattern["spending"]
            )
            test_db.add(spending_record)
            
            users.append(user)
        
        test_db.commit()
        for user in users:
            test_db.refresh(user)
        
        return users

    def test_budget_overview_logic(self, test_db: Session, test_organization: Organization, users_with_spending):
        """
        Test budget overview logic returns accurate dashboard data.
        
        Requirements: 4.2 - Admin dashboard for budget overview
        """
        user_repo = UserRepository(test_db)
        budget_service = BudgetService(test_db)
        
        # Get all users in organization
        users = user_repo.get_all(test_organization.id)
        
        # Calculate budget statistics (simulating the endpoint logic)
        total_budget = sum(user.monthly_budget_usd for user in users)
        total_spending = Decimal('0.00')
        users_over_budget = 0
        users_near_limit = 0  # 80%+ utilization
        user_budget_data = []
        
        for user in users:
            budget_status = budget_service.get_budget_status_with_warnings(user.id)
            current_spending = budget_status["current_spending"]
            budget_limit = budget_status["budget_limit"]
            utilization = budget_status["utilization_percentage"]
            
            total_spending += current_spending
            
            if budget_status["is_over_budget"]:
                users_over_budget += 1
            elif utilization >= 80.0:
                users_near_limit += 1
            
            user_budget_data.append({
                "user_id": str(user.id),
                "email": user.email,
                "name": user.name,
                "monthly_budget_usd": float(budget_limit),
                "current_spending_usd": float(current_spending),
                "remaining_budget_usd": float(budget_status["remaining_budget"]),
                "utilization_percentage": utilization,
                "is_over_budget": budget_status["is_over_budget"],
                "is_near_limit": budget_status["is_near_limit"],
                "has_warning": budget_status["has_warning"],
                "warning_message": budget_status["warning_message"]
            })
        
        # Sort by utilization percentage descending
        user_budget_data.sort(key=lambda x: x["utilization_percentage"], reverse=True)
        
        # Test budget reporting accuracy
        assert len(users) == 4
        assert total_budget == Decimal("750.00")  # 100 + 200 + 150 + 300
        assert total_spending == Decimal("420.00")  # 50 + 180 + 160 + 30
        assert (total_budget - total_spending) == Decimal("330.00")  # 750 - 420
        
        expected_utilization = float(total_spending / total_budget * 100)
        assert abs(expected_utilization - 56.0) < 0.01  # 420/750 * 100
        
        # Test alert generation
        assert users_over_budget == 1  # User with 160/150 spending
        assert users_near_limit == 1   # User with 180/200 spending (90%)
        assert (len(users) - users_over_budget - users_near_limit) == 2  # Remaining users
        
        # Verify user data is sorted by utilization
        assert len(user_budget_data) == 4
        
        # First user should be over budget (highest utilization)
        assert user_budget_data[0]["is_over_budget"] is True
        assert user_budget_data[0]["utilization_percentage"] > 100
        
        # Second user should be near limit
        assert user_budget_data[1]["is_near_limit"] is True
        assert user_budget_data[1]["utilization_percentage"] >= 80

    def test_spending_trends_logic(self, test_db: Session, test_organization: Organization, users_with_spending):
        """
        Test spending trends logic returns historical data.
        
        Requirements: 4.3 - Spending analytics and trends
        """
        from sqlalchemy import func
        
        # Create historical spending data for multiple months
        users = users_with_spending
        base_date = datetime.utcnow()
        
        # Add spending for previous months
        for month_offset in range(1, 4):  # 3 months back
            month_date = base_date - timedelta(days=30 * month_offset)
            
            for i, user in enumerate(users):
                spending_amount = Decimal("25.00") * (i + 1) * month_offset  # Varying amounts
                
                spending_record = UserMonthlySpending(
                    user_id=user.id,
                    year=month_date.year,
                    month=month_date.month,
                    total_spent_usd=spending_amount
                )
                test_db.add(spending_record)
        
        test_db.commit()
        
        # Simulate the spending trends endpoint logic
        months = 4
        end_date = datetime.utcnow()
        start_date = end_date.replace(day=1)  # First day of current month
        
        # Go back the specified number of months
        for _ in range(months - 1):
            if start_date.month == 1:
                start_date = start_date.replace(year=start_date.year - 1, month=12)
            else:
                start_date = start_date.replace(month=start_date.month - 1)
        
        # Query monthly spending data
        spending_data = (
            test_db.query(
                UserMonthlySpending.year,
                UserMonthlySpending.month,
                func.sum(UserMonthlySpending.total_spent_usd).label('total_spending'),
                func.count(UserMonthlySpending.user_id).label('active_users')
            )
            .join(User, User.id == UserMonthlySpending.user_id)
            .filter(
                User.organization_id == test_organization.id,
                UserMonthlySpending.year >= start_date.year,
                UserMonthlySpending.month >= start_date.month if UserMonthlySpending.year == start_date.year else True
            )
            .group_by(UserMonthlySpending.year, UserMonthlySpending.month)
            .order_by(UserMonthlySpending.year, UserMonthlySpending.month)
            .all()
        )
        
        # Get total budget for each month (sum of all user budgets)
        total_monthly_budget = sum(user.monthly_budget_usd for user in users)
        
        # Format the data
        trends = []
        for row in spending_data:
            month_str = f"{row.year}-{row.month:02d}"
            utilization = float(row.total_spending / total_monthly_budget * 100) if total_monthly_budget > 0 else 0.0
            
            trends.append({
                "year": row.year,
                "month": row.month,
                "month_label": month_str,
                "total_spending_usd": float(row.total_spending),
                "active_users": row.active_users,
                "total_budget_usd": float(total_monthly_budget),
                "utilization_percentage": utilization
            })
        
        # Verify trend data
        assert len(trends) >= 1  # At least current month
        
        # Verify trend data structure
        for trend in trends:
            assert "year" in trend
            assert "month" in trend
            assert "total_spending_usd" in trend
            assert "active_users" in trend
            assert "total_budget_usd" in trend
            assert "utilization_percentage" in trend
            
            # Verify calculations
            assert trend["total_budget_usd"] == 750.0  # Sum of all user budgets
            if trend["total_spending_usd"] > 0:
                expected_utilization = trend["total_spending_usd"] / trend["total_budget_usd"] * 100
                assert abs(trend["utilization_percentage"] - expected_utilization) < 0.01

    def test_budget_alerts_logic(self, test_db: Session, test_organization: Organization, users_with_spending):
        """
        Test budget alerts logic identifies users needing attention.
        
        Requirements: 4.4 - Budget utilization alerts
        """
        user_repo = UserRepository(test_db)
        budget_service = BudgetService(test_db)
        
        users = user_repo.get_all(test_organization.id)
        alerts = []
        
        for user in users:
            budget_status = budget_service.get_budget_status_with_warnings(user.id)
            
            # Only include users with warnings or over budget
            if budget_status["has_warning"] or budget_status["is_over_budget"]:
                alert_level = "critical" if budget_status["is_over_budget"] else "warning"
                
                alerts.append({
                    "user_id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "alert_level": alert_level,
                    "monthly_budget_usd": float(budget_status["budget_limit"]),
                    "current_spending_usd": float(budget_status["current_spending"]),
                    "utilization_percentage": budget_status["utilization_percentage"],
                    "is_over_budget": budget_status["is_over_budget"],
                    "warning_message": budget_status["warning_message"],
                    "last_updated": datetime.utcnow().isoformat()
                })
        
        # Sort by utilization percentage descending (most critical first)
        alerts.sort(key=lambda x: x["utilization_percentage"], reverse=True)
        
        # Test alert generation accuracy
        critical_alerts = len([a for a in alerts if a["alert_level"] == "critical"])
        warning_alerts = len([a for a in alerts if a["alert_level"] == "warning"])
        total_alerts = len([a for a in alerts if a["alert_level"] in ["warning", "critical"]])
        
        assert critical_alerts == 1  # One user over budget
        assert warning_alerts == 1   # One user near limit (80%+)
        assert total_alerts == 2     # Total alerts
        
        # Verify alerts are sorted by utilization (most critical first)
        for i in range(len(alerts) - 1):
            assert alerts[i]["utilization_percentage"] >= alerts[i + 1]["utilization_percentage"]
        
        # Verify alert levels
        critical_alert_list = [a for a in alerts if a["alert_level"] == "critical"]
        warning_alert_list = [a for a in alerts if a["alert_level"] == "warning"]
        
        assert len(critical_alert_list) == 1
        assert len(warning_alert_list) == 1
        
        # Critical alert should be over budget
        critical_alert = critical_alert_list[0]
        assert critical_alert["is_over_budget"] is True
        assert critical_alert["utilization_percentage"] > 100
        
        # Warning alert should be near limit but not over
        warning_alert = warning_alert_list[0]
        assert warning_alert["is_over_budget"] is False
        assert warning_alert["utilization_percentage"] >= 80

    def test_budget_alerts_with_resolved_logic(self, test_db: Session, test_organization: Organization, users_with_spending):
        """
        Test budget alerts logic with resolved alerts included.
        """
        user_repo = UserRepository(test_db)
        budget_service = BudgetService(test_db)
        
        users = user_repo.get_all(test_organization.id)
        alerts = []
        include_resolved = True
        
        for user in users:
            budget_status = budget_service.get_budget_status_with_warnings(user.id)
            
            # Include users with warnings or over budget
            if budget_status["has_warning"] or budget_status["is_over_budget"]:
                alert_level = "critical" if budget_status["is_over_budget"] else "warning"
                
                alerts.append({
                    "user_id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "alert_level": alert_level,
                    "monthly_budget_usd": float(budget_status["budget_limit"]),
                    "current_spending_usd": float(budget_status["current_spending"]),
                    "utilization_percentage": budget_status["utilization_percentage"],
                    "is_over_budget": budget_status["is_over_budget"],
                    "warning_message": budget_status["warning_message"]
                })
            elif include_resolved:
                # Include users within budget if requested
                alerts.append({
                    "user_id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "alert_level": "resolved",
                    "monthly_budget_usd": float(budget_status["budget_limit"]),
                    "current_spending_usd": float(budget_status["current_spending"]),
                    "utilization_percentage": budget_status["utilization_percentage"],
                    "is_over_budget": False,
                    "warning_message": None
                })
        
        # Should include all users when include_resolved=true
        assert len(alerts) == 4
        
        # Verify resolved alerts are included
        resolved_alerts = [a for a in alerts if a["alert_level"] == "resolved"]
        assert len(resolved_alerts) == 2  # Users within budget

    def test_budget_service_error_handling(self, test_db: Session, test_organization: Organization, monkeypatch):
        """
        Test budget monitoring logic handles service errors gracefully.
        
        Requirements: 4.1 - Error handling in monitoring
        """
        # Create a user
        import bcrypt
        password_hash = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user = User(
            email="error_user@example.com",
            password_hash=password_hash,
            name="Error User",
            role=UserRoleEnum.PRODUCT_MANAGER,
            organization_id=test_organization.id,
            is_active=True,
            monthly_budget_usd=Decimal("100.00")
        )
        test_db.add(user)
        test_db.commit()
        
        # Mock budget service to raise an exception
        def mock_get_budget_status_with_warnings(user_id):
            raise Exception("Service error")
        
        monkeypatch.setattr(BudgetService, "get_budget_status_with_warnings", mock_get_budget_status_with_warnings)
        
        user_repo = UserRepository(test_db)
        users = user_repo.get_all(test_organization.id)
        
        # Budget overview logic should handle errors gracefully
        successful_users = []
        for user in users:
            try:
                budget_service = BudgetService(test_db)
                budget_status = budget_service.get_budget_status_with_warnings(user.id)
                successful_users.append(user)
            except Exception:
                # Skip users with errors
                continue
        
        # Should skip users with errors but still process others
        assert len(successful_users) == 0  # All users will fail due to mock

    def test_budget_overview_empty_organization(self, test_db: Session, test_organization: Organization):
        """
        Test budget overview handles organization with no additional users gracefully.
        
        Requirements: 4.2 - Handle edge cases
        """
        user_repo = UserRepository(test_db)
        budget_service = BudgetService(test_db)
        
        # Get all users in organization (should be empty or minimal)
        users = user_repo.get_all(test_organization.id)
        
        # Calculate budget statistics
        total_budget = sum(user.monthly_budget_usd for user in users)
        total_spending = Decimal('0.00')
        users_over_budget = 0
        users_near_limit = 0
        
        for user in users:
            try:
                budget_status = budget_service.get_budget_status_with_warnings(user.id)
                current_spending = budget_status["current_spending"]
                utilization = budget_status["utilization_percentage"]
                
                total_spending += current_spending
                
                if budget_status["is_over_budget"]:
                    users_over_budget += 1
                elif utilization >= 80.0:
                    users_near_limit += 1
            except Exception:
                # Skip users with errors
                continue
        
        # Should handle empty or minimal organization gracefully
        assert users_over_budget == 0
        assert users_near_limit == 0
        assert total_spending >= Decimal('0.00')