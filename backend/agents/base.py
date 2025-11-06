"""
Base agent class for all AI agents.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from backend.llm.client import get_anthropic_client, AnthropicClient
from backend.models import LLMCall
from backend.config import settings


class BaseAgent:
    """
    Base class for all AI agents using Claude.

    Provides common functionality:
    - LLM client access
    - Tracking and logging
    - Error handling
    """

    def __init__(
        self,
        db: Session,
        agent_name: str,
        model: Optional[str] = None
    ):
        """
        Initialize base agent.

        Args:
            db: Database session
            agent_name: Name of the agent (e.g., "Knowledge Gap Agent")
            model: Claude model to use (defaults to settings.anthropic_model)
        """
        self.db = db
        self.agent_name = agent_name
        self.model = model or settings.anthropic_model
        self.client: AnthropicClient = get_anthropic_client()

    def call_llm(
        self,
        system: str,
        messages: list[dict],
        organization_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        initiative_id: Optional[UUID] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0
    ) -> tuple[str, LLMCall, str]:
        """
        Make an LLM call with automatic tracking.

        Args:
            system: System prompt
            messages: Message history
            organization_id: Organization ID for attribution
            user_id: User ID for attribution
            initiative_id: Initiative ID for attribution
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            tuple: (response_text, llm_call_record, stop_reason)
        """
        return self.client.create_message(
            db=self.db,
            agent_name=self.agent_name,
            system=system,
            messages=messages,
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            organization_id=organization_id,
            user_id=user_id,
            initiative_id=initiative_id
        )
