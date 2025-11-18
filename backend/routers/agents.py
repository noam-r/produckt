"""
AI Agent API endpoints for question generation and MRD creation.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from backend.database import get_db
from backend.models import User, JobType
from backend.repositories.initiative import InitiativeRepository
from backend.repositories.context import ContextRepository
from backend.repositories.question import QuestionRepository
from backend.repositories.evaluation import EvaluationRepository
from backend.repositories.job import JobRepository
from backend.auth.dependencies import get_current_user
from backend.agents.knowledge_gap import KnowledgeGapAgent
from backend.agents.mrd_generator import MRDGeneratorAgent
from backend.agents.mrd_editor import MRDEditorAgent
from backend.agents.scoring import ScoringAgent
from backend.agents.readiness_evaluator import ReadinessEvaluatorAgent
from backend.repositories.mrd import MRDRepository
from backend.repositories.score import ScoreRepository
from backend.schemas.question import QuestionResponse
from backend.schemas.score import ScoreResponse
from backend.schemas.mrd import MRDResponse, MRDContentResponse
from backend.services.pdf_generator import markdown_to_pdf
from fastapi.responses import Response
from backend.services.job_executor import execute_job_in_background
from backend.services.quality_scorer import calculate_quality_score
from backend.agents.scoring_gap_analyzer import ScoringGapAnalyzer


router = APIRouter(prefix="/agents", tags=["AI Agents"])


# Request models
class FineTuneSectionRequest(BaseModel):
    section_name: str = Field(..., description="Name of the section to fine-tune")
    section_content: str = Field(..., description="Current content of the section")
    user_instructions: str = Field(..., description="User's instructions for improving the section")


@router.post("/initiatives/{initiative_id}/generate-questions")
def generate_questions(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate questions for an initiative using AI (async job).

    This endpoint creates an async job that:
    1. Analyzes the initiative and organizational context
    2. Uses Claude to generate targeted questions across all categories
    3. Saves questions to the database
    4. Increments the initiative's iteration count

    Only generates questions for initiatives in DRAFT or IN_REVIEW status.

    Returns:
        Dict with job_id for polling job status
    """
    # Get initiative
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Check status - allow question generation for Draft and In_QA initiatives
    if initiative.status.value not in ["Draft", "In_QA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot generate questions for initiative in {initiative.status.value} status"
        )

    # Verify context exists
    context_repo = ContextRepository(db)
    context = context_repo.get_current(current_user.organization_id)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organizational context found. Please create context first."
        )

    # Create async job
    job_repo = JobRepository(db)
    job = job_repo.create_job(
        job_type=JobType.GENERATE_QUESTIONS,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        initiative_id=initiative_id
    )
    db.commit()

    # Start background execution
    execute_job_in_background(job.id)

    # Return job ID for polling
    return {"job_id": str(job.id)}


@router.post("/initiatives/{initiative_id}/regenerate-questions", response_model=list[QuestionResponse])
def regenerate_questions(
    initiative_id: UUID,
    keep_unanswered: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Regenerate questions for an initiative.

    This is useful when:
    - The initiative description has changed significantly
    - The organizational context has been updated
    - You want fresh questions based on new information

    Args:
        initiative_id: Initiative to regenerate questions for
        keep_unanswered: If True, keeps unanswered questions from current iteration

    Only regenerates for initiatives in DRAFT or IN_REVIEW status.
    """
    # Get initiative
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Check status - allow question regeneration for Draft and In_QA initiatives
    if initiative.status.value not in ["Draft", "In_QA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot regenerate questions for initiative in {initiative.status.value} status"
        )

    # Get current context
    context_repo = ContextRepository(db)
    context = context_repo.get_current(current_user.organization_id)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organizational context found. Please create context first."
        )

    # Regenerate questions using agent
    try:
        agent = KnowledgeGapAgent(db)
        questions = agent.regenerate_questions(
            initiative=initiative,
            context=context,
            user_id=current_user.id,
            keep_existing=keep_unanswered
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate questions: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during question regeneration: {str(e)}"
        )

    # Save questions to database
    question_repo = QuestionRepository(db)

    for question in questions:
        question_repo.create(question)

    # Increment initiative iteration
    initiative_repo.increment_iteration(initiative_id, current_user.organization_id)

    db.commit()

    # Return questions
    return [QuestionResponse.model_validate(q) for q in questions]


@router.post("/initiatives/{initiative_id}/evaluate-readiness")
def evaluate_readiness(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluate initiative readiness for MRD generation using AI (async job).

    This endpoint creates an async job that:
    1. Analyzes all Q&A data and initiative details
    2. Uses Claude to assess knowledge gaps and MRD readiness
    3. Provides recommendations on next steps
    4. Persists evaluation to database

    Returns:
        Dict with job_id for polling job status
    """
    # Get initiative
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Verify context exists
    context_repo = ContextRepository(db)
    context = context_repo.get_current(current_user.organization_id)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organizational context found. Please create context first."
        )

    # Create async job
    job_repo = JobRepository(db)
    job = job_repo.create_job(
        job_type=JobType.EVALUATE_READINESS,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        initiative_id=initiative_id
    )
    db.commit()

    # Start background execution
    execute_job_in_background(job.id)

    # Return job ID for polling
    return {"job_id": str(job.id)}


