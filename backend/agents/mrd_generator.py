"""
MRD Generator Agent - Creates Market Requirements Documents from Q&A.
"""

import re
import logging
from typing import Optional, List, Tuple, Dict, Callable
from uuid import UUID
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from backend.agents.base import BaseAgent
from backend.agents.prompts import (
    MRD_GENERATOR_AGENT_SYSTEM,
    MRD_GENERATOR_AGENT_USER_TEMPLATE,
    build_qa_section_for_mrd
)
from backend.agents.mrd_section_prompts import (
    get_all_sections,
    get_section_prompt,
    get_section_definition
)
from backend.models import Initiative, Context, MRD, Question, Answer, AnswerStatus
from backend.repositories.question import QuestionRepository
from backend.repositories.answer import AnswerRepository


class MRDGeneratorAgent(BaseAgent):
    """
    Agent that generates Market Requirements Documents from initiative Q&A.

    Uses Claude to synthesize answered questions into a comprehensive,
    well-structured MRD document.
    """

    def __init__(self, db: Session, model: Optional[str] = None):
        """
        Initialize MRD Generator Agent.

        Args:
            db: Database session
            model: Claude model to use (defaults to settings.anthropic_model)
        """
        super().__init__(
            db=db,
            agent_name="MRD Generator Agent",
            model=model
        )

    def generate_mrd(
        self,
        initiative: Initiative,
        context: Context,
        user_id: UUID
    ) -> Tuple[str, dict, List[str]]:
        """
        Generate an MRD for an initiative.

        Args:
            initiative: Initiative to generate MRD for
            context: Current organizational context
            user_id: User requesting MRD generation

        Returns:
            Tuple of:
            - mrd_content: Generated MRD markdown content
            - metadata: Dict with word_count, completeness_score, readiness_score
            - assumptions: List of assumptions made due to unknown answers

        Raises:
            ValueError: If no questions have been generated for this initiative
        """
        # Get all questions and answers for this initiative
        question_repo = QuestionRepository(self.db)
        answer_repo = AnswerRepository(self.db)

        questions = question_repo.get_by_initiative(initiative.id)

        if not questions:
            raise ValueError(
                "No questions have been generated for this initiative. "
                "Please generate questions first before creating an MRD."
            )

        # Build Q&A list
        questions_with_answers = []
        for question in questions:
            answer = answer_repo.get_by_question(question.id)
            questions_with_answers.append((question, answer))

        # Calculate readiness metrics
        readiness_score, assumptions = self._calculate_readiness(questions_with_answers)

        # Build prompt
        qa_section = build_qa_section_for_mrd(questions_with_answers)

        user_message = MRD_GENERATOR_AGENT_USER_TEMPLATE.format(
            title=initiative.title,
            description=initiative.description or "No description provided",
            status=initiative.status.value,
            company_mission=context.company_mission or "Not specified",
            strategic_objectives=context.strategic_objectives or "Not specified",
            target_markets=context.target_markets or "Not specified",
            competitive_landscape=context.competitive_landscape or "Not specified",
            technical_constraints=context.technical_constraints or "Not specified",
            qa_section=qa_section
        )

        # Call LLM with larger token limit for MRD generation
        mrd_content, llm_call = self.call_llm(
            system=MRD_GENERATOR_AGENT_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
            organization_id=initiative.organization_id,
            user_id=user_id,
            initiative_id=initiative.id,
            max_tokens=8192,  # Larger for comprehensive MRD
            temperature=0.7   # Slightly lower for more consistent output
        )

        # Calculate completeness score
        completeness_score = self._calculate_completeness(mrd_content, questions_with_answers)

        # Calculate word count
        word_count = len(mrd_content.split())

        metadata = {
            "word_count": word_count,
            "completeness_score": completeness_score,
            "readiness_score": readiness_score
        }

        return mrd_content, metadata, assumptions

    def _calculate_readiness(
        self,
        questions_with_answers: List[Tuple[Question, Optional[Answer]]]
    ) -> Tuple[int, List[str]]:
        """
        Calculate readiness score based on answered questions.

        Readiness score considers:
        - P0 questions: 50% weight
        - P1 questions: 30% weight
        - P2 questions: 20% weight

        Args:
            questions_with_answers: List of (question, answer) tuples

        Returns:
            Tuple of (readiness_score, assumptions_list)
            - readiness_score: 0-100 score
            - assumptions_list: List of assumption strings from Unknown answers
        """
        from backend.models import QuestionPriority

        # Count questions by priority
        p0_total = p0_answered = 0
        p1_total = p1_answered = 0
        p2_total = p2_answered = 0
        assumptions = []

        for question, answer in questions_with_answers:
            if question.priority == QuestionPriority.P0:
                p0_total += 1
                if answer and answer.answer_status == AnswerStatus.ANSWERED:
                    p0_answered += 1
                elif answer and answer.answer_status == AnswerStatus.UNKNOWN:
                    assumptions.append(f"{question.question_text}: {answer.skip_reason or 'Unknown'}")
            elif question.priority == QuestionPriority.P1:
                p1_total += 1
                if answer and answer.answer_status == AnswerStatus.ANSWERED:
                    p1_answered += 1
                elif answer and answer.answer_status == AnswerStatus.UNKNOWN:
                    assumptions.append(f"{question.question_text}: {answer.skip_reason or 'Unknown'}")
            elif question.priority == QuestionPriority.P2:
                p2_total += 1
                if answer and answer.answer_status == AnswerStatus.ANSWERED:
                    p2_answered += 1

        # Calculate weighted score
        p0_score = (p0_answered / p0_total * 50) if p0_total > 0 else 50
        p1_score = (p1_answered / p1_total * 30) if p1_total > 0 else 30
        p2_score = (p2_answered / p2_total * 20) if p2_total > 0 else 20

        readiness_score = int(p0_score + p1_score + p2_score)

        return readiness_score, assumptions

    def _calculate_completeness(
        self,
        mrd_content: str,
        questions_with_answers: List[Tuple[Question, Optional[Answer]]]
    ) -> int:
        """
        Calculate completeness score based on MRD sections present.

        Expected sections:
        1. Executive Summary
        2. Background and Context
        3. Target Audience
        4. Requirements
        5. Success Metrics
        6. Go-to-Market Strategy
        7. Timeline and Milestones
        8. Risks and Mitigation
        9. Open Questions and Assumptions

        Args:
            mrd_content: Generated MRD markdown content
            questions_with_answers: Q&A tuples (for context)

        Returns:
            Completeness score 0-100
        """
        expected_sections = [
            r"#+ .*Executive Summary",
            r"#+ .*Background",
            r"#+ .*Target Audience",
            r"#+ .*Requirements",
            r"#+ .*Success Metrics",
            r"#+ .*Go-to-Market",
            r"#+ .*Timeline",
            r"#+ .*Risks",
            r"#+ .*Open Questions|#+ .*Assumptions"
        ]

        sections_found = 0
        for pattern in expected_sections:
            if re.search(pattern, mrd_content, re.IGNORECASE | re.MULTILINE):
                sections_found += 1

        completeness = int((sections_found / len(expected_sections)) * 100)

        return completeness

    def generate_quality_disclaimer(self, readiness_score: int) -> str:
        """
        Generate a quality disclaimer based on readiness score.

        Args:
            readiness_score: Readiness score 0-100

        Returns:
            Disclaimer text
        """
        if readiness_score > 80:
            return (
                "**Quality Note:** This MRD is based on comprehensive discovery and "
                "is ready for implementation planning."
            )
        elif readiness_score >= 50:
            return (
                "**Quality Note:** This MRD includes some assumptions and areas needing "
                "further discovery. Please review the Open Questions and Assumptions "
                "section carefully before proceeding."
            )
        else:
            return (
                "**⚠️ WARNING:** This MRD has significant gaps in discovery. "
                "Additional research and validation are strongly recommended before "
                "proceeding with implementation. See Open Questions and Assumptions section."
            )

    def generate_mrd_by_sections(
        self,
        initiative: Initiative,
        context: Context,
        user_id: UUID,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Tuple[Dict[str, str], str, dict, List[str]]:
        """
        Generate an MRD section-by-section for better quality and progress tracking.

        Args:
            initiative: Initiative to generate MRD for
            context: Current organizational context
            user_id: User requesting MRD generation
            progress_callback: Optional callback(message, percent) for progress updates

        Returns:
            Tuple of:
            - sections: Dict mapping section_key to generated content
            - mrd_content: Full assembled MRD markdown
            - metadata: Dict with word_count, completeness_score, readiness_score, sections_metadata
            - assumptions: List of assumptions made due to unknown answers

        Raises:
            ValueError: If no questions have been generated for this initiative
        """
        # Get all questions and answers
        question_repo = QuestionRepository(self.db)
        answer_repo = AnswerRepository(self.db)

        questions = question_repo.get_by_initiative(initiative.id)

        if not questions:
            raise ValueError(
                "No questions have been generated for this initiative. "
                "Please generate questions first before creating an MRD."
            )

        # Build Q&A list
        questions_with_answers = []
        for question in questions:
            answer = answer_repo.get_by_question(question.id)
            questions_with_answers.append((question, answer))

        # Calculate readiness metrics
        readiness_score, assumptions = self._calculate_readiness(questions_with_answers)

        # Build common context for all sections
        qa_text = build_qa_section_for_mrd(questions_with_answers)

        # Prepare unanswered questions for final section
        unanswered = [
            f"**{q.question_text}** ({q.priority.value})"
            for q, a in questions_with_answers
            if not a or a.answer_status != AnswerStatus.ANSWERED
        ]
        unanswered_text = "\n".join(unanswered) if unanswered else "All critical questions have been answered."

        # Generate each section
        sections = {}
        section_definitions = get_all_sections()
        total_sections = len(section_definitions)

        for idx, section_def in enumerate(section_definitions):
            section_key = section_def["key"]
            section_title = section_def["title"]

            # Calculate progress (10% base + 85% for sections + 5% for assembly)
            progress_percent = 10 + int((idx / total_sections) * 85)

            if progress_callback:
                progress_callback(f"Generating {section_title}...", progress_percent)

            # Get section-specific prompts
            prompts = get_section_prompt(section_key)

            # Build user message with section-specific template
            user_message = prompts["user_template"].format(
                title=initiative.title,
                description=initiative.description or "No description provided",
                status=initiative.status.value,
                company_mission=context.company_mission or "Not specified",
                strategic_objectives=context.strategic_objectives or "Not specified",
                target_markets=context.target_markets or "Not specified",
                competitive_landscape=context.competitive_landscape or "Not specified",
                technical_constraints=context.technical_constraints or "Not specified",
                relevant_qa=qa_text,
                unanswered_questions=unanswered_text,
                assumptions="\n".join(assumptions) if assumptions else "No major assumptions"
            )

            # Call LLM for this section
            section_content, llm_call, stop_reason = self.call_llm(
                system=prompts["system"],
                messages=[{"role": "user", "content": user_message}],
                organization_id=initiative.organization_id,
                user_id=user_id,
                initiative_id=initiative.id,
                max_tokens=section_def["max_tokens"],
                temperature=0.7
            )

            # Check if section was truncated
            if stop_reason == "max_tokens":
                logger.warning(
                    f"Section '{section_title}' was truncated at max_tokens limit "
                    f"({section_def['max_tokens']} tokens). Content may be incomplete. "
                    f"Initiative: {initiative.id}"
                )

            sections[section_key] = section_content.strip()

        # Perform editorial pass with MRD Editor Agent
        if progress_callback:
            progress_callback("Editing and consolidating MRD...", 90)

        from backend.agents.mrd_editor import MRDEditorAgent
        editor = MRDEditorAgent(self.db, self.model)

        # Generate quality disclaimer
        disclaimer = self.generate_quality_disclaimer(readiness_score)

        # Let the editor consolidate all sections
        mrd_content, edited_word_count = editor.edit_mrd(
            initiative=initiative,
            sections=sections,
            quality_disclaimer=disclaimer,
            user_id=user_id
        )

        # Calculate section-level metadata (pre-edit)
        sections_metadata = {
            section_key: {
                "word_count": len(content.split()),
                "char_count": len(content)
            }
            for section_key, content in sections.items()
        }

        # Calculate total pre-edit word count for comparison
        pre_edit_word_count = sum(meta["word_count"] for meta in sections_metadata.values())

        # Log the editing impact
        reduction_pct = int(100 * (1 - edited_word_count / pre_edit_word_count)) if pre_edit_word_count > 0 else 0
        logger.info(
            f"MRD editing complete for initiative {initiative.id}. "
            f"Pre-edit: {pre_edit_word_count} words, Post-edit: {edited_word_count} words, "
            f"Reduction: {reduction_pct}%"
        )

        metadata = {
            "word_count": edited_word_count,
            "completeness_score": 100,  # All sections generated and edited
            "readiness_score": readiness_score,
            "sections_metadata": sections_metadata,
            "generation_method": "multi_section_with_editor",
            "pre_edit_word_count": pre_edit_word_count,
            "editing_reduction_pct": reduction_pct
        }

        return sections, mrd_content, metadata, assumptions
