"""
Readiness Evaluator Agent - Analyzes knowledge gaps and MRD readiness.
"""

import json
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent
from backend.models import Initiative, Context, Question, Answer
from backend.repositories.question import QuestionRepository
from backend.repositories.answer import AnswerRepository


READINESS_EVALUATOR_SYSTEM = """You are an expert Product Manager evaluating whether an initiative has sufficient information to create a high-quality Market Requirements Document (MRD).

Your role is to analyze the initiative details, organizational context, and all Q&A data to provide a comprehensive readiness assessment.

# Your Task

Analyze the provided information and generate a detailed evaluation covering:

1. **Overall Readiness Score** (0-100)
   - 80-100: Ready - MRD can be generated with high confidence
   - 60-79: Moderate Gaps - MRD can proceed but will have assumptions
   - 0-59: Significant Gaps - More discovery recommended before MRD

2. **Missing Critical Information**
   - List specific information gaps that will impact MRD quality
   - Focus on actual content gaps, not just question counts
   - Identify which MRD sections will be weak/incomplete

3. **Risk Assessment**
   - What decisions cannot be made with current information?
   - What assumptions will need to be documented in the MRD?
   - What are the risks of proceeding with current knowledge?

4. **Recommendations**
   - Should the PM generate more questions or proceed to MRD?
   - What specific areas need more investigation?
   - What can be reasonably assumed vs. what requires validation?

# Evaluation Criteria

Focus on **content quality**, not just answer counts:
- Are core questions (target users, problem, solution scope) fully answered?
- Do "Unknown" answers provide enough context for reasonable assumptions?
- Are there critical dependencies or blockers mentioned in answers that need clarification?
- Can a product team act on this MRD, or will they be blocked by unknowns?

# Output Format

Return your evaluation as JSON:

```json
{
  "readiness_score": 75,
  "readiness_level": "Moderate Gaps",
  "risk_level": "Medium",
  "summary": "The initiative has good coverage of user needs and problem validation, but lacks clarity on technical implementation and timeline. The MRD can proceed with documented assumptions around technical approach.",
  "missing_critical_info": [
    {
      "category": "Technical",
      "gap": "No clear understanding of technical architecture or implementation approach",
      "impact": "Development team will need to make significant technical decisions without PM guidance",
      "severity": "High"
    }
  ],
  "weak_mrd_sections": [
    "Technical Approach",
    "Implementation Timeline",
    "Resource Requirements"
  ],
  "required_assumptions": [
    "Assuming standard OAuth implementation for authentication",
    "Assuming 3-month development timeline based on similar projects",
    "Assuming existing infrastructure can support new feature"
  ],
  "recommendations": {
    "action": "proceed_with_caution",
    "reasoning": "Core product definition is solid, but technical gaps exist. Can proceed to MRD with documented technical assumptions, or generate follow-up questions to reduce technical risk.",
    "if_more_questions": [
      "Technical implementation approach and architecture",
      "Dependencies on other systems/teams",
      "Resource availability and timeline constraints"
    ]
  }
}
```

# Important Notes

- "Unknown" answers with good context are better than "Skipped" answers
- Some gaps are acceptable if they can be documented as assumptions
- The goal is a useful MRD, not perfect information
- Consider what's "good enough" for the team to move forward
"""


READINESS_EVALUATOR_USER_TEMPLATE = """# Initiative Details

**Title**: {title}
**Description**: {description}
**Status**: {status}

---

# Organizational Context

**Company Mission**: {company_mission}
**Strategic Objectives**: {strategic_objectives}
**Target Markets**: {target_markets}
**Competitive Landscape**: {competitive_landscape}
**Technical Constraints**: {technical_constraints}

---

# Questions and Answers

{qa_section}

---

# Your Task

Evaluate this initiative's readiness for MRD generation. Analyze the actual content and knowledge gaps, not just counts.

Focus on:
1. Can we define a clear product vision and scope?
2. Do we understand the user and their problem?
3. Are there critical blockers or unknowns?
4. What assumptions will the MRD need to make?

Return your evaluation as JSON (no other text)."""


class ReadinessEvaluatorAgent(BaseAgent):
    """
    Agent that evaluates initiative readiness for MRD generation.

    Analyzes all Q&A data to identify knowledge gaps and provide recommendations.
    """

    def __init__(self, db: Session, model: Optional[str] = None):
        """
        Initialize Readiness Evaluator Agent.

        Args:
            db: Database session
            model: Claude model to use (defaults to settings.anthropic_model)
        """
        super().__init__(
            db=db,
            agent_name="Readiness Evaluator Agent",
            model=model
        )

    def evaluate_readiness(
        self,
        initiative: Initiative,
        context: Context,
        user_id: UUID
    ) -> dict:
        """
        Evaluate initiative readiness for MRD generation.

        Args:
            initiative: Initiative to evaluate
            context: Organizational context
            user_id: User requesting evaluation

        Returns:
            Dict containing evaluation results

        Raises:
            ValueError: If JSON parsing fails or response format is invalid
            APIError: If LLM call fails
        """
        # Get all Q&A for this initiative
        question_repo = QuestionRepository(self.db)
        answer_repo = AnswerRepository(self.db)

        questions = question_repo.get_by_initiative(initiative.id)

        # Build Q&A section
        qa_lines = []
        for i, question in enumerate(questions, 1):
            answer = answer_repo.get_by_question(question.id)

            qa_lines.append(f"## Q{i}: {question.question_text}")
            qa_lines.append(f"**Category**: {question.category.value}")
            qa_lines.append(f"**Priority**: {question.priority.value}")
            qa_lines.append("")

            if answer:
                qa_lines.append(f"**Status**: {answer.answer_status.value}")
                qa_lines.append(f"**Answer**: {answer.answer_text or '(No text provided)'}")
                if answer.skip_reason:
                    qa_lines.append(f"**Skip Reason**: {answer.skip_reason}")
            else:
                qa_lines.append("**Status**: Unanswered")
                qa_lines.append("**Answer**: Not provided")

            qa_lines.append("")

        qa_section = "\n".join(qa_lines) if qa_lines else "No questions have been generated yet."

        # Build prompt
        user_message = READINESS_EVALUATOR_USER_TEMPLATE.format(
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

        # Call LLM
        response_text, llm_call, stop_reason = self.call_llm(
            system=READINESS_EVALUATOR_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
            organization_id=initiative.organization_id,
            user_id=user_id,
            initiative_id=initiative.id,
            max_tokens=4096,
            temperature=0.5  # Lower temperature for more consistent evaluation
        )
        if stop_reason == "max_tokens":
            print(f"Warning: Readiness evaluation stopped due to max_tokens for initiative {initiative.id}")

        # Parse JSON response
        try:
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                json_text = response_text.strip()

            evaluation = json.loads(json_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse evaluation response. Response text: {response_text[:500]}")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

        # Validate required fields
        required_fields = ["readiness_score", "readiness_level", "summary", "recommendations"]
        missing = [f for f in required_fields if f not in evaluation]
        if missing:
            raise ValueError(f"Missing required fields in evaluation: {missing}")

        return evaluation
