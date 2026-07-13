from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from recruiter_workflow.database import get_db
from recruiter_workflow.models import Candidate, JobDescription, RecruitmentStage
from recruiter_workflow.schemas import EmailRequest, EmailResponse
from recruiter_workflow.services.email_service import generate_email

router = APIRouter(prefix="/api/email", tags=["Email Generation"])


@router.post("/generate", response_model=EmailResponse)
def generate_candidate_email(payload: EmailRequest, db: Session = Depends(get_db)):
    """Generate a templated email for a candidate (interview, offer, rejection, follow-up)."""
    candidate = (
        db.query(Candidate)
        .options(
            joinedload(Candidate.job_description),
            joinedload(Candidate.resume),
        )
        .filter(Candidate.id == payload.candidate_id)
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate_name = candidate.resume.candidate_name if candidate.resume else "Candidate"
    position = candidate.job_description.title if candidate.job_description else "Open Position"

    # Fetch the latest stage for scheduling info
    latest_stage = (
        db.query(RecruitmentStage)
        .filter(RecruitmentStage.candidate_id == candidate.id)
        .order_by(RecruitmentStage.created_at.desc())
        .first()
    )
    stage_name = latest_stage.stage if latest_stage else ""
    scheduled = str(latest_stage.scheduled_date) if latest_stage and latest_stage.scheduled_date else None

    result = generate_email(
        candidate_id=payload.candidate_id,
        template_type=payload.template_type,
        custom_data=payload.custom_data,
        candidate_name=candidate_name,
        position=position,
        stage=stage_name,
        scheduled_date=scheduled,
    )

    return EmailResponse(subject=result["subject"], body=result["body"])
