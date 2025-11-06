"""
Session management for authentication (in-memory POC).

For production, this should be replaced with Redis or a database-backed session store.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from dataclasses import dataclass
import uuid

from backend.config import settings


@dataclass
class Session:
    """Session data structure."""

    session_id: str
    user_id: uuid.UUID
    email: str
    name: str
    role: str
    organization_id: uuid.UUID
    organization_name: str
    created_at: datetime
    expires_at: datetime


class SessionManager:
    """
    In-memory session manager for POC.

    WARNING: This is not suitable for production as:
    1. Sessions are lost on server restart
    2. Does not scale across multiple server instances
    3. Memory usage grows with active sessions

    For production, use Redis or a database-backed session store.
    """

    def __init__(self, session_duration_minutes: int = 43200):  # 30 days default
        self._sessions: Dict[str, Session] = {}
        self._session_duration = timedelta(minutes=session_duration_minutes)

    def create_session(
        self,
        user_id: uuid.UUID,
        email: str,
        name: str,
        role: str,
        organization_id: uuid.UUID,
        organization_name: str
    ) -> Session:
        """Create a new session for a user."""
        session_id = f"sess_{secrets.token_urlsafe(32)}"
        now = datetime.utcnow()
        expires_at = now + self._session_duration

        session = Session(
            session_id=session_id,
            user_id=user_id,
            email=email,
            name=name,
            role=role,
            organization_id=organization_id,
            organization_name=organization_name,
            created_at=now,
            expires_at=expires_at
        )

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID if it exists and is not expired.

        Returns None if session doesn't exist or is expired.
        """
        session = self._sessions.get(session_id)

        if session is None:
            return None

        # Check if session is expired
        if datetime.utcnow() > session.expires_at:
            # Clean up expired session
            self.delete_session(session_id)
            return None

        return session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Returns True if session was deleted, False if it didn't exist.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def delete_user_sessions(self, user_id: uuid.UUID) -> int:
        """
        Delete all sessions for a user.

        Returns the number of sessions deleted.
        """
        sessions_to_delete = [
            sid for sid, session in self._sessions.items()
            if session.user_id == user_id
        ]

        for session_id in sessions_to_delete:
            del self._sessions[session_id]

        return len(sessions_to_delete)

    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions.

        Returns the number of sessions cleaned up.
        """
        now = datetime.utcnow()
        expired_sessions = [
            sid for sid, session in self._sessions.items()
            if now > session.expires_at
        ]

        for session_id in expired_sessions:
            del self._sessions[session_id]

        return len(expired_sessions)

    def extend_session(self, session_id: str) -> bool:
        """
        Extend a session's expiration time.

        Returns True if session was extended, False if it doesn't exist or is expired.
        """
        session = self.get_session(session_id)
        if session is None:
            return False

        session.expires_at = datetime.utcnow() + self._session_duration
        return True

    def get_active_session_count(self) -> int:
        """Get the count of active (non-expired) sessions."""
        now = datetime.utcnow()
        return sum(1 for session in self._sessions.values() if now <= session.expires_at)


# Global session manager instance
session_manager = SessionManager(session_duration_minutes=settings.session_timeout_minutes)
