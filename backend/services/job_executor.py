"""
Job executor service for running background tasks.
"""

import threading
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


def execute_job_in_background(job_id: UUID) -> None:
    """
    Execute a job in a background thread.

    Args:
        job_id: ID of the job to execute
    """
    thread = threading.Thread(target=_execute_job, args=(job_id,), daemon=True)
    thread.start()


def _execute_job(job_id: UUID) -> None:
    """
    Internal function to execute a job with proper error handling.

    Args:
        job_id: ID of the job to execute
    """
    db: Session = SessionLocal()

    try:
        job_repo = JobRepository(db)
        job = job_repo.get_by_id(job_id)

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
        else:
            raise ValueError(f"Unknown job type: {job.job_type}")

        # Mark as completed
        job_repo.mark_completed(job, result)
        db.commit()

        print(f"Job {job_id} completed successfully")

    except Exception as e:
        # Mark as failed with error details
        error_message = str(e)
        error_details = {
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

        try:
            job_repo = JobRepository(db)
            job = job_repo.get_by_id(job_id)
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

    db.commit()

    return {
        "mrd_id": str(mrd.id),
        "word_count": metadata["word_count"],
        "completeness_score": metadata["completeness_score"],
        "version": mrd.version,
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

    # Update initiative's readiness_score field for easy access in list views
    initiative.readiness_score = evaluation_data["readiness_score"]

    db.commit()

    return {
        "evaluation_id": str(evaluation_record.id),
        "readiness_score": evaluation_data["readiness_score"],
        "risk_level": evaluation_data["risk_level"],
        "initiative_id": str(job.initiative_id)
    }
