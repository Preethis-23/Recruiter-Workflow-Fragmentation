from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from recruiter_workflow.database import get_db
from recruiter_workflow.models import Meeting, Candidate
from recruiter_workflow.schemas import (
    MeetingCreate,
    MeetingUpdate,
    MeetingResponse,
)

router = APIRouter(prefix="/api/meetings", tags=["Meetings"])


@router.get("/candidate/{candidate_id}", response_model=list[MeetingResponse])
def list_meetings_for_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Get all scheduled meetings for a candidate."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return (
        db.query(Meeting)
        .filter(Meeting.candidate_id == candidate_id)
        .order_by(Meeting.scheduled_at.asc())
        .all()
    )


@router.post("/candidate/{candidate_id}", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
def create_meeting(candidate_id: int, payload: MeetingCreate, db: Session = Depends(get_db)):
    """Schedule a new meeting for a candidate."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    meeting = Meeting(
        candidate_id=candidate_id,
        title=payload.title,
        meeting_link=payload.meeting_link,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        attendees=payload.attendees,
        notes=payload.notes,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.put("/{meeting_id}", response_model=MeetingResponse)
def update_meeting(meeting_id: int, payload: MeetingUpdate, db: Session = Depends(get_db)):
    """Update a scheduled meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(meeting, key, value)

    db.commit()
    db.refresh(meeting)
    return meeting


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """Delete a scheduled meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    db.delete(meeting)
    db.commit()
