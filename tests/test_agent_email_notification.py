"""Test automated candidate status update and email notification delivery."""

import pytest
from recruiter_workflow.database import SessionLocal
from recruiter_workflow.models import JobDescription, Resume, Candidate
from recruiter_workflow.services.pipeline_service import (
    schedule_and_email_candidate,
    reject_and_email_candidate,
    batch_update_candidates_with_emails,
)
from recruiter_workflow.services.agent_service import _execute_tool


@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()


def test_schedule_and_email_candidate_interview(db_session):
    """Test candidate moving to Next Round (Interview) sends interview email with Google Meet link."""
    jd = JobDescription(
        title="Senior Python Backend Lead",
        department="Engineering",
        description="Lead backend architecture using Django, Celery, and PostgreSQL.",
        required_skills="Python, Django, Celery, PostgreSQL"
    )
    db_session.add(jd)
    db_session.commit()
    db_session.refresh(jd)

    resume = Resume(
        file_path="./uploads/test_cand_1.pdf",
        candidate_name="Alex Mercer",
        email="alex.mercer@example.com",
        skills="Python, Django, PostgreSQL, Celery",
        raw_text="Alex Mercer. Experienced Python Developer."
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    candidate = Candidate(
        jd_id=jd.id,
        resume_id=resume.id,
        status="New",
        interview_questions="1. Describe your experience with Celery."
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    # Execute scheduling and email
    res = schedule_and_email_candidate(db_session, candidate.id)

    assert res["success"] is True
    assert res["decision"] == "Selected (Next Round / Interview)"
    assert res["email_status"] == "Sent"
    assert "https://meet.google.com" in res["meeting_link"]

    db_session.refresh(candidate)
    assert candidate.status == "Interview"
    assert candidate.email_status == "Sent"
    assert candidate.meeting_link is not None


def test_reject_and_email_candidate(db_session):
    """Test candidate moving to Rejected sends rejection email."""
    jd = JobDescription(
        title="Full Stack Engineer",
        department="Engineering",
        description="Full stack web development.",
        required_skills="JavaScript, React, Node.js"
    )
    db_session.add(jd)
    db_session.commit()
    db_session.refresh(jd)

    resume = Resume(
        file_path="./uploads/test_cand_2.pdf",
        candidate_name="John Doe",
        email="john.doe@example.com",
        skills="Java, C++",
        raw_text="John Doe. Java Developer."
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    candidate = Candidate(
        jd_id=jd.id,
        resume_id=resume.id,
        status="New",
        interview_questions="1. Experience with React?"
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    res = reject_and_email_candidate(db_session, candidate.id)

    assert res["success"] is True
    assert res["decision"] == "Rejected"
    assert res["email_status"] == "Sent"

    db_session.refresh(candidate)
    assert candidate.status == "Rejected"
    assert candidate.email_status == "Sent"


def test_agent_update_candidate_status_tool(db_session):
    """Test agent update_candidate_status tool automatically dispatches corresponding emails."""
    jd = db_session.query(JobDescription).first()
    resume = db_session.query(Resume).first()
    candidate = Candidate(
        jd_id=jd.id,
        resume_id=resume.id,
        status="New",
        interview_questions="1. Tell me about your background."
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    # Agent updates status to Interview -> should auto-send interview invite
    tool_res = _execute_tool("update_candidate_status", {"candidate_id": candidate.id, "status": "Interview"}, db_session)
    assert tool_res["success"] is True
    assert tool_res["email_status"] == "Sent"

    db_session.refresh(candidate)
    assert candidate.status == "Interview"
    assert candidate.email_status == "Sent"
