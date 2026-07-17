from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from recruiter_workflow.database import get_db
from recruiter_workflow.models import Candidate, JobDescription, Resume
from recruiter_workflow.schemas import (
    CandidateResponse,
    CandidateStatusUpdate,
    CandidateNotesUpdate,
)
from recruiter_workflow.services.ranking_service import rank_resumes_for_jd, get_ranked_candidates
from recruiter_workflow.services.llm_service import generate_summary

router = APIRouter(prefix="/api/candidates", tags=["Candidates"])


@router.get("/", response_model=list[CandidateResponse])
def list_candidates(
    jd_id: int | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    """List candidates, optionally filtered by jd_id and/or status."""
    query = db.query(Candidate).options(joinedload(Candidate.resume))
    if jd_id is not None:
        query = query.filter(Candidate.jd_id == jd_id)
    if status_filter:
        query = query.filter(Candidate.status == status_filter)
    return query.order_by(Candidate.similarity_score.desc().nulls_last(), Candidate.created_at.desc()).all()


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Return a single candidate by ID."""
    candidate = (
        db.query(Candidate)
        .options(joinedload(Candidate.resume))
        .filter(Candidate.id == candidate_id)
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.put("/{candidate_id}/status", response_model=CandidateResponse)
def update_candidate_status(
    candidate_id: int,
    payload: CandidateStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update a candidate's status (e.g., Screening, Interview, Offer, Hired, Rejected)."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate.status = payload.status
    db.commit()
    db.refresh(candidate)
    return candidate


@router.put("/{candidate_id}/notes", response_model=CandidateResponse)
def update_candidate_notes(
    candidate_id: int,
    payload: CandidateNotesUpdate,
    db: Session = Depends(get_db),
):
    """Update a candidate's performance notes."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate.notes = payload.notes
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/rank/{jd_id}")
def rank_candidates(jd_id: int, db: Session = Depends(get_db)):
    """Compute similarity scores between a JD and all resumes, creating/updating Candidate records."""
    try:
        results = rank_resumes_for_jd(db, jd_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"message": f"Ranked {len(results)} candidates", "results": results}


@router.get("/rank/{jd_id}")
def get_ranking(jd_id: int, db: Session = Depends(get_db)):
    """Get ranked candidates for a job description (sorted by similarity, descending)."""
    return get_ranked_candidates(db, jd_id)


@router.post("/{candidate_id}/summary", response_model=dict)
def generate_candidate_summary(candidate_id: int, db: Session = Depends(get_db)):
    """Generate an AI-powered summary comparing the candidate's resume to the JD."""
    candidate = (
        db.query(Candidate)
        .options(joinedload(Candidate.resume), joinedload(Candidate.job_description))
        .filter(Candidate.id == candidate_id)
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not candidate.resume or not candidate.resume.raw_text:
        raise HTTPException(status_code=400, detail="Resume raw text not available")
    if not candidate.job_description:
        raise HTTPException(status_code=400, detail="Job description not available")

    jd_text = (
        f"{candidate.job_description.title}\n"
        f"{candidate.job_description.description}\n"
        f"{candidate.job_description.required_skills or ''}"
    )
    summary = generate_summary(candidate.resume.raw_text, jd_text)

    candidate.summary = summary
    db.commit()

    return {"candidate_id": candidate_id, "summary": summary}
