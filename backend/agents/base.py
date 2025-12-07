"""
Base agent class for all AI agents.
"""

import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from anthropic import APIError, APITimeoutError, RateLimitError, NotFoundError

from backend.llm.client import get_anthropic_client, AnthropicClient
from backend.models import LLMCall
from backend.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors with user-friendly messages."""

    def __init__(self, message: str, technical_details: str = None):
        self.message = message
        self.technical_details = technical_details
        super().__init__(message)


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
        logger.debug(f"Initialized {agent_name} with model {self.model}")

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
        logger.info(
            f"LLM call started: agent={self.agent_name}, model={self.model}, "
            f"max_tokens={max_tokens}, temperature={temperature}"
        )

        try:
            result = self.client.create_message(
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

            logger.info(
                f"LLM call completed: agent={self.agent_name}, "
                f"response_length={len(result[0])}, stop_reason={result[2]}"
            )

            return result
        except NotFoundError as e:
            error_msg = (
                f"AI model '{self.model}' not found. Please update your ANTHROPIC_MODEL "
                f"environment variable to a valid model (e.g., 'claude-sonnet-4-5'). "
                f"Check the .env.example file for available options."
            )
            logger.error(
                f"LLM model not found: agent={self.agent_name}, model={self.model}, error={str(e)}"
            )
            raise LLMError(error_msg, str(e))
        except RateLimitError as e:
            error_msg = (
                "AI service rate limit exceeded. Please try again in a few moments. "
                "If this persists, contact support."
            )
            logger.error(
                f"LLM rate limit exceeded: agent={self.agent_name}, error={str(e)}"
            )
            raise LLMError(error_msg, str(e))
        except APITimeoutError as e:
            error_msg = (
                f"AI service request timed out after {settings.anthropic_api_timeout} seconds. "
                f"This usually happens with complex requests. Please try again."
            )
            logger.error(
                f"LLM timeout: agent={self.agent_name}, timeout={settings.anthropic_api_timeout}s, error={str(e)}"
            )
            raise LLMError(error_msg, str(e))
        except APIError as e:
            error_msg = (
                "AI service error occurred. This might be a temporary issue. "
                "Please try again, and contact support if the problem persists."
            )
            logger.error(
                f"LLM API error: agent={self.agent_name}, error={str(e)}",
                exc_info=True
            )
            raise LLMError(error_msg, str(e))
        except Exception as e:
            error_msg = (
                f"Unexpected error during AI processing: {str(e)}"
            )
            logger.error(
                f"LLM unexpected error: agent={self.agent_name}, error={str(e)}",
                exc_info=True
            )
            raise LLMError(error_msg, str(e))
