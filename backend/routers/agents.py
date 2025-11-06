"""
AI Agent API endpoints for question generation and MRD creation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

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


router = APIRouter(prefix="/agents", tags=["AI Agents"])


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
        # Get initiative
        initiative_repo = InitiativeRepository(db)
        initiative = initiative_repo.get_by_id(initiative_id)

        if not initiative:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Initiative not found"
            )

        # Check access
        if initiative.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this initiative"
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


@router.post("/initiatives/{initiative_id}/calculate-scores", response_model=ScoreResponse)
def calculate_scores(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate RICE and FDV scores for an initiative.

    This endpoint:
    1. Analyzes the initiative, Q&A, and MRD
    2. Uses Claude to calculate RICE and FDV scores
    3. Saves scores to the database (creates or updates)

    Requirements:
    - Initiative must have an MRD generated
    - Organizational context must exist

    Returns the complete score data with reasoning.
    """
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

    # Calculate scores using agent
    try:
        agent = ScoringAgent(db)
        print(f"[SCORING] Starting score calculation for initiative {initiative_id}")
        rice_data, fdv_data, data_quality, warnings = agent.calculate_scores(
            initiative=initiative,
            context=context,
            user_id=current_user.id
        )
        print(f"[SCORING] Score calculation completed successfully")
        print(f"[SCORING] RICE data keys: {list(rice_data.keys())}")
        print(f"[SCORING] FDV data keys: {list(fdv_data.keys())}")
    except ValueError as e:
        print(f"[SCORING ERROR] ValueError: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"[SCORING ERROR] Unexpected exception: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during score calculation: {str(e)}"
        )

    # Validate calculations (only if values are present - None indicates insufficient data)
    print(f"[SCORING] Validating RICE score...")
    # Skip validation if critical values are None (LLM indicated insufficient data)
    if rice_data.get("reach") is not None and rice_data.get("rice_score") is not None:
        rice_valid = agent.validate_rice_score(rice_data)
        print(f"[SCORING] RICE validation result: {rice_valid}")
        if not rice_valid:
            print(f"[SCORING ERROR] RICE validation failed! Data: {rice_data}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="RICE score calculation validation failed"
            )
    else:
        print(f"[SCORING] Skipping RICE validation - some values are None (insufficient data)")

    print(f"[SCORING] Validating FDV score...")
    # Skip validation if critical values are None (LLM indicated insufficient data)
    if (fdv_data.get("feasibility") is not None and
        fdv_data.get("desirability") is not None and
        fdv_data.get("viability") is not None and
        fdv_data.get("fdv_score") is not None):
        fdv_valid = agent.validate_fdv_score(fdv_data)
        print(f"[SCORING] FDV validation result: {fdv_valid}")
        if not fdv_valid:
            print(f"[SCORING ERROR] FDV validation failed! Data: {fdv_data}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="FDV score calculation validation failed"
            )
    else:
        print(f"[SCORING] Skipping FDV validation - some values are None (insufficient data)")

    # Save scores to database
    print(f"[SCORING] Saving scores to database...")
    try:
        score_repo = ScoreRepository(db)
        score = score_repo.create_or_update(
            initiative_id=initiative_id,
            reach=rice_data["reach"],
            impact=rice_data["impact"],
            confidence=rice_data["confidence"],
            effort=rice_data["effort"],
            rice_score=rice_data["rice_score"],
            rice_reasoning=rice_data["reasoning"],
            feasibility=fdv_data["feasibility"],
            desirability=fdv_data["desirability"],
            viability=fdv_data["viability"],
            fdv_score=fdv_data["fdv_score"],
            fdv_reasoning=fdv_data["reasoning"],
            scored_by=current_user.id,
            data_quality=data_quality,
            warnings=warnings
        )
        print(f"[SCORING] Score saved successfully, committing...")
        db.commit()
        print(f"[SCORING] Database commit successful")
        return score
    except Exception as e:
        print(f"[SCORING ERROR] Database error: {e}")
        import traceback
        traceback.print_exc()
        raise


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
