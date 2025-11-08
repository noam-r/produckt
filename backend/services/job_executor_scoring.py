"""
Job executor handlers for scoring-related jobs.
"""

from sqlalchemy.orm import Session
from backend.models import Job, JobStatus
from backend.repositories.job import JobRepository
from backend.repositories.initiative import InitiativeRepository
from backend.repositories.context import ContextRepository
from backend.agents.scoring_gap_analyzer import ScoringGapAnalyzer
from backend.agents.scoring import ScoringAgent


def execute_analyze_scoring_gaps(db: Session, job: Job) -> dict:
    """
    Execute gap analysis job.

    Args:
        db: Database session
        job: Job instance

    Returns:
        Gap analysis results
    """
    job_repo = JobRepository(db)
    initiative_repo = InitiativeRepository(db)
    context_repo = ContextRepository(db)

    # Get initiative and context
    initiative = initiative_repo.get_by_id(job.initiative_id, job.organization_id)
    if not initiative:
        raise ValueError(f"Initiative {job.initiative_id} not found")

    context = context_repo.get_current(job.organization_id)
    if not context:
        raise ValueError("No active context found for organization")

    # Update progress - starting analysis
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Preparing gap analysis...", 10)
    db.commit()

    # Run gap analysis (this is the long-running LLM call)
    analyzer = ScoringGapAnalyzer(db)

    # Update progress before LLM call
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Analyzing scoring gaps with AI...", 30)
    db.commit()

    gap_analysis = analyzer.analyze_gaps(
        initiative=initiative,
        context=context,
        user_id=job.created_by
    )

    # Debug logging
    print(f"Gap analysis completed. Result type: {type(gap_analysis)}, has gap_analysis: {'gap_analysis' in (gap_analysis or {})}")
    if gap_analysis:
        print(f"Gap analysis keys: {gap_analysis.keys() if isinstance(gap_analysis, dict) else 'not a dict'}")

    # Update progress after analysis
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Processing gap analysis results...", 70)
    db.commit()

    # Commit gap questions to database
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Saving gap questions...", 85)
    db.commit()

    result = {
        "initiative_id": str(job.initiative_id),
        "can_calculate": gap_analysis.get("can_calculate", False) if gap_analysis else False,
        "gap_count": len(gap_analysis.get("blocking_gaps", [])) if gap_analysis else 0,
        "gap_analysis": gap_analysis
    }

    print(f"Returning result: {result.keys()}, gap_analysis is None: {result['gap_analysis'] is None}")

    return result


def execute_calculate_scores(db: Session, job: Job) -> dict:
    """
    Execute score calculation job.

    Args:
        db: Database session
        job: Job instance

    Returns:
        Calculated scores
    """
    job_repo = JobRepository(db)
    initiative_repo = InitiativeRepository(db)
    context_repo = ContextRepository(db)

    # Get initiative and context
    initiative = initiative_repo.get_by_id(job.initiative_id, job.organization_id)
    if not initiative:
        raise ValueError(f"Initiative {job.initiative_id} not found")

    context = context_repo.get_current(job.organization_id)
    if not context:
        raise ValueError("No active context found for organization")

    # Update progress
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Analyzing initiative data...", 20)
    db.commit()

    # Calculate scores (this is the long-running LLM call)
    scoring_agent = ScoringAgent(db)

    # Update progress before LLM call
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Calculating RICE and FDV scores...", 40)
    db.commit()

    rice_data, fdv_data, data_quality, warnings = scoring_agent.calculate_scores(
        initiative=initiative,
        context=context,
        user_id=job.created_by
    )

    # Update progress after LLM call
    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Saving scores to database...", 80)
    db.commit()

    # Save scores to database
    from backend.repositories.score import ScoreRepository
    from backend.models.score import Score

    score_repo = ScoreRepository(db)
    existing_score = score_repo.get_by_initiative(job.initiative_id)

    if existing_score:
        # Update existing score
        existing_score.reach = rice_data.get("reach")
        existing_score.impact = rice_data.get("impact")
        existing_score.confidence = rice_data.get("confidence")
        existing_score.effort = rice_data.get("effort")
        existing_score.rice_score = rice_data.get("rice_score")
        existing_score.feasibility = fdv_data.get("feasibility")
        existing_score.desirability = fdv_data.get("desirability")
        existing_score.viability = fdv_data.get("viability")
        existing_score.fdv_score = fdv_data.get("fdv_score")
        existing_score.rice_reasoning = rice_data.get("reasoning", "")
        existing_score.fdv_reasoning = fdv_data.get("reasoning", "")
        existing_score.data_quality = data_quality
        existing_score.warnings = warnings
        existing_score.scored_by = job.created_by
        score = existing_score
    else:
        # Create new score
        score = Score(
            initiative_id=job.initiative_id,
            reach=rice_data.get("reach"),
            impact=rice_data.get("impact"),
            confidence=rice_data.get("confidence"),
            effort=rice_data.get("effort"),
            rice_score=rice_data.get("rice_score"),
            feasibility=fdv_data.get("feasibility"),
            desirability=fdv_data.get("desirability"),
            viability=fdv_data.get("viability"),
            fdv_score=fdv_data.get("fdv_score"),
            rice_reasoning=rice_data.get("reasoning", ""),
            fdv_reasoning=fdv_data.get("reasoning", ""),
            data_quality=data_quality,
            warnings=warnings,
            scored_by=job.created_by
        )
        score_repo.create(score)

    job_repo.update_status(job, JobStatus.IN_PROGRESS, "Finalizing...", 90)
    db.commit()

    return {
        "initiative_id": str(job.initiative_id),
        "score_id": str(score.id),
        "rice_score": rice_data.get("rice_score"),
        "fdv_score": fdv_data.get("fdv_score"),
        "data_quality": data_quality,
        "warnings": warnings
    }