@router.get("/initiatives/{initiative_id}/evaluate-readiness")
def get_evaluation(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the latest evaluation for an initiative.

    Returns:
        Dict containing evaluation data, or 404 if no evaluation exists
    """
    # Get initiative to verify access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Get evaluation
    evaluation_repo = EvaluationRepository(db)
    evaluation = evaluation_repo.get_by_initiative(initiative_id)

    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluation found for this initiative"
        )

    return evaluation.evaluation_data


@router.post("/initiatives/{initiative_id}/generate-mrd")
def generate_mrd(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate an MRD (Market Requirements Document) for an initiative (async job).

    This endpoint creates an async job that:
    1. Collects all answered questions for the initiative
    2. Uses Claude to synthesize them into a comprehensive MRD
    3. Calculates readiness and completeness scores
    4. Saves the MRD to the database (creates or updates/increments version)

    Requirements:
    - Initiative must have generated questions
    - Organizational context must exist
    - At least some questions should be answered (can generate with gaps)

    Returns:
        Dict with job_id for polling job status
    """
    # Get initiative
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Verify context exists
    context_repo = ContextRepository(db)
    context = context_repo.get_current(current_user.organization_id)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organizational context found. Please create context first."
        )

    # Create async job
    job_repo = JobRepository(db)
    job = job_repo.create_job(
        job_type=JobType.GENERATE_MRD,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        initiative_id=initiative_id
    )
    db.commit()

    # Start background execution
    execute_job_in_background(job.id)

    # Return job ID for polling
    return {"job_id": str(job.id)}


@router.get("/initiatives/{initiative_id}/mrd", response_model=MRDResponse)
def get_mrd(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the MRD for an initiative.

    Returns the most recent version of the MRD if it exists.
    """
    # Verify initiative access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Get MRD
    mrd_repo = MRDRepository(db)
    mrd = mrd_repo.get_by_initiative(initiative_id)

    if not mrd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MRD not found for this initiative. Generate one first."
        )

    return mrd


@router.get("/initiatives/{initiative_id}/mrd/content", response_model=MRDContentResponse)
def get_mrd_content(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the MRD content (for export/download).

    Returns just the content, quality disclaimer, word count, and version.
    Useful for exporting to files.
    """
    # Verify initiative access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Get MRD
    mrd_repo = MRDRepository(db)
    mrd = mrd_repo.get_by_initiative(initiative_id)

    if not mrd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MRD not found for this initiative. Generate one first."
        )

    return MRDContentResponse(
        content=mrd.content,
        quality_disclaimer=mrd.quality_disclaimer,
        word_count=mrd.word_count or 0,
        version=mrd.version
    )


