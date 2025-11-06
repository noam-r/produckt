"""
Knowledge Gap Agent - Identifies critical questions for initiative validation.
"""

import json
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent
from backend.agents.prompts import (
    KNOWLEDGE_GAP_AGENT_SYSTEM,
    KNOWLEDGE_GAP_AGENT_USER_TEMPLATE,
    build_previous_qa_section
)
from backend.models import Initiative, Context, Question, Answer, QuestionCategory, QuestionPriority
from backend.repositories.question import QuestionRepository
from backend.repositories.answer import AnswerRepository


class KnowledgeGapAgent(BaseAgent):
    """
    Agent that analyzes initiatives and generates targeted questions.

    Uses Claude to identify critical knowledge gaps that need to be filled
    before an MRD can be generated.
    """

    def __init__(self, db: Session, model: Optional[str] = None):
        """
        Initialize Knowledge Gap Agent.

        Args:
            db: Database session
            model: Claude model to use (defaults to settings.anthropic_model)
        """
        super().__init__(
            db=db,
            agent_name="Knowledge Gap Agent",
            model=model
        )

    def generate_questions(
        self,
        initiative: Initiative,
        context: Context,
        user_id: UUID
    ) -> list[Question]:
        """
        Generate questions for an initiative based on organizational context.

        Args:
            initiative: Initiative to analyze
            context: Organizational context (current version)
            user_id: User requesting question generation

        Returns:
            List of generated Question objects (not yet persisted)

        Raises:
            ValueError: If JSON parsing fails or response format is invalid
            APIError: If LLM call fails
        """
        # Get previous Q&A for this initiative
        question_repo = QuestionRepository(self.db)
        answer_repo = AnswerRepository(self.db)

        previous_questions = question_repo.get_by_initiative(initiative.id)
        questions_with_answers = []

        for q in previous_questions:
            answer = answer_repo.get_by_question(q.id)
            questions_with_answers.append((q, answer))

        # Build prompt
        previous_qa_section = build_previous_qa_section(questions_with_answers)

        user_message = KNOWLEDGE_GAP_AGENT_USER_TEMPLATE.format(
            title=initiative.title,
            description=initiative.description or "No description provided",
            status=initiative.status.value,
            iteration=initiative.iteration_count + 1,  # Next iteration
            company_mission=context.company_mission or "Not specified",
            strategic_objectives=context.strategic_objectives or "Not specified",
            target_markets=context.target_markets or "Not specified",
            competitive_landscape=context.competitive_landscape or "Not specified",
            technical_constraints=context.technical_constraints or "Not specified",
            previous_qa_section=previous_qa_section
        )

        # Call LLM
        response_text, llm_call, stop_reason = self.call_llm(
            system=KNOWLEDGE_GAP_AGENT_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
            organization_id=initiative.organization_id,
            user_id=user_id,
            initiative_id=initiative.id,
            max_tokens=4096,
            temperature=1.0
        )
        if stop_reason == "max_tokens":
            print(f"Warning: Knowledge gap generation stopped due to max_tokens for initiative {initiative.id}")

        # Parse JSON response
        # Claude Sonnet 4.5 may wrap JSON in markdown code blocks
        try:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Try direct parsing
                json_text = response_text.strip()

            questions_data = json.loads(json_text)
        except json.JSONDecodeError as e:
            # Log the actual response for debugging
            print(f"Failed to parse LLM response. Response text: {response_text[:500]}")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

        if not isinstance(questions_data, list):
            raise ValueError(f"Expected JSON array, got {type(questions_data)}")

        # Get all existing questions for deduplication
        existing_questions = question_repo.get_by_initiative(initiative.id)
        existing_question_texts = {q.question_text.lower().strip() for q in existing_questions}

        # Convert to Question objects
        questions = []
        next_iteration = initiative.iteration_count + 1
        duplicates_filtered = 0

        for item in questions_data:
            # Validate required fields
            required_fields = ["category", "priority", "question_text", "rationale"]
            missing = [f for f in required_fields if f not in item]
            if missing:
                raise ValueError(f"Missing required fields: {missing}")

            # Parse enums
            try:
                category = QuestionCategory(item["category"])
            except ValueError:
                raise ValueError(f"Invalid category: {item['category']}")

            try:
                priority = QuestionPriority(item["priority"])
            except ValueError:
                raise ValueError(f"Invalid priority: {item['priority']}")

            # Check for exact duplicates (case-insensitive)
            question_text_normalized = item["question_text"].lower().strip()
            if question_text_normalized in existing_question_texts:
                # Skip this duplicate question
                duplicates_filtered += 1
                print(f"Warning: Filtered duplicate question: {item['question_text'][:100]}")
                continue

            # Create Question object
            question = Question(
                initiative_id=initiative.id,
                category=category,
                priority=priority,
                question_text=item["question_text"],
                rationale=item["rationale"],
                blocks_mrd_generation=item.get("blocks_mrd_generation", priority == QuestionPriority.P0),
                iteration=next_iteration
            )

            questions.append(question)

        # Log if duplicates were filtered
        if duplicates_filtered > 0:
            print(f"Filtered {duplicates_filtered} duplicate question(s) for initiative {initiative.id}")

        return questions

    def regenerate_questions(
        self,
        initiative: Initiative,
        context: Context,
        user_id: UUID,
        keep_existing: bool = False
    ) -> list[Question]:
        """
        Regenerate questions for an initiative.

        Args:
            initiative: Initiative to regenerate questions for
            context: Current organizational context
            user_id: User requesting regeneration
            keep_existing: If True, keep existing unanswered questions from current iteration

        Returns:
            List of newly generated Question objects

        Raises:
            ValueError: If JSON parsing fails or response format is invalid
        """
        # If not keeping existing, we'll treat this as a fresh generation
        # The generate_questions method already handles previous iterations properly
        new_questions = self.generate_questions(initiative, context, user_id)

        if keep_existing:
            # Get unanswered questions from current iteration
            question_repo = QuestionRepository(self.db)
            answer_repo = AnswerRepository(self.db)

            current_questions = question_repo.get_by_initiative(
                initiative.id,
                iteration=initiative.iteration_count
            )

            unanswered = [
                q for q in current_questions
                if not answer_repo.get_by_question(q.id)
            ]

            # Combine with new questions
            # Adjust iteration for existing questions
            for q in unanswered:
                q.iteration = initiative.iteration_count + 1

            return unanswered + new_questions

        return new_questions
