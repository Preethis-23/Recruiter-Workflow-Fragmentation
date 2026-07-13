from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from recruiter_workflow.database import get_db
from recruiter_workflow.models import RecruitmentStage, Candidate
from recruiter_workflow.schemas import (
    RecruitmentStageCreate,
    RecruitmentStageUpdate,
    RecruitmentStageResponse,
)

router = APIRouter(prefix="/api/stages", tags=["Recruitment Stages"])


@router.get("/candidate/{candidate_id}", response_model=list[RecruitmentStageResponse])
def list_stages_for_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Get all recruitment stages for a candidate, ordered by creation date."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return (
        db.query(RecruitmentStage)
        .filter(RecruitmentStage.candidate_id == candidate_id)
        .order_by(RecruitmentStage.created_at.asc())
        .all()
    )


@router.get("/{stage_id}", response_model=RecruitmentStageResponse)
def get_stage(stage_id: int, db: Session = Depends(get_db)):
    """Get a single recruitment stage by ID."""
    stage = db.query(RecruitmentStage).filter(RecruitmentStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    return stage


@router.post("/candidate/{candidate_id}", response_model=RecruitmentStageResponse, status_code=status.HTTP_201_CREATED)
def create_stage(candidate_id: int, payload: RecruitmentStageCreate, db: Session = Depends(get_db)):
    """Create a new recruitment stage for a candidate."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if payload.stage not in RecruitmentStage.STAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage type. Must be one of: {', '.join(RecruitmentStage.STAGE_TYPES)}",
        )

    stage = RecruitmentStage(
        candidate_id=candidate_id,
        stage=payload.stage,
        scheduled_date=payload.scheduled_date,
        notes=payload.notes,
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


@router.put("/{stage_id}", response_model=RecruitmentStageResponse)
def update_stage(stage_id: int, payload: RecruitmentStageUpdate, db: Session = Depends(get_db)):
    """Update a recruitment stage (status, notes, feedback, scheduled date)."""
    stage = db.query(RecruitmentStage).filter(RecruitmentStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(stage, key, value)

    db.commit()
    db.refresh(stage)
    return stage


@router.delete("/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stage(stage_id: int, db: Session = Depends(get_db)):
    """Delete a recruitment stage."""
    stage = db.query(RecruitmentStage).filter(RecruitmentStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    db.delete(stage)
    db.commit()