@router.post("/initiatives/{initiative_id}/mrd/fine-tune-section")
def fine_tune_mrd_section(
    initiative_id: UUID,
    request: FineTuneSectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fine-tune a specific section of the MRD based on user instructions.

    This endpoint:
    1. Calls the MRD Editor Agent to improve the section content
    2. Updates the MRD with the improved section
    3. Re-calculates completeness score
    4. Increments MRD version
    5. Returns the updated MRD

    Requirements:
    - MRD must exist for the initiative
    - Section content must not be empty
    - User instructions must not be empty
    """
    import re

    # Verify initiative access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Get existing MRD
    mrd_repo = MRDRepository(db)
    mrd = mrd_repo.get_by_initiative(initiative_id)

    if not mrd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MRD not found for this initiative. Generate one first."
        )

    # Validate request
    if not request.section_content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section content cannot be empty"
        )

    if not request.user_instructions.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User instructions cannot be empty"
        )

    # Call MRD Editor Agent to fine-tune the section
    editor_agent = MRDEditorAgent(db)
    try:
        improved_content = editor_agent.fine_tune_section(
            initiative=initiative,
            section_name=request.section_name,
            section_content=request.section_content,
            user_instructions=request.user_instructions,
            user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Replace the section in the full MRD content
    # We need to find and replace the specific section content
    current_content = mrd.content

    # Check if the section content exists in the MRD
    if request.section_content not in current_content:
        # Log for debugging
        logger.warning(
            f"Section content not found in MRD for initiative {initiative_id}. "
            f"Section: {request.section_name}, Content length: {len(request.section_content)}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section content not found in MRD. The content may have been modified."
        )

    # Replace the section content (only first occurrence)
    updated_content = current_content.replace(request.section_content, improved_content, 1)

    # Recalculate word count
    new_word_count = len(updated_content.split())

    # Recalculate completeness score (simple version - can be enhanced)
    # For now, keep the existing completeness score since the structure hasn't changed
    # A more sophisticated approach would re-analyze the content

    # Update MRD in database
    mrd.content = updated_content
    mrd.word_count = new_word_count
    mrd.version += 1

    # Recalculate quality score after MRD fine-tuning
    quality_score, quality_breakdown = calculate_quality_score(db, initiative_id)
    initiative.readiness_score = quality_score
    logger.info(f"Quality score recalculated to {quality_score}% after MRD fine-tuning")

    db.commit()
    db.refresh(mrd)

    return mrd


@router.get("/initiatives/{initiative_id}/mrd/pdf")
def export_mrd_pdf(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export the MRD as a PDF file.

    Returns a properly formatted PDF with correct page breaks.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Get initiative (with organization filtering)
        initiative_repo = InitiativeRepository(db)
        initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

        if not initiative:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Initiative not found"
            )

        # Get MRD
        mrd_repo = MRDRepository(db)
        mrd = mrd_repo.get_by_initiative(initiative_id)

        if not mrd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MRD not found for this initiative. Generate one first."
            )

        logger.info(f"Generating PDF for MRD {mrd.id}, content length: {len(mrd.content)} chars")

        # Generate PDF
        pdf_bytes = markdown_to_pdf(
            markdown_content=mrd.content,
            title=f"MRD - {initiative.title}"
        )

        logger.info(f"PDF generated successfully, {len(pdf_bytes)} bytes")

        # Return PDF with proper headers
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="mrd-{initiative_id}.pdf"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.delete("/initiatives/{initiative_id}/mrd", status_code=status.HTTP_204_NO_CONTENT)
def delete_mrd(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete the MRD for an initiative.

    This allows regenerating from scratch with a fresh version 1.
    """
    # Verify initiative access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Delete MRD
    mrd_repo = MRDRepository(db)
    deleted = mrd_repo.delete_by_initiative(initiative_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MRD not found for this initiative"
        )

    db.commit()

    return None


@router.post("/initiatives/{initiative_id}/calculate-scores")
def calculate_scores(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate RICE and FDV scores for an initiative (async with job).

    This endpoint:
    1. Creates a background job for score calculation
    2. Returns immediately with job ID for polling
    3. Job runs score calculation asynchronously

    Requirements:
    - Initiative must have an MRD generated
    - Organizational context must exist

    Returns job ID for status polling.
    """
    from backend.models import Job, JobStatus

    print(f"\n{'='*80}")
    print(f"[ENDPOINT CALLED] POST /api/agents/initiatives/{initiative_id}/calculate-scores")
    print(f"[ENDPOINT CALLED] User: {current_user.email} (ID: {current_user.id})")
    print(f"{'='*80}\n")

    # Get initiative
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Get current context
    context_repo = ContextRepository(db)
    context = context_repo.get_current(current_user.organization_id)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organizational context found. Please create context first."
        )

    # Create background job
    job_repo = JobRepository(db)
    job = Job(
        job_type=JobType.CALCULATE_SCORES,
        initiative_id=initiative_id,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        status=JobStatus.PENDING,
        progress_percent=0,
        progress_message="Starting score calculation..."
    )
    job_repo.create(job)
    db.commit()

    print(f"[SCORING] Created job {job.id} for score calculation")

    # Execute job in background
    execute_job_in_background(job.id)

    return {
        "job_id": str(job.id),
        "status": "pending",
        "message": "Score calculation started in background"
    }


@router.get("/initiatives/{initiative_id}/scores", response_model=ScoreResponse)
def get_scores(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the scores for an initiative.

    Returns the most recent RICE and FDV scores if they exist.
    """
    # Verify initiative access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Get scores
    score_repo = ScoreRepository(db)
    score = score_repo.get_by_initiative(initiative_id)

    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scores not found for this initiative. Calculate them first."
        )

    return score


@router.get("/initiatives/{initiative_id}/scores/pdf")
def export_scores_pdf(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export the scorecard as a PDF file.

    Returns a properly formatted PDF with RICE and FDV scores and reasoning.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Get initiative
        initiative_repo = InitiativeRepository(db)
        initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

        if not initiative:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Initiative not found"
            )

        # Get scores
        score_repo = ScoreRepository(db)
        score = score_repo.get_by_initiative(initiative_id)

        if not score:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scores not found for this initiative. Calculate them first."
            )

        # Import PDF generator
        from backend.services.pdf_generator import scorecard_to_pdf

        # Prepare data
        rice_data = {
            'reach': score.reach,
            'impact': score.impact,
            'confidence': score.confidence,
            'effort': score.effort
        }

        fdv_data = {
            'feasibility': score.feasibility,
            'desirability': score.desirability,
            'viability': score.viability
        }

        # Generate PDF
        pdf_bytes = scorecard_to_pdf(
            initiative_title=initiative.title,
            rice_score=score.rice_score,
            rice_data=rice_data,
            rice_reasoning=score.rice_reasoning or {},
            fdv_score=score.fdv_score,
            fdv_data=fdv_data,
            fdv_reasoning=score.fdv_reasoning or {}
        )

        logger.info(f"Scorecard PDF generated successfully, {len(pdf_bytes)} bytes")

        # Return PDF with proper headers
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="scorecard-{initiative_id}.pdf"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating scorecard PDF: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate scorecard PDF: {str(e)}"
        )


