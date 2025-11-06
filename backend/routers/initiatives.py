"""
Initiative API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from backend.database import get_db
from backend.models import Initiative, InitiativeStatus, User
from backend.repositories.initiative import InitiativeRepository
from backend.schemas.initiative import (
    InitiativeCreate, InitiativeUpdate, InitiativeResponse,
    InitiativeListResponse, InitiativeStatusUpdate
)
from backend.auth.dependencies import get_current_user, require_product_manager


router = APIRouter(prefix="/initiatives", tags=["Initiatives"])


@router.post("", response_model=InitiativeResponse, status_code=status.HTTP_201_CREATED)
def create_initiative(
    data: InitiativeCreate,
    current_user: User = Depends(require_product_manager),
    db: Session = Depends(get_db)
):
    """
    Create a new initiative.

    Requires Product Manager or Admin role.
    """
    repo = InitiativeRepository(db)

    # Create initiative
    initiative = Initiative(
        title=data.title,
        description=data.description,
        status=InitiativeStatus.DRAFT,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        iteration_count=0
    )

    created = repo.create(initiative)
    db.commit()

    return created


@router.get("", response_model=InitiativeListResponse)
def list_initiatives(
    status_filter: Optional[InitiativeStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List initiatives for the current user's organization.

    Optionally filter by status.
    """
    repo = InitiativeRepository(db)

    if status_filter:
        initiatives = repo.get_by_status(
            status_filter,
            current_user.organization_id,
            limit=limit,
            offset=offset
        )
    else:
        initiatives = repo.get_all(
            organization_id=current_user.organization_id,
            limit=limit,
            offset=offset
        )

    total = repo.count(organization_id=current_user.organization_id)

    return InitiativeListResponse(
        initiatives=initiatives,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{initiative_id}", response_model=InitiativeResponse)
def get_initiative(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific initiative by ID."""
    repo = InitiativeRepository(db)

    initiative = repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    return initiative


@router.patch("/{initiative_id}", response_model=InitiativeResponse)
def update_initiative(
    initiative_id: UUID,
    data: InitiativeUpdate,
    current_user: User = Depends(require_product_manager),
    db: Session = Depends(get_db)
):
    """
    Update an initiative.

    Requires Product Manager or Admin role.
    """
    repo = InitiativeRepository(db)

    initiative = repo.get_by_id(initiative_id, current_user.organization_id)

    if not initiative:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    # Update fields
    if data.title is not None:
        initiative.title = data.title
    if data.description is not None:
        initiative.description = data.description
    if data.status is not None:
        initiative.status = data.status

    updated = repo.update(initiative)
    db.commit()

    return updated


@router.put("/{initiative_id}/status", response_model=InitiativeResponse)
def update_initiative_status(
    initiative_id: UUID,
    data: InitiativeStatusUpdate,
    current_user: User = Depends(require_product_manager),
    db: Session = Depends(get_db)
):
    """
    Update initiative status.

    Requires Product Manager or Admin role.
    """
    repo = InitiativeRepository(db)

    updated = repo.update_status(
        initiative_id,
        data.status,
        current_user.organization_id
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    db.commit()

    return updated


@router.delete("/{initiative_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_initiative(
    initiative_id: UUID,
    current_user: User = Depends(require_product_manager),
    db: Session = Depends(get_db)
):
    """
    Delete an initiative.

    Requires Product Manager or Admin role.
    """
    repo = InitiativeRepository(db)

    deleted = repo.delete(initiative_id, current_user.organization_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Initiative not found"
        )

    db.commit()

    return None


@router.get("/search/{search_term}", response_model=list[InitiativeResponse])
def search_initiatives(
    search_term: str,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search initiatives by title or description."""
    repo = InitiativeRepository(db)

    initiatives = repo.search_by_title(
        search_term,
        current_user.organization_id,
        limit=limit
    )

    return initiatives
