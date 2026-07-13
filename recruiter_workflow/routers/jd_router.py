from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from recruiter_workflow.database import get_db
from recruiter_workflow.models import JobDescription
from recruiter_workflow.schemas import (
    JobDescriptionCreate,
    JobDescriptionUpdate,
    JobDescriptionResponse,
)

router = APIRouter(prefix="/api/jds", tags=["Job Descriptions"])


@router.get("/", response_model=list[JobDescriptionResponse])
def list_jds(db: Session = Depends(get_db)):
    """Return all job descriptions."""
    return db.query(JobDescription).order_by(JobDescription.created_at.desc()).all()


@router.get("/{jd_id}", response_model=JobDescriptionResponse)
def get_jd(jd_id: int, db: Session = Depends(get_db)):
    """Return a single job description by ID."""
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    return jd


@router.post("/", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_jd(payload: JobDescriptionCreate, db: Session = Depends(get_db)):
    """Create a new job description."""
    existing = db.query(JobDescription).filter(JobDescription.title == payload.title).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"A Job Description with the title '{payload.title}' already exists.")
        
    jd = JobDescription(**payload.model_dump())
    db.add(jd)
    db.commit()
    db.refresh(jd)
    return jd


@router.put("/{jd_id}", response_model=JobDescriptionResponse)
def update_jd(jd_id: int, payload: JobDescriptionUpdate, db: Session = Depends(get_db)):
    """Update an existing job description."""
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    if payload.title and payload.title != jd.title:
        existing = db.query(JobDescription).filter(JobDescription.title == payload.title).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"A Job Description with the title '{payload.title}' already exists.")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(jd, key, value)

    db.commit()
    db.refresh(jd)
    return jd


@router.delete("/{jd_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_jd(jd_id: int, db: Session = Depends(get_db)):
    """Delete a job description."""
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    db.delete(jd)
    db.commit()