@router.delete("/initiatives/{initiative_id}/scores", status_code=status.HTTP_204_NO_CONTENT)
def delete_scores(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete the scores for an initiative.

    This allows recalculating scores from scratch.
    """
    # Verify initiative access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Delete scores
    score_repo = ScoreRepository(db)
    deleted = score_repo.delete_by_initiative(initiative_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scores not found for this initiative"
        )

    db.commit()

    return None


@router.post("/initiatives/{initiative_id}/recalculate-quality")
def recalculate_quality_score(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually recalculate the quality score for an initiative.

    This endpoint recalculates the quality score based on current Q&A coverage.
    Useful after:
    - Answering additional questions
    - Updating question priorities
    - Making significant changes to the initiative

    The quality score measures how thoroughly the initiative has been researched
    through Q&A, weighted by question priority (P0: 50%, P1: 30%, P2: 20%).

    Returns:
        Dict with updated quality_score and detailed breakdown
    """
    # Verify initiative access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Calculate quality score
    quality_score, quality_breakdown = calculate_quality_score(db, initiative_id)

    # Update initiative
    initiative.readiness_score = quality_score
    db.commit()

    return {
        "initiative_id": str(initiative_id),
        "quality_score": quality_score,
        "breakdown": quality_breakdown,
        "message": "Quality score recalculated successfully"
    }


# Gap Analysis request models
class AnswerGapQuestionRequest(BaseModel):
    question_id: UUID = Field(..., description="ID of the question to answer")
    answer_text: str = Field(..., description="Estimated answer provided by the user")
    estimation_confidence: str = Field(..., description="Confidence level: Low, Medium, or High")


@router.post("/initiatives/{initiative_id}/analyze-scoring-gaps")
def analyze_scoring_gaps(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze scoring gaps for an initiative and generate targeted questions (async with job).

    This endpoint:
    1. Creates a background job for gap analysis
    2. Returns immediately with job ID for polling
    3. Job runs gap analysis asynchronously

    Returns job ID for status polling.
    """
    from backend.models import Job, JobStatus

    # Verify initiative access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Get context
    context_repo = ContextRepository(db)
    context = context_repo.get_current(current_user.organization_id)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organizational context found. Please create context first."
        )

    # Create background job
    job_repo = JobRepository(db)
    job = Job(
        job_type=JobType.ANALYZE_SCORING_GAPS,
        initiative_id=initiative_id,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        status=JobStatus.PENDING,
        progress_percent=0,
        progress_message="Starting gap analysis..."
    )
    job_repo.create(job)
    db.commit()

    print(f"[GAP ANALYSIS] Created job {job.id} for gap analysis")

    # Execute job in background
    execute_job_in_background(job.id)

    return {
        "job_id": str(job.id),
        "status": "pending",
        "message": "Gap analysis started in background"
    }


@router.post("/initiatives/{initiative_id}/answer-gap-question")
def answer_gap_question(
    initiative_id: UUID,
    request: AnswerGapQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save an estimated answer to a gap-filling question.

    This endpoint:
    1. Validates the question belongs to the initiative
    2. Creates or updates an Answer with status=ESTIMATED
    3. Stores the estimation confidence level
    4. Returns success response

    The estimated answers will be used in score calculation with
    confidence penalties applied based on the number of estimates.
    """
    # Verify initiative access
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Validate confidence level
    valid_confidence = ["Low", "Medium", "High"]
    if request.estimation_confidence not in valid_confidence:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid confidence level. Must be one of: {', '.join(valid_confidence)}"
        )

    # Get the question and verify it belongs to this initiative
    question_repo = QuestionRepository(db)
    question = question_repo.get_by_id(request.question_id)

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    if question.initiative_id != initiative_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question does not belong to this initiative"
        )

    # Create or update answer
    from backend.repositories.answer import AnswerRepository
    from backend.models.answer import AnswerStatus

    answer_repo = AnswerRepository(db)
    existing_answer = answer_repo.get_by_question(request.question_id)

    if existing_answer:
        # Update existing answer
        existing_answer.answer_text = request.answer_text
        existing_answer.answer_status = AnswerStatus.ESTIMATED
        existing_answer.estimation_confidence = request.estimation_confidence
        existing_answer.answered_by = current_user.id
        answer = existing_answer
    else:
        # Create new answer
        from backend.models.answer import Answer
        answer = Answer(
            question_id=request.question_id,
            answer_text=request.answer_text,
            answer_status=AnswerStatus.ESTIMATED,
            estimation_confidence=request.estimation_confidence,
            answered_by=current_user.id
        )
        answer_repo.create(answer)

    db.commit()

    return {
        "success": True,
        "question_id": str(request.question_id),
        "answer_id": str(answer.id),
        "status": "ESTIMATED",
        "confidence": request.estimation_confidence,
        "message": "Estimated answer saved successfully"
    }


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Poll job status and progress.

    Returns:
        Job status with progress information
    """
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id, current_user.organization_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "progress_percent": job.progress_percent or 0,
        "progress_message": job.progress_message or "",
        "result_data": job.result_data if job.status.value == "completed" else None,
        "error_message": job.error_message if job.status.value == "failed" else None,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat()
    }
