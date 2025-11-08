"""
Scoring Gap Analyzer - Identifies missing data preventing score calculation.

This agent analyzes failed scoring attempts and generates targeted questions
to bridge data gaps, enabling users to provide estimates that unlock scoring.
"""

import json
from typing import Dict, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent
from backend.agents.scoring import ScoringAgent
from backend.models import Initiative, Context
from backend.repositories.question import QuestionRepository
from backend.repositories.answer import AnswerRepository
from backend.repositories.mrd import MRDRepository


class ScoringGapAnalyzer(BaseAgent):
    """
    Agent that analyzes scoring failures and generates targeted gap-filling questions.
    """

    def __init__(self, db: Session, model: str = None):
        """
        Initialize Scoring Gap Analyzer.

        Args:
            db: Database session
            model: Claude model to use (defaults to settings.anthropic_model)
        """
        super().__init__(
            db=db,
            agent_name="Scoring Gap Analyzer",
            model=model
        )

    def analyze_gaps(
        self,
        initiative: Initiative,
        context: Context,
        user_id: UUID
    ) -> Dict:
        """
        Analyze scoring gaps and generate targeted questions.

        Args:
            initiative: Initiative to analyze
            context: Organizational context
            user_id: User requesting analysis

        Returns:
            Dict containing:
            - can_calculate: bool
            - blocking_gaps: List of gap objects with questions
            - partial_scores: Dict of successfully calculated components
            - warnings: List of data quality warnings
        """
        # First, attempt to calculate scores normally
        scoring_agent = ScoringAgent(self.db, self.model)

        try:
            rice_data, fdv_data, data_quality, warnings = scoring_agent.calculate_scores(
                initiative=initiative,
                context=context,
                user_id=user_id
            )

            # Check RICE confidence level - if below threshold, suggest questions to improve it
            rice_confidence = rice_data.get("confidence", 0)
            confidence_threshold = 80  # Suggest improvements if confidence < 80%

            needs_improvement = rice_confidence < confidence_threshold

            if not needs_improvement:
                # Confidence is already high - no need for improvement
                return {
                    "can_calculate": True,
                    "blocking_gaps": [],
                    "partial_scores": {
                        "rice": rice_data,
                        "fdv": fdv_data
                    },
                    "warnings": warnings,
                    "data_quality": data_quality,
                    "current_confidence": rice_confidence,
                    "message": f"RICE confidence is {rice_confidence}% - no improvement needed"
                }

            # Generate improvement questions - these help increase confidence
            improvement_questions = self._identify_gaps(
                rice_data=rice_data,
                fdv_data=fdv_data,
                data_quality=data_quality,
                warnings=warnings,
                initiative=initiative,
                context=context,
                user_id=user_id
            )

            return {
                "can_calculate": True,  # Scores exist but confidence can be improved
                "blocking_gaps": improvement_questions,  # Questions to improve confidence
                "partial_scores": {
                    "rice": rice_data,
                    "fdv": fdv_data
                },
                "warnings": warnings,
                "data_quality": data_quality,
                "current_confidence": rice_confidence,
                "message": f"RICE confidence is {rice_confidence}% - answering questions can improve it"
            }

        except ValueError as e:
            # Scoring completely failed - MRD missing or other critical error
            return {
                "can_calculate": False,
                "error": str(e),
                "blocking_gaps": [],
                "partial_scores": {},
                "warnings": [str(e)]
            }

    def _identify_gaps(
        self,
        rice_data: Dict,
        fdv_data: Dict,
        data_quality: Dict,
        warnings: List,
        initiative: Initiative,
        context: Context,
        user_id: UUID
    ) -> List[Dict]:
        """
        Identify specific gaps and generate targeted questions using LLM.

        Args:
            rice_data: RICE calculation results (may have None values)
            fdv_data: FDV calculation results (may have None values)
            data_quality: Data quality metadata
            warnings: List of warnings from scoring
            initiative: Initiative being analyzed
            context: Organizational context
            user_id: User ID for LLM call tracking

        Returns:
            List of gap objects with generated questions
        """
        # Get Q&A and MRD context
        question_repo = QuestionRepository(self.db)
        answer_repo = AnswerRepository(self.db)
        mrd_repo = MRDRepository(self.db)

        questions = question_repo.get_by_initiative(initiative.id)
        mrd = mrd_repo.get_by_initiative(initiative.id)

        # Build Q&A summary
        qa_summary = []
        for q in questions[:10]:  # Limit to first 10 for context
            answer = answer_repo.get_by_question(q.id)
            if answer and answer.answer_status == "Answered":
                qa_summary.append(f"Q: {q.question_text}\nA: {answer.answer_text}")

        qa_context = "\n\n".join(qa_summary) if qa_summary else "No Q&A available"
        mrd_excerpt = mrd.content[:2000] if mrd else "No MRD available"

        # Build gap analysis prompt
        gaps_description = self._format_gaps_for_llm(rice_data, fdv_data, data_quality, warnings)

        prompt = f"""You are analyzing an initiative that cannot be fully scored due to missing data.

INITIATIVE: {initiative.title}
{initiative.description}

ORGANIZATION CONTEXT:
- Mission: {context.company_mission or 'Not specified'}
- Target Markets: {context.target_markets or 'Not specified'}

EXISTING Q&A (Sample):
{qa_context}

MRD EXCERPT:
{mrd_excerpt}

SCORING GAPS DETECTED:
{gaps_description}

YOUR TASK:
Generate 3-5 highly specific, actionable questions that would enable score calculation. For each question:

1. Target ONLY the missing quantitative data
2. Make it EASY to estimate (provide context/benchmarks)
3. Accept ranges or approximations
4. Explain WHY this data matters for scoring

Return JSON in this EXACT format:
{{
  "gaps": [
    {{
      "framework": "RICE" or "FDV",
      "component": "reach" | "impact" | "confidence" | "effort" | "feasibility" | "desirability" | "viability",
      "issue_summary": "Brief description of what's missing",
      "questions": [
        {{
          "text": "The specific question to ask the user",
          "hint": "Helpful context to guide estimation (benchmarks, ranges, etc)",
          "priority": "P0" or "P1",
          "example_answer": "Example of acceptable answer format"
        }}
      ]
    }}
  ]
}}

Focus on practical, estimable questions. Avoid asking for data that requires extensive research."""

        # Call LLM
        response_text, llm_call, stop_reason = self.call_llm(
            system="You are a product management expert helping teams estimate scoring metrics when exact data isn't available. Generate practical, estimable questions.",
            messages=[{"role": "user", "content": prompt}],
            organization_id=initiative.organization_id,
            user_id=user_id,
            initiative_id=initiative.id,
            max_tokens=4096,
            temperature=0.7
        )

        # Parse response
        json_text = response_text.strip()
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            json_text = "\n".join(lines).strip()

        try:
            result = json.loads(json_text)
            gaps = result.get("gaps", [])

            # Create Question records for gap-filling questions
            for gap in gaps:
                for q_data in gap.get("questions", []):
                    # Create a new question
                    from backend.models import Question, QuestionPriority, QuestionCategory

                    # Map framework components to categories
                    category_map = {
                        "reach": QuestionCategory.PRODUCT,
                        "impact": QuestionCategory.PRODUCT,
                        "confidence": QuestionCategory.BUSINESS_DEV,
                        "effort": QuestionCategory.TECHNICAL,
                        "feasibility": QuestionCategory.TECHNICAL,
                        "desirability": QuestionCategory.PRODUCT,
                        "viability": QuestionCategory.FINANCIAL,
                    }

                    category = category_map.get(gap["component"].lower(), QuestionCategory.BUSINESS_DEV)
                    priority = QuestionPriority.P0 if q_data["priority"] == "P0" else QuestionPriority.P1

                    new_question = Question(
                        initiative_id=initiative.id,
                        iteration=initiative.iteration_count,
                        category=category,
                        priority=priority,
                        blocks_mrd_generation=False,  # Gap questions don't block MRD
                        question_text=q_data["text"],
                        rationale=f"[Gap Analysis] {q_data.get('hint', 'Missing data for scoring')}"
                    )
                    question_repo.create(new_question)

                    # Add question_id to the response
                    q_data["question_id"] = str(new_question.id)

            return gaps
        except json.JSONDecodeError as e:
            print(f"Failed to parse gap analysis response: {e}")
            print(f"Response: {json_text[:500]}")
            # Return empty gaps on parse failure
            return []

    def _format_gaps_for_llm(
        self,
        rice_data: Dict,
        fdv_data: Dict,
        data_quality: Dict,
        warnings: List
    ) -> str:
        """
        Format gap information for LLM prompt.

        Args:
            rice_data: RICE results (may have None values)
            fdv_data: FDV results (may have None values)
            data_quality: Quality metadata
            warnings: Warning messages

        Returns:
            Formatted string describing gaps
        """
        gaps_text = []

        # RICE gaps
        if rice_data.get("reach") is None:
            reach_reason = rice_data.get("reasoning", {}).get("reach", "Unknown reason")
            gaps_text.append(f"**RICE Reach**: {reach_reason}")

        if rice_data.get("impact") is None:
            impact_reason = rice_data.get("reasoning", {}).get("impact", "Unknown reason")
            gaps_text.append(f"**RICE Impact**: {impact_reason}")

        if rice_data.get("confidence") is None:
            confidence_reason = rice_data.get("reasoning", {}).get("confidence", "Unknown reason")
            gaps_text.append(f"**RICE Confidence**: {confidence_reason}")

        if rice_data.get("effort") is None:
            effort_reason = rice_data.get("reasoning", {}).get("effort", "Unknown reason")
            gaps_text.append(f"**RICE Effort**: {effort_reason}")

        # FDV gaps
        if fdv_data.get("feasibility") is None:
            feasibility_reason = fdv_data.get("reasoning", {}).get("feasibility", "Unknown reason")
            gaps_text.append(f"**FDV Feasibility**: {feasibility_reason}")

        if fdv_data.get("desirability") is None:
            desirability_reason = fdv_data.get("reasoning", {}).get("desirability", "Unknown reason")
            gaps_text.append(f"**FDV Desirability**: {desirability_reason}")

        if fdv_data.get("viability") is None:
            viability_reason = fdv_data.get("reasoning", {}).get("viability", "Unknown reason")
            gaps_text.append(f"**FDV Viability**: {viability_reason}")

        # Add warnings
        if warnings:
            gaps_text.append(f"\n**Additional Warnings**:")
            for warning in warnings:
                gaps_text.append(f"- {warning}")

        return "\n\n".join(gaps_text) if gaps_text else "No specific gaps identified"
