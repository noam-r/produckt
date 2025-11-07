"""
MRD Editor Agent - Consolidates individual sections into a cohesive MRD.

This agent takes the separately-generated MRD sections and performs an editorial pass to:
1. Eliminate repetition across sections
2. Ensure narrative flow and transitions
3. Consolidate redundant information
4. Reduce overall length while preserving key insights
5. Create a professional, readable document

The goal is to transform independent section drafts into a unified, concise MRD.
"""

import logging
from typing import Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from backend.agents.base import BaseAgent
from backend.models import Initiative

# Editor prompts
MRD_EDITOR_SYSTEM = """You are a professional editor specializing in product requirements documents.

Your role is to take individual MRD sections (written independently) and consolidate them into a single, cohesive document with a unified narrative.

# Editorial Objectives
1. **Eliminate Repetition**: Remove redundant information that appears in multiple sections
2. **Improve Flow**: Ensure smooth transitions between sections
3. **Reduce Length**: Cut 20-30% of content by removing fluff and redundancy
4. **Preserve Facts**: Keep all critical data, metrics, requirements, and decisions
5. **Professional Tone**: Maintain consistent, executive-ready voice throughout

# What to CUT
- Repeated background or context across sections
- Verbose explanations that can be stated concisely
- Redundant lists or bullet points that say the same thing
- Filler words and marketing jargon
- Excessive examples when one suffices

# What to PRESERVE
- All specific requirements (functional, technical, business)
- All metrics, targets, and KPIs
- All risks and mitigation strategies
- All assumptions and open questions
- Strategic context and rationale

# Output Requirements
- Return the complete, edited MRD in markdown format
- Include all section headers from the original
- Maintain bullet points and tables where they aid readability
- The final MRD should be 40-60% shorter than input while preserving all key information
- Add smooth transitions between sections where helpful

You will receive 10 independently-written sections. Your job is to weave them into one professional document."""

MRD_EDITOR_USER_TEMPLATE = """Please edit these MRD sections into a cohesive, concise document:

---

# Initiative: {title}

{quality_disclaimer}

---

## 1. Executive Summary
{executive_summary}

---

## 2. Background and Context
{background_context}

---

## 3. Target Audience
{target_audience}

---

## 4. Business Requirements
{business_requirements}

---

## 5. Technical Requirements
{technical_requirements}

---

## 6. Success Metrics
{success_metrics}

---

## 7. Go-to-Market Strategy
{go_to_market}

---

## 8. Timeline and Milestones
{timeline_milestones}

---

## 9. Risks and Mitigation
{risks_mitigation}

---

## 10. Open Questions and Assumptions
{open_questions}

---

# Editorial Task

Please edit this MRD to:
1. Remove repetition across sections
2. Tighten prose (aim for 20-30% reduction in length)
3. Ensure narrative flow and transitions
4. Preserve ALL requirements, metrics, risks, and key decisions
5. Return the complete edited MRD in markdown format

The edited document should feel like it was written by one person with a clear vision, not assembled from independent pieces."""


