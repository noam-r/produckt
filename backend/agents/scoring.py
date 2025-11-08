"""
Scoring Agent - Calculates RICE and FDV scores for initiative prioritization.
"""

import json
from typing import Tuple, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent
from backend.agents.prompts import (
    SCORING_AGENT_SYSTEM,
    SCORING_AGENT_USER_TEMPLATE,
    build_qa_section_for_mrd
)
from backend.models import Initiative, Context, MRD
from backend.repositories.question import QuestionRepository
from backend.repositories.answer import AnswerRepository
from backend.repositories.mrd import MRDRepository


class ScoringAgent(BaseAgent):
    """
    Agent that calculates RICE and FDV scores for initiatives.

    Uses Claude to analyze initiative details, Q&A, and MRD content
    to generate objective prioritization scores.
    """

    def __init__(self, db: Session, model: Optional[str] = None):
        """
        Initialize Scoring Agent.

        Args:
            db: Database session
            model: Claude model to use (defaults to settings.anthropic_model)
        """
        super().__init__(
            db=db,
            agent_name="Scoring Agent",
            model=model
        )

    def calculate_scores(
        self,
        initiative: Initiative,
        context: Context,
        user_id: UUID
    ) -> Tuple[Dict, Dict, Dict, list]:
        """
        Calculate RICE and FDV scores for an initiative.

        Args:
            initiative: Initiative to score
            context: Current organizational context
            user_id: User requesting score calculation

        Returns:
            Tuple of (rice_data, fdv_data, data_quality, warnings) containing:
            - rice_data: {reach, impact, confidence, effort, rice_score, reasoning}
            - fdv_data: {feasibility, desirability, viability, fdv_score, reasoning}
            - data_quality: {reach_quality, reach_source, impact_quality, ...}
            - warnings: List of warning strings about data limitations

        Raises:
            ValueError: If no MRD exists or JSON parsing fails
        """
        # Get MRD
        mrd_repo = MRDRepository(self.db)
        mrd = mrd_repo.get_by_initiative(initiative.id)

        if not mrd:
            raise ValueError(
                "No MRD found for this initiative. "
                "Please generate an MRD before calculating scores."
            )

        # Get questions and answers
        question_repo = QuestionRepository(self.db)
        answer_repo = AnswerRepository(self.db)

        questions = question_repo.get_by_initiative(initiative.id)
        questions_with_answers = [
            (q, answer_repo.get_by_question(q.id))
            for q in questions
        ]

        # Count estimated answers for confidence penalty
        estimated_count = sum(
            1 for q, a in questions_with_answers
            if a and a.answer_status.value == "Estimated"
        )

        # Build Q&A section
        qa_section = build_qa_section_for_mrd(questions_with_answers)

        # Build prompt
        user_message = SCORING_AGENT_USER_TEMPLATE.format(
            title=initiative.title,
            description=initiative.description or "No description provided",
            status=initiative.status.value,
            company_mission=context.company_mission or "Not specified",
            strategic_objectives=context.strategic_objectives or "Not specified",
            target_markets=context.target_markets or "Not specified",
            qa_section=qa_section,
            mrd_content=mrd.content[:8000]  # Limit MRD content to avoid token limits
        )

        # Call LLM
        response_text, llm_call, stop_reason = self.call_llm(
            system=SCORING_AGENT_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
            organization_id=initiative.organization_id,
            user_id=user_id,
            initiative_id=initiative.id,
            max_tokens=4096,
            temperature=0.5  # Lower temperature for more consistent scoring
        )
        if stop_reason == "max_tokens":
            print(f"Warning: Scoring stopped due to max_tokens for initiative {initiative.id}")

        # Parse JSON response - handle markdown code fences and whitespace
        json_text = response_text.strip()

        # Remove markdown code fences if present
        if json_text.startswith("```"):
            # Remove opening fence
            lines = json_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove closing fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            json_text = "\n".join(lines).strip()

        # Check if empty
        if not json_text:
            raise ValueError(f"LLM returned empty response. Response was: {repr(response_text[:200])}")

        try:
            scores_data = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse scoring response as JSON: {e}. Response snippet: {json_text[:500]}")

        # Validate structure
        if "rice" not in scores_data or "fdv" not in scores_data:
            raise ValueError("Scoring response missing 'rice' or 'fdv' keys")

        rice_data = scores_data["rice"]
        fdv_data = scores_data["fdv"]

        # Validate RICE fields
        rice_required = ["reach", "impact", "confidence", "effort", "rice_score", "reasoning"]
        missing_rice = [f for f in rice_required if f not in rice_data]
        if missing_rice:
            raise ValueError(f"RICE data missing fields: {missing_rice}")

        # Validate FDV fields
        fdv_required = ["feasibility", "desirability", "viability", "fdv_score", "reasoning"]
        missing_fdv = [f for f in fdv_required if f not in fdv_data]
        if missing_fdv:
            raise ValueError(f"FDV data missing fields: {missing_fdv}")

        # Extract data quality and warnings (optional fields)
        data_quality = scores_data.get("data_quality", {})
        warnings = scores_data.get("warnings", [])

        # Apply confidence penalty for estimated answers
        if estimated_count > 0:
            # Calculate penalty: min(30%, estimated_count * 10%)
            confidence_penalty_percent = min(30, estimated_count * 10)

            # Apply penalty to RICE confidence if it exists
            if rice_data.get("confidence") is not None:
                original_confidence = rice_data["confidence"]
                adjusted_confidence = max(0, original_confidence - confidence_penalty_percent)
                rice_data["confidence"] = adjusted_confidence

                # Recalculate RICE score with adjusted confidence
                if (rice_data.get("reach") is not None and
                    rice_data.get("impact") is not None and
                    rice_data.get("effort") is not None and
                    rice_data["effort"] > 0):
                    rice_data["rice_score"] = (
                        rice_data["reach"] *
                        rice_data["impact"] *
                        (adjusted_confidence / 100)
                    ) / rice_data["effort"]

                # Add warning about estimation penalty
                penalty_warning = (
                    f"RICE Confidence reduced by {confidence_penalty_percent}% "
                    f"(from {original_confidence}% to {adjusted_confidence}%) "
                    f"due to {estimated_count} estimated answer(s). "
                    f"Provide precise data to improve confidence."
                )
                warnings.append(penalty_warning)

            # Add estimation metadata to data quality
            data_quality["estimated_answers_count"] = estimated_count
            data_quality["confidence_penalty_applied"] = f"-{confidence_penalty_percent}%"

        return rice_data, fdv_data, data_quality, warnings

    def validate_rice_score(self, rice_data: Dict) -> bool:
        """
        Validate RICE score calculation.

        Args:
            rice_data: RICE data dictionary

        Returns:
            True if calculation is correct within tolerance
        """
        print(f"[VALIDATION] Inside validate_rice_score method")
        reach = rice_data.get("reach")
        impact = rice_data.get("impact")
        confidence = rice_data.get("confidence")
        effort = rice_data.get("effort")
        rice_score = rice_data.get("rice_score")

        print(f"[VALIDATION] RICE values - reach: {reach}, impact: {impact}, confidence: {confidence}, effort: {effort}, score: {rice_score}")

        # Check for None values
        if reach is None or impact is None or confidence is None or effort is None or rice_score is None:
            print(f"[VALIDATION ERROR] One or more RICE values is None - skipping validation")
            return False

        # Check for zero effort (division by zero)
        if effort == 0:
            print(f"[VALIDATION ERROR] Effort is zero - cannot calculate RICE score")
            return False

        # Calculate expected score
        expected = (reach * impact * (confidence / 100)) / effort
        print(f"[VALIDATION] Expected RICE: {expected}, Actual: {rice_score}")

        # Allow 1% tolerance for rounding
        tolerance = expected * 0.01
        result = abs(rice_score - expected) <= tolerance
        print(f"[VALIDATION] RICE validation result: {result}")
        return result

    def validate_fdv_score(self, fdv_data: Dict) -> bool:
        """
        Validate FDV score calculation.

        Args:
            fdv_data: FDV data dictionary

        Returns:
            True if calculation is correct within tolerance
        """
        feasibility = fdv_data.get("feasibility")
        desirability = fdv_data.get("desirability")
        viability = fdv_data.get("viability")
        fdv_score = fdv_data.get("fdv_score")

        print(f"[VALIDATION] FDV values - feasibility: {feasibility}, desirability: {desirability}, viability: {viability}, score: {fdv_score}")

        # Check for None values
        if feasibility is None or desirability is None or viability is None or fdv_score is None:
            print(f"[VALIDATION ERROR] One or more FDV values is None - skipping validation")
            return False

        # Calculate expected score
        expected = (feasibility + desirability + viability) / 3.0

        # Allow small tolerance for rounding
        tolerance = 0.1
        result = abs(fdv_score - expected) <= tolerance
        print(f"[VALIDATION] FDV validation - Expected: {expected}, Actual: {fdv_score}, Result: {result}")
        return result
