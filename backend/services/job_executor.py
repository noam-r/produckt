"""
Job executor service for running background tasks.
"""

import logging
import traceback
from typing import Callable, Any
from uuid import UUID
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Job, JobStatus, JobType
from backend.repositories.job import JobRepository
from backend.repositories.initiative import InitiativeRepository
from backend.repositories.context import ContextRepository
from backend.repositories.question import QuestionRepository
from backend.repositories.mrd import MRDRepository
from backend.agents.knowledge_gap import KnowledgeGapAgent
from backend.agents.mrd_generator import MRDGeneratorAgent
from backend.agents.readiness_evaluator import ReadinessEvaluatorAgent
from backend.services.question_throttle_service import QuestionThrottleService
from backend.agents.base import LLMError
from backend.services.quality_scorer import calculate_quality_score
from backend.services.job_executor_scoring import (
    execute_analyze_scoring_gaps,
    execute_calculate_scores
)
from backend.services.monthly_budget_reset_service import MonthlyBudgetResetService

logger = logging.getLogger(__name__)


def execute_job_in_background(job_id: UUID) -> None:
    """
    Queue a job for background execution.

    Note: This function no longer spawns threads directly. Instead, it relies
    on the background job worker to poll for pending jobs and execute them.
    The job should already be created with status PENDING before calling this.

    Args:
        job_id: ID of the job to execute
    """
    # Job will be picked up by the background worker
    # No action needed here - just ensure the job is in PENDING status
    logger.info(f"Job {job_id} queued for background execution by worker")


