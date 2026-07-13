from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from recruiter_workflow.database import get_db
from recruiter_workflow.models import Candidate, JobDescription, Resume
from recruiter_workflow.schemas import InterviewQuestionResponse
from recruiter_workflow.services.llm_service import generate_interview_questions

router = APIRouter(prefix="/api/interview", tags=["Interview Questions"])


@router.post("/questions/{candidate_id}", response_model=InterviewQuestionResponse)
def get_interview_questions(candidate_id: int, db: Session = Depends(get_db)):
    """Generate interview questions based on a candidate's resume and linked JD."""
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

    questions = generate_interview_questions(
        resume_text=candidate.resume.raw_text,
        jd_text=jd_text,
        count=5,
    )

    return InterviewQuestionResponse(questions=questions)