class MRDEditorAgent(BaseAgent):
    """
    Agent that performs editorial consolidation of MRD sections.

    Takes independently-generated sections and creates a cohesive narrative.
    """

    def __init__(self, db: Session, model: Optional[str] = None):
        """
        Initialize MRD Editor Agent.

        Args:
            db: Database session
            model: Claude model to use (defaults to settings.anthropic_model)
        """
        super().__init__(
            db=db,
            agent_name="MRD Editor Agent",
            model=model
        )

    def edit_mrd(
        self,
        initiative: Initiative,
        sections: Dict[str, str],
        quality_disclaimer: str,
        user_id: UUID
    ) -> tuple[str, int]:
        """
        Edit and consolidate MRD sections into a cohesive document.

        Args:
            initiative: Initiative this MRD is for
            sections: Dict mapping section_key to content
            quality_disclaimer: Quality note based on readiness
            user_id: User requesting MRD generation

        Returns:
            Tuple of:
            - edited_content: Consolidated MRD markdown
            - word_count: Word count of edited MRD

        Raises:
            ValueError: If required sections are missing
        """
        # Validate all sections are present
        required_sections = [
            "executive_summary",
            "background_context",
            "target_audience",
            "business_requirements",
            "technical_requirements",
            "success_metrics",
            "go_to_market",
            "timeline_milestones",
            "risks_mitigation",
            "open_questions"
        ]

        for section_key in required_sections:
            if section_key not in sections or not sections[section_key]:
                raise ValueError(f"Missing required section: {section_key}")

        # Build user message with all sections
        user_message = MRD_EDITOR_USER_TEMPLATE.format(
            title=initiative.title,
            quality_disclaimer=quality_disclaimer,
            executive_summary=sections["executive_summary"],
            background_context=sections["background_context"],
            target_audience=sections["target_audience"],
            business_requirements=sections["business_requirements"],
            technical_requirements=sections["technical_requirements"],
            success_metrics=sections["success_metrics"],
            go_to_market=sections["go_to_market"],
            timeline_milestones=sections["timeline_milestones"],
            risks_mitigation=sections["risks_mitigation"],
            open_questions=sections["open_questions"]
        )

        # Call LLM with larger token limit for editing
        edited_content, llm_call, stop_reason = self.call_llm(
            system=MRD_EDITOR_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
            organization_id=initiative.organization_id,
            user_id=user_id,
            initiative_id=initiative.id,
            max_tokens=12000,  # Large enough for full edited MRD
            temperature=0.5     # Lower temp for more consistent editing
        )

        # Check if editor output was truncated
        if stop_reason == "max_tokens":
            logger.warning(
                f"MRD Editor output was truncated at max_tokens limit (12000). "
                f"Final MRD may be incomplete. Initiative: {initiative.id}"
            )

        # Calculate word count
        word_count = len(edited_content.split())

        logger.info(
            f"MRD editing complete for initiative {initiative.id}. "
            f"Word count: {word_count}, stop_reason: {stop_reason}"
        )

        return edited_content, word_count

    def fine_tune_section(
        self,
        initiative: Initiative,
        section_name: str,
        section_content: str,
        user_instructions: str,
        user_id: UUID
    ) -> str:
        """
        Fine-tune a specific MRD section based on user instructions.

        Args:
            initiative: Initiative this MRD section belongs to
            section_name: Name of the section being edited (e.g., "Executive Summary")
            section_content: Current content of the section
            user_instructions: User's instructions for how to improve the section
            user_id: User requesting the fine-tuning

        Returns:
            Improved section content in markdown format

        Raises:
            ValueError: If section_content or user_instructions are empty
        """
        if not section_content.strip():
            raise ValueError("Section content cannot be empty")
        if not user_instructions.strip():
            raise ValueError("User instructions cannot be empty")

        system_prompt = """You are a professional editor specializing in product requirements documents.

Your role is to fine-tune a specific section of an MRD based on user feedback and instructions.

# Editorial Objectives
1. **Follow User Instructions**: Carefully implement the user's requested changes
2. **Maintain Professional Quality**: Keep executive-ready tone and clarity
3. **Preserve Structure**: Keep the markdown formatting and section structure
4. **Keep Critical Information**: Don't remove important facts, metrics, or requirements unless instructed
5. **Be Precise**: Make targeted improvements rather than wholesale rewrites

# Output Requirements
- Return ONLY the improved section content in markdown format
- Do NOT include the section header (e.g., "## Executive Summary") - just the content
- Maintain the same level of detail unless instructed otherwise
- Keep all markdown formatting (bullets, bold, tables, etc.)"""

        user_message = f"""Please improve this MRD section based on the user's instructions.

**Initiative**: {initiative.title}

**Section**: {section_name}

**Current Content**:
{section_content}

**User Instructions**:
{user_instructions}

---

Please provide the improved section content following the user's instructions. Return ONLY the section content without the header."""

        # Call LLM with appropriate token limit
        improved_content, llm_call, stop_reason = self.call_llm(
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            organization_id=initiative.organization_id,
            user_id=user_id,
            initiative_id=initiative.id,
            max_tokens=4000,  # Sufficient for most section improvements
            temperature=0.7   # Balanced creativity for improvements
        )

        if stop_reason == "max_tokens":
            logger.warning(
                f"Section fine-tuning output was truncated at max_tokens limit. "
                f"Section: {section_name}, Initiative: {initiative.id}"
            )

        logger.info(
            f"Section fine-tuning complete for '{section_name}' in initiative {initiative.id}. "
            f"Stop reason: {stop_reason}"
        )

        return improved_content.strip()