def _execute_job(job_id: UUID) -> None:
    """
    Internal function to execute a job with proper error handling.

    Args:
        job_id: ID of the job to execute
    """
    db: Session = SessionLocal()

    try:
        job_repo = JobRepository(db)
        job = job_repo._get_by_id_internal(job_id)

        if not job:
            print(f"Job {job_id} not found")
            return

        if job.status != JobStatus.PENDING:
            print(f"Job {job_id} is not pending (status: {job.status})")
            return

        # Mark as in progress
        job_repo.update_status(job, JobStatus.IN_PROGRESS, "Starting job...")
        db.commit()

        # Execute based on job type
        if job.job_type == JobType.GENERATE_QUESTIONS:
            result = _execute_generate_questions(db, job)
        elif job.job_type == JobType.GENERATE_MRD:
            result = _execute_generate_mrd(db, job)
        elif job.job_type == JobType.EVALUATE_READINESS:
            result = _execute_evaluate_readiness(db, job)
        elif job.job_type == JobType.ANALYZE_SCORING_GAPS:
            result = execute_analyze_scoring_gaps(db, job)
        elif job.job_type == JobType.CALCULATE_SCORES:
            result = execute_calculate_scores(db, job)
        elif job.job_type == JobType.MONTHLY_BUDGET_RESET:
            result = _execute_monthly_budget_reset(db, job)
        else:
            raise ValueError(f"Unknown job type: {job.job_type}")

        # Mark as completed
        job_repo.mark_completed(job, result)
        db.commit()

        print(f"Job {job_id} completed successfully")

    except LLMError as e:
        # LLM-specific errors with user-friendly messages
        error_message = e.message
        error_details = {
            "error_type": "LLMError",
            "user_message": e.message,
            "technical_details": e.technical_details,
            "traceback": traceback.format_exc()
        }

        try:
            job_repo = JobRepository(db)
            job = job_repo._get_by_id_internal(job_id)
            if job:
                job_repo.mark_failed(job, error_message, error_details)
                db.commit()
        except Exception as commit_error:
            print(f"Failed to mark job as failed: {commit_error}")

        print(f"Job {job_id} failed with LLM error: {error_message}")
        if e.technical_details:
            print(f"Technical details: {e.technical_details}")

    except Exception as e:
        # Generic errors
        error_message = str(e)
        error_details = {
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

        try:
            job_repo = JobRepository(db)
            job = job_repo._get_by_id_internal(job_id)
            if job:
                job_repo.mark_failed(job, error_message, error_details)
                db.commit()
        except Exception as commit_error:
            print(f"Failed to mark job as failed: {commit_error}")

        print(f"Job {job_id} failed: {error_message}")
        print(traceback.format_exc())

    finally:
        db.close()


def _execute_generate_questions(db: Session, job: Job) -> dict:
    """
    Execute question generation job.

    Args:
        db: Database session
        job: Job instance

    Returns:
        Result data with generated questions
    """
    if not job.initiative_id:
        raise ValueError("Initiative ID is required for question generation")

    # Get initiative and context
    initiative_repo = InitiativeRepository(db)
    context_repo = ContextRepository(db)
    question_repo = QuestionRepository(db)

    initiative = initiative_repo.get_by_id(job.initiative_id, job.organization_id)
    if not initiative:
        raise ValueError(f"Initiative {job.initiative_id} not found")

    context = context_repo.get_current(job.organization_id)
    if not context:
        raise ValueError("No active context found for organization")

    # Update progress
    job_repo = JobRepository(db)
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Analyzing knowledge gaps...", 30)
    db.commit()

    # Generate questions
    agent = KnowledgeGapAgent(db)
    questions = agent.generate_questions(initiative, context, job.created_by)

    # Validate question count doesn't exceed limits
    throttle_service = QuestionThrottleService(db)
    result = throttle_service.check_question_limits(initiative.id, len(questions))
    
    if not result.can_add:
        # Truncate questions to fit within limits
        max_allowed = result.max_questions - result.total_count
        if max_allowed > 0:
            print(f"Warning: Generated {len(questions)} questions, truncating to {max_allowed} to fit within limits")
            questions = questions[:max_allowed]
        else:
            raise ValueError(f"Cannot add questions: initiative at maximum limit ({result.total_count}/{result.max_questions})")

    # Update progress
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Saving questions...", 80)
    db.commit()

    # Save questions
    for question in questions:
        question_repo.create(question)

    # Increment iteration count
    initiative.iteration_count += 1

    db.commit()

    return {
        "questions_count": len(questions),
        "iteration": initiative.iteration_count,
        "initiative_id": str(job.initiative_id)
    }


def _execute_generate_mrd(db: Session, job: Job) -> dict:
    """
    Execute MRD generation job.

    Args:
        db: Database session
        job: Job instance

    Returns:
        Result data with MRD info
    """
    import logging
    logger = logging.getLogger(__name__)

    if not job.initiative_id:
        raise ValueError("Initiative ID is required for MRD generation")

    # Get initiative and context
    initiative_repo = InitiativeRepository(db)
    context_repo = ContextRepository(db)
    mrd_repo = MRDRepository(db)

    initiative = initiative_repo.get_by_id(job.initiative_id, job.organization_id)
    if not initiative:
        raise ValueError(f"Initiative {job.initiative_id} not found")

    context = context_repo.get_current(job.organization_id)
    if not context:
        raise ValueError("No active context found for organization")

    # Update progress
    job_repo = JobRepository(db)
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Preparing MRD generation...", 10)
    db.commit()

    logger.info(f"Job {job.id}: Starting multi-section MRD generation for initiative {job.initiative_id}")

    # Define progress callback for section-by-section updates
    def update_progress(message: str, percent: int):
        """Update job progress during section generation."""
        job_repo.update_status(job, JobStatus.IN_PROGRESS, message, percent)
        db.commit()
        logger.info(f"Job {job.id}: {message} ({percent}%)")

    # Generate MRD section-by-section - THIS IS THE LONG-RUNNING OPERATION
    try:
        agent = MRDGeneratorAgent(db)
        sections, mrd_content, metadata, assumptions = agent.generate_mrd_by_sections(
            initiative,
            context,
            job.created_by,
            progress_callback=update_progress
        )
        logger.info(f"Job {job.id}: Multi-section MRD generation completed successfully")
    except Exception as e:
        logger.error(f"Job {job.id}: MRD generation failed: {str(e)}")
        raise

    # Update progress for saving
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Saving MRD...", 98)
    db.commit()

    # Check if MRD already exists
    existing_mrd = mrd_repo.get_by_initiative(job.initiative_id)

    if existing_mrd:
        # Update existing MRD
        existing_mrd.content = mrd_content
        existing_mrd.sections = sections  # Store sections separately
        existing_mrd.version += 1
        existing_mrd.word_count = metadata["word_count"]
        existing_mrd.completeness_score = metadata["completeness_score"]
        existing_mrd.readiness_at_generation = metadata["readiness_score"]
        existing_mrd.assumptions_made = assumptions
        mrd = existing_mrd
    else:
        # Create new MRD
        from backend.models import MRD
        mrd = MRD(
            initiative_id=job.initiative_id,
            content=mrd_content,
            sections=sections,  # Store sections separately
            word_count=metadata["word_count"],
            completeness_score=metadata["completeness_score"],
            readiness_at_generation=metadata["readiness_score"],
            assumptions_made=assumptions,
            generated_by=job.created_by
        )
        mrd_repo.create(mrd)

    # Recalculate quality score after MRD generation
    # This ensures the quality score reflects the most recent work
    initiative_repo = InitiativeRepository(db)
    initiative = initiative_repo.get_by_id(job.initiative_id, job.organization_id)
    if initiative:
        quality_score, quality_breakdown = calculate_quality_score(db, job.initiative_id)
        initiative.readiness_score = quality_score

        # Update initiative status to MRD_Generated
        from backend.models.initiative import InitiativeStatus
        initiative.status = InitiativeStatus.MRD_GENERATED

    db.commit()

    return {
        "mrd_id": str(mrd.id),
        "word_count": metadata["word_count"],
        "completeness_score": metadata["completeness_score"],
        "version": mrd.version,
        "quality_score": quality_score if initiative else None,
        "initiative_id": str(job.initiative_id)
    }


def _execute_evaluate_readiness(db: Session, job: Job) -> dict:
    """
    Execute readiness evaluation job.

    Args:
        db: Database session
        job: Job instance

    Returns:
        Result data with evaluation
    """
    if not job.initiative_id:
        raise ValueError("Initiative ID is required for evaluation")

    # Get initiative and context
    initiative_repo = InitiativeRepository(db)
    context_repo = ContextRepository(db)

    initiative = initiative_repo.get_by_id(job.initiative_id, job.organization_id)
    if not initiative:
        raise ValueError(f"Initiative {job.initiative_id} not found")

    context = context_repo.get_current(job.organization_id)
    if not context:
        raise ValueError("No active context found for organization")

    # Update progress
    job_repo = JobRepository(db)
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Analyzing readiness...", "50")
    db.commit()

    # Evaluate readiness
    agent = ReadinessEvaluatorAgent(db)
    evaluation_data = agent.evaluate_readiness(initiative, context, job.created_by)

    # Save evaluation
    from backend.repositories.evaluation import EvaluationRepository
    eval_repo = EvaluationRepository(db)

    evaluation_record = eval_repo.create_or_update(
        initiative_id=job.initiative_id,
        evaluation_data=evaluation_data,
        readiness_score=evaluation_data["readiness_score"],
        risk_level=evaluation_data["risk_level"],
        iteration_at_evaluation=initiative.iteration_count,
        evaluated_by=job.created_by
    )

    # Recalculate quality score based on Q&A coverage
    # This provides a dynamic, up-to-date quality assessment
    quality_score, quality_breakdown = calculate_quality_score(db, job.initiative_id)
    initiative.readiness_score = quality_score

    db.commit()

    return {
        "evaluation_id": str(evaluation_record.id),
        "evaluation_readiness": evaluation_data["readiness_score"],  # Original evaluation score
        "quality_score": quality_score,  # Dynamic Q&A coverage score
        "quality_breakdown": quality_breakdown,
        "risk_level": evaluation_data["risk_level"],
        "initiative_id": str(job.initiative_id)
    }

def _execute_monthly_budget_reset(db: Session, job: Job) -> dict:
    """
    Execute monthly budget reset job.

    Args:
        db: Database session
        job: Job instance

    Returns:
        Result data with reset statistics
    """
    from datetime import datetime
    
    # Update progress
    job_repo = JobRepository(db)
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Starting monthly budget reset...", 10)
    db.commit()

    # Get current date for reset
    now = datetime.utcnow()
    target_year = now.year
    target_month = now.month

    # Initialize reset service
    reset_service = MonthlyBudgetResetService(db)

    # Update progress
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Checking if reset is needed...", 20)
    db.commit()

    # Check if reset should run
    should_run = reset_service.should_run_reset(target_year, target_month)
    
    if not should_run:
        # Reset already processed for this month
        result = {
            "already_processed": True,
            "target_year": target_year,
            "target_month": target_month,
            "message": f"Budget reset already processed for {target_year}-{target_month:02d}"
        }
        logger.info(f"Monthly budget reset skipped - already processed for {target_year}-{target_month:02d}")
        return result

    # Update progress
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Getting previous month summary...", 30)
    db.commit()

    # Get previous month summary for reporting
    prev_month_summary = reset_service.get_previous_month_spending_summary(target_year, target_month)

    # Update progress
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Resetting monthly spending counters...", 50)
    db.commit()

    # Perform the reset
    reset_stats = reset_service.reset_monthly_budgets(target_year, target_month)

    # Update progress
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Cleaning up old records...", 80)
    db.commit()

    # Clean up old records (keep 24 months of history)
    cleanup_count = reset_service.cleanup_old_spending_records(months_to_keep=24)

    # Final result
    result = {
        "reset_completed": True,
        "target_year": target_year,
        "target_month": target_month,
        "reset_statistics": reset_stats,
        "previous_month_summary": prev_month_summary,
        "cleanup_count": cleanup_count,
        "message": f"Successfully reset budgets for {target_year}-{target_month:02d}"
    }

    logger.info(f"Monthly budget reset completed successfully: {result}")
    return result