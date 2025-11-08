"""
Analytics repository for LLM usage and cost reporting.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from uuid import UUID

from backend.models.llmcall import LLMCall, LLMCallStatus
from backend.models.user import User


class AnalyticsRepository:
    """Repository for analytics queries on LLM usage."""

    def __init__(self, db: Session):
        self.db = db

    def get_total_stats(
        self,
        organization_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Get overall usage statistics for an organization.

        Args:
            organization_id: Organization to query
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict with total_calls, total_cost, total_tokens, avg_latency
        """
        query = self.db.query(
            func.count(LLMCall.id).label('total_calls'),
            func.sum(LLMCall.cost_usd).label('total_cost'),
            func.sum(LLMCall.total_tokens).label('total_tokens'),
            func.avg(LLMCall.latency_ms).label('avg_latency')
        ).filter(
            LLMCall.organization_id == organization_id,
            LLMCall.status == LLMCallStatus.SUCCESS
        )

        if start_date:
            query = query.filter(LLMCall.created_at >= start_date)
        if end_date:
            query = query.filter(LLMCall.created_at <= end_date)

        result = query.first()

        return {
            "total_calls": result.total_calls or 0,
            "total_cost": float(result.total_cost or 0.0),
            "total_tokens": result.total_tokens or 0,
            "avg_latency_ms": float(result.avg_latency or 0.0) if result.avg_latency else None
        }

    def get_usage_by_user(
        self,
        organization_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get usage statistics broken down by user.

        Args:
            organization_id: Organization to query
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of users to return

        Returns:
            List of dicts with user stats
        """
        query = self.db.query(
            User.id,
            User.email,
            User.name,
            func.count(LLMCall.id).label('call_count'),
            func.sum(LLMCall.cost_usd).label('total_cost'),
            func.sum(LLMCall.total_tokens).label('total_tokens'),
            func.sum(LLMCall.input_tokens).label('input_tokens'),
            func.sum(LLMCall.output_tokens).label('output_tokens')
        ).join(
            LLMCall, LLMCall.user_id == User.id
        ).filter(
            LLMCall.organization_id == organization_id,
            LLMCall.status == LLMCallStatus.SUCCESS
        )

        if start_date:
            query = query.filter(LLMCall.created_at >= start_date)
        if end_date:
            query = query.filter(LLMCall.created_at <= end_date)

        results = query.group_by(
            User.id, User.email, User.name
        ).order_by(
            func.sum(LLMCall.cost_usd).desc()
        ).limit(limit).all()

        return [
            {
                "user_id": str(r.id),
                "email": r.email,
                "full_name": r.name,
                "call_count": r.call_count,
                "total_cost": float(r.total_cost or 0.0),
                "total_tokens": r.total_tokens or 0,
                "input_tokens": r.input_tokens or 0,
                "output_tokens": r.output_tokens or 0
            }
            for r in results
        ]

    def get_usage_by_agent(
        self,
        organization_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get usage statistics broken down by agent/action type.

        Args:
            organization_id: Organization to query
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of dicts with agent stats
        """
        query = self.db.query(
            LLMCall.agent_name,
            func.count(LLMCall.id).label('call_count'),
            func.sum(LLMCall.cost_usd).label('total_cost'),
            func.sum(LLMCall.total_tokens).label('total_tokens'),
            func.avg(LLMCall.latency_ms).label('avg_latency')
        ).filter(
            LLMCall.organization_id == organization_id,
            LLMCall.status == LLMCallStatus.SUCCESS
        )

        if start_date:
            query = query.filter(LLMCall.created_at >= start_date)
        if end_date:
            query = query.filter(LLMCall.created_at <= end_date)

        results = query.group_by(
            LLMCall.agent_name
        ).order_by(
            func.sum(LLMCall.cost_usd).desc()
        ).all()

        return [
            {
                "agent_name": r.agent_name,
                "call_count": r.call_count,
                "total_cost": float(r.total_cost or 0.0),
                "total_tokens": r.total_tokens or 0,
                "avg_latency_ms": float(r.avg_latency or 0.0) if r.avg_latency else None
            }
            for r in results
        ]

    def get_usage_over_time(
        self,
        organization_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = 'day'  # 'hour', 'day', 'week', 'month'
    ) -> List[Dict]:
        """
        Get usage statistics over time for trend analysis.

        Args:
            organization_id: Organization to query
            start_date: Optional start date filter
            end_date: Optional end date filter
            granularity: Time bucket size ('hour', 'day', 'week', 'month')

        Returns:
            List of dicts with time-series data
        """
        # SQLite-compatible date truncation using strftime
        if granularity == 'hour':
            date_trunc = func.strftime('%Y-%m-%d %H:00:00', LLMCall.created_at)
        elif granularity == 'day':
            date_trunc = func.strftime('%Y-%m-%d', LLMCall.created_at)
        elif granularity == 'week':
            # Week truncation: get start of week (Monday)
            date_trunc = func.date(LLMCall.created_at, 'weekday 0', '-6 days')
        elif granularity == 'month':
            date_trunc = func.strftime('%Y-%m-01', LLMCall.created_at)
        else:
            date_trunc = func.strftime('%Y-%m-%d', LLMCall.created_at)

        query = self.db.query(
            date_trunc.label('time_bucket'),
            func.count(LLMCall.id).label('call_count'),
            func.sum(LLMCall.cost_usd).label('total_cost'),
            func.sum(LLMCall.total_tokens).label('total_tokens')
        ).filter(
            LLMCall.organization_id == organization_id,
            LLMCall.status == LLMCallStatus.SUCCESS
        )

        if start_date:
            query = query.filter(LLMCall.created_at >= start_date)
        if end_date:
            query = query.filter(LLMCall.created_at <= end_date)

        results = query.group_by(
            'time_bucket'
        ).order_by(
            'time_bucket'
        ).all()

        return [
            {
                "timestamp": r.time_bucket if isinstance(r.time_bucket, str) else r.time_bucket.isoformat(),
                "call_count": r.call_count,
                "total_cost": float(r.total_cost or 0.0),
                "total_tokens": r.total_tokens or 0
            }
            for r in results
        ]

    def get_usage_by_model(
        self,
        organization_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get usage statistics broken down by model.

        Args:
            organization_id: Organization to query
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of dicts with model stats
        """
        query = self.db.query(
            LLMCall.model,
            func.count(LLMCall.id).label('call_count'),
            func.sum(LLMCall.cost_usd).label('total_cost'),
            func.sum(LLMCall.total_tokens).label('total_tokens')
        ).filter(
            LLMCall.organization_id == organization_id,
            LLMCall.status == LLMCallStatus.SUCCESS
        )

        if start_date:
            query = query.filter(LLMCall.created_at >= start_date)
        if end_date:
            query = query.filter(LLMCall.created_at <= end_date)

        results = query.group_by(
            LLMCall.model
        ).order_by(
            func.sum(LLMCall.cost_usd).desc()
        ).all()

        return [
            {
                "model": r.model,
                "call_count": r.call_count,
                "total_cost": float(r.total_cost or 0.0),
                "total_tokens": r.total_tokens or 0
            }
            for r in results
        ]

    def get_error_stats(
        self,
        organization_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Get error statistics for monitoring.

        Args:
            organization_id: Organization to query
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict with error counts and rate
        """
        query = self.db.query(
            func.count(LLMCall.id).label('total_calls'),
            func.sum(
                case(
                    (LLMCall.status != LLMCallStatus.SUCCESS, 1),
                    else_=0
                )
            ).label('error_count')
        ).filter(
            LLMCall.organization_id == organization_id
        )

        if start_date:
            query = query.filter(LLMCall.created_at >= start_date)
        if end_date:
            query = query.filter(LLMCall.created_at <= end_date)

        result = query.first()

        total_calls = result.total_calls or 0
        error_count = result.error_count or 0
        error_rate = (error_count / total_calls * 100) if total_calls > 0 else 0.0

        return {
            "total_calls": total_calls,
            "error_count": error_count,
            "success_count": total_calls - error_count,
            "error_rate_percent": round(error_rate, 2)
        }
