"""
Context API endpoints for organizational context versioning.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from backend.database import get_db
from backend.models import User
from backend.repositories.context import ContextRepository
from backend.schemas.context import ContextCreate, ContextResponse, ContextListResponse
from backend.auth.dependencies import get_current_user, require_product_manager


router = APIRouter(prefix="/context", tags=["Context"])


@router.get("/current", response_model=ContextResponse)
def get_current_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current (active) context for the organization.
    """
    repo = ContextRepository(db)

    context = repo.get_current(current_user.organization_id)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No context found for organization"
        )

    return context


@router.post("", response_model=ContextResponse, status_code=status.HTTP_201_CREATED)
def create_context_version(
    data: ContextCreate,
    current_user: User = Depends(require_product_manager),
    db: Session = Depends(get_db)
):
    """
    Create a new version of context.

    Automatically increments version number and marks as current.
    Requires Product Manager or Admin role.
    """
    repo = ContextRepository(db)

    context = repo.create_new_version(
        organization_id=current_user.organization_id,
        company_mission=data.company_mission,
        strategic_objectives=data.strategic_objectives,
        target_markets=data.target_markets,
        competitive_landscape=data.competitive_landscape,
        technical_constraints=data.technical_constraints,
        created_by=current_user.id
    )

    db.commit()

    return context


@router.get("/versions", response_model=ContextListResponse)
def list_context_versions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all context versions for the organization.

    Returns versions ordered by version number (newest first).
    """
    repo = ContextRepository(db)

    contexts = repo.get_all_versions(current_user.organization_id)

    return ContextListResponse(
        contexts=contexts,
        total=len(contexts)
    )


@router.get("/versions/{version}", response_model=ContextResponse)
def get_context_version(
    version: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific version of context."""
    repo = ContextRepository(db)

    context = repo.get_by_version(current_user.organization_id, version)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Context version {version} not found"
        )

    return context


@router.put("/{context_id}/make-current", response_model=ContextResponse)
def set_context_as_current(
    context_id: UUID,
    current_user: User = Depends(require_product_manager),
    db: Session = Depends(get_db)
):
    """
    Set a specific context version as current.

    Requires Product Manager or Admin role.
    """
    repo = ContextRepository(db)

    context = repo.set_current(context_id, current_user.organization_id)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Context not found"
        )

    db.commit()

    return context


@router.delete("/{context_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_context_version(
    context_id: UUID,
    current_user: User = Depends(require_product_manager),
    db: Session = Depends(get_db)
):
    """
    Delete a context version.

    Cannot delete the current version - must set another version as current first.
    Requires Product Manager or Admin role.
    """
    repo = ContextRepository(db)

    deleted = repo.delete_version(context_id, current_user.organization_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete current context version or context not found"
        )

    db.commit()

    return None
