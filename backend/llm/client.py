"""
Anthropic API client wrapper with error handling and tracking.
"""

import time
import hashlib
import logging
from typing import Optional, Dict, Any
from uuid import UUID
from anthropic import Anthropic, APIError, APITimeoutError, RateLimitError
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import LLMCall, LLMCallStatus

logger = logging.getLogger(__name__)


class AnthropicClient:
    """
    Wrapper for Anthropic API with automatic logging and cost tracking.

    All calls are logged to the llm_calls table for observability and billing.
    """

    # Pricing per million tokens (as of January 2025)
    PRICING = {
        "claude-sonnet-4-5": {
            "input": 3.00,   # $3 per 1M input tokens
            "output": 15.00  # $15 per 1M output tokens
        },
        "claude-sonnet-4-5-20250929": {
            "input": 3.00,   # $3 per 1M input tokens
            "output": 15.00  # $15 per 1M output tokens
        },
        "claude-haiku-4-5": {
            "input": 1.00,   # $1 per 1M input tokens
            "output": 5.00   # $5 per 1M output tokens
        },
        "claude-haiku-4-5-20251001": {
            "input": 1.00,   # $1 per 1M input tokens
            "output": 5.00   # $5 per 1M output tokens
        },
        "claude-3-7-sonnet-20250219": {
            "input": 3.00,   # $3 per 1M input tokens
            "output": 15.00  # $15 per 1M output tokens
        },
        "claude-3-5-haiku-20241022": {
            "input": 0.80,   # $0.80 per 1M input tokens
            "output": 4.00   # $4 per 1M output tokens
        }
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to settings.anthropic_api_key)
        """
        self.api_key = api_key or settings.anthropic_api_key

        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY in .env")

        self.client = Anthropic(
            api_key=self.api_key,
            timeout=settings.anthropic_api_timeout
        )

    def create_message(
        self,
        db: Session,
        agent_name: str,
        system: str,
        messages: list[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        organization_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        initiative_id: Optional[UUID] = None
    ) -> tuple[str, LLMCall, str]:
        """
        Create a message using Claude API with automatic tracking.

        Args:
            db: Database session for logging
            agent_name: Name of the agent making the call (e.g., "Knowledge Gap Agent")
            system: System prompt
            messages: List of message dicts with 'role' and 'content'
            model: Claude model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            organization_id: Organization ID for cost attribution
            user_id: User ID for attribution
            initiative_id: Initiative ID for attribution

        Returns:
            tuple: (response_text, llm_call_record, stop_reason)

        Raises:
            APIError: If API call fails
            APITimeoutError: If API call times out
            RateLimitError: If rate limit is exceeded
        """
        # Use configured model if not specified
        if model is None:
            model = settings.anthropic_model

        start_time = time.time()
        status = LLMCallStatus.SUCCESS
        error_message = None
        response_text = ""
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        stop_reason = "unknown"

        # Calculate prompt hash for versioning
        prompt_hash = self._hash_prompt(system, messages)

        try:
            logger.info(f"Starting Anthropic API call: agent={agent_name}, model={model}, timeout={settings.anthropic_api_timeout}s")

            # Make API call
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages
            )

            # Extract response
            response_text = response.content[0].text if response.content else ""

            # Extract token usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens

            # Check stop_reason for truncated responses
            stop_reason = response.stop_reason
            if stop_reason == "max_tokens":
                logger.warning(
                    f"Anthropic API response truncated due to max_tokens limit: "
                    f"agent={agent_name}, max_tokens={max_tokens}, output_tokens={output_tokens}. "
                    f"Response may be incomplete."
                )
                # Add a marker to error_message to indicate truncation
                error_message = f"Response truncated at max_tokens limit ({max_tokens})"
                status = LLMCallStatus.SUCCESS  # Still mark as success but log the truncation
            elif stop_reason != "end_turn":
                logger.warning(
                    f"Anthropic API response stopped with unexpected reason: "
                    f"agent={agent_name}, stop_reason={stop_reason}"
                )

            logger.info(f"Anthropic API call successful: agent={agent_name}, tokens={total_tokens}, stop_reason={stop_reason}, latency={time.time() - start_time:.1f}s")

        except RateLimitError as e:
            status = LLMCallStatus.RATE_LIMITED
            error_message = str(e)[:500]
            logger.error(f"Anthropic API rate limit: agent={agent_name}, error={error_message}")
            raise

        except APITimeoutError as e:
            status = LLMCallStatus.TIMEOUT
            error_message = str(e)[:500]
            elapsed = time.time() - start_time
            logger.error(f"Anthropic API timeout: agent={agent_name}, model={model}, elapsed={elapsed:.1f}s, configured_timeout={settings.anthropic_api_timeout}s")
            logger.error(f"Timeout details: {error_message}")
            raise

        except APIError as e:
            status = LLMCallStatus.ERROR
            error_message = str(e)[:500]
            logger.error(f"Anthropic API error: agent={agent_name}, error={error_message}")
            raise

        finally:
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Calculate cost
            cost_usd = self._calculate_cost(model, input_tokens, output_tokens)

            # Log the call
            llm_call = LLMCall(
                agent_name=agent_name,
                model=model,
                provider="anthropic",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                status=status,
                error_message=error_message,
                user_id=user_id,
                organization_id=organization_id,
                initiative_id=initiative_id,
                prompt_hash=prompt_hash
            )

            db.add(llm_call)
            db.commit()
            db.refresh(llm_call)

            # Record spending for budget tracking if user_id is provided
            if user_id and cost_usd > 0:
                try:
                    from backend.services.budget_service import BudgetService
                    from decimal import Decimal
                    
                    budget_service = BudgetService(db)
                    budget_service.record_spending(
                        user_id=user_id,
                        amount=Decimal(str(cost_usd)),
                        llm_call_id=llm_call.id
                    )
                    logger.debug(f"Recorded spending ${cost_usd:.4f} for user {user_id}")
                except Exception as e:
                    # Log error but don't fail the LLM call
                    logger.error(f"Failed to record spending for user {user_id}: {e}")

        return response_text, llm_call, stop_reason

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in USD for API call.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        if model not in self.PRICING:
            # Default to Sonnet 4.5 pricing if model not found
            model = "claude-sonnet-4-5"

        pricing = self.PRICING[model]

        # Cost = (input_tokens / 1M) * input_price + (output_tokens / 1M) * output_price
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return round(input_cost + output_cost, 6)

    def _hash_prompt(self, system: str, messages: list[Dict[str, str]]) -> str:
        """
        Generate SHA-256 hash of prompt for versioning.

        Args:
            system: System prompt
            messages: Message history

        Returns:
            SHA-256 hash (hex string)
        """
        # Concatenate system prompt and all messages
        content = system + "".join([f"{m['role']}:{m['content']}" for m in messages])

        # Generate hash
        return hashlib.sha256(content.encode()).hexdigest()


# Global client instance (lazy initialization)
_client: Optional[AnthropicClient] = None


def get_anthropic_client() -> AnthropicClient:
    """
    Get or create global Anthropic client instance.

    Returns:
        AnthropicClient instance
    """
    global _client

    if _client is None:
        _client = AnthropicClient()

    return _client
