import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload

from recruiter_workflow.models import Candidate, JobDescription, Resume, RecruitmentStage, Meeting
from recruiter_workflow.services.embedding_service import compute_similarity
from recruiter_workflow.services.llm_service import _call_llm, generate_summary, generate_interview_questions
from recruiter_workflow.services.calendar_service import create_google_calendar_event
from recruiter_workflow.services.email_service import generate_email, send_email_notification

logger = logging.getLogger(__name__)

def run_candidate_workflow(db: Session, candidate_id: int) -> dict:
    """Run the entire autonomous recruitment workflow for a candidate.
    
    Processes the candidate through ranking, match explanation, summary, 
    interview questions, pipeline tracking, calendar scheduling, and automated emailing.
    """
    logger.info(f"Triggering automated workflow for candidate ID {candidate_id}")
    
    candidate = (
        db.query(Candidate)
        .options(
            joinedload(Candidate.resume),
            joinedload(Candidate.job_description)
        )
        .filter(Candidate.id == candidate_id)
        .first()
    )
    
    if not candidate:
        logger.error(f"Candidate {candidate_id} not found")
        return {"success": False, "error": f"Candidate {candidate_id} not found"}
        
    resume = candidate.resume
    jd = candidate.job_description
    
    if not resume or not jd:
        logger.error(f"Candidate {candidate_id} is missing resume or job description link")
        return {"success": False, "error": "Missing resume or job description association"}
        
    jd_text = f"{jd.title}\n{jd.description}\n{jd.required_skills or ''}"
    
    # ─── Step 1: Rank Candidate ───
    if not candidate.similarity_score:
        logger.info(f"Computing similarity score for candidate {candidate_id}")
        score = compute_similarity(jd_text, resume.raw_text)
        candidate.similarity_score = score
        db.flush()
    
    # ─── Step 2: Generate Explainable Match Score ───
    if not candidate.explanation:
        logger.info(f"Generating match score explanation for candidate {candidate_id}")
        score_pct = int(candidate.similarity_score * 100)
        explanation_prompt = (
            f"Write a clear, professional, and explainable summary (2-3 sentences) explaining why candidate "
            f"'{resume.candidate_name}' received a match score of {score_pct}% for the role '{jd.title}' "
            f"based on their resume and the job description. Focus on matching skills, experience, and key gaps."
        )
        explanation = _call_llm(
            system_prompt="You are a professional recruiting assistant explaining match similarity scores to a hiring manager.",
            user_prompt=explanation_prompt,
            max_tokens=250,
            temperature=0.3
        )
        if not explanation:
            explanation = f"Match similarity calculated at {score_pct}%. Candidate demonstrates key overlap in technical skills specified in the Job Description. Detailed review of gaps is advised."
        candidate.explanation = explanation
        db.flush()
        
    # ─── Step 3: Generate Summary ───
    if not candidate.summary:
        logger.info(f"Generating candidate summary for candidate {candidate_id}")
        summary = generate_summary(resume.raw_text, jd_text)
        candidate.summary = summary
        db.flush()
        
    # ─── Step 4: Generate Personalized Interview Questions ───
    if not candidate.interview_questions:
        logger.info(f"Generating interview questions for candidate {candidate_id}")
        questions = generate_interview_questions(resume.raw_text, jd_text, count=5)
        candidate.interview_questions = "\n".join(questions)
        db.flush()
    else:
        questions = candidate.interview_questions.split("\n")
        
    # ─── Step 5: Update Recruitment Stage to Technical Interview ───
    # We update the stage to Technical Interview and schedule it
    scheduled_time = datetime.utcnow() + timedelta(days=1, hours=2)  # Scheduled for tomorrow + 2 hours
    
    # Create the stage in db
    stage = RecruitmentStage(
        candidate_id=candidate.id,
        stage="Technical Interview",
        scheduled_date=scheduled_time,
        notes="Automated technical interview scheduled during pipeline run."
    )
    db.add(stage)
    candidate.status = "Interview"
    db.flush()
    
    # ─── Step 6: Schedule Google Calendar Event & Get Link ───
    logger.info(f"Scheduling calendar event for candidate {candidate_id}")
    meeting_details = create_google_calendar_event(
        summary=f"Technical Interview: {resume.candidate_name or 'Candidate'} - {jd.title}",
        attendee_email=resume.email or "candidate@example.com",
        start_time=scheduled_time,
        duration_minutes=30,
        description=f"Technical Interview for candidate {resume.candidate_name}.\n\nTailored Interview Questions:\n" + "\n".join([f"- {q}" for q in questions])
    )
    
    event_id = meeting_details.get("event_id")
    meeting_link = meeting_details.get("meeting_link")
    
    # Save calendar / meeting details in Candidate
    candidate.calendar_event_id = event_id
    candidate.meeting_link = meeting_link
    candidate.scheduled_date = scheduled_time
    
    # Create Meeting model record
    meeting = Meeting(
        candidate_id=candidate.id,
        title=f"Technical Interview: {resume.candidate_name or 'Candidate'}",
        meeting_link=meeting_link,
        scheduled_at=scheduled_time,
        duration_minutes=30,
        attendees=resume.email,
        notes=f"Auto-generated Google Calendar meeting. Event ID: {event_id}",
        calendar_event_id=event_id
    )
    db.add(meeting)
    db.flush()
    
    # ─── Step 7: Generate Email Invitation ───
    logger.info(f"Drafting automated interview email for candidate {candidate_id}")
    email_draft = generate_email(
        candidate_id=candidate.id,
        template_type="interview_scheduling",
        candidate_name=resume.candidate_name or "Candidate",
        position=jd.title,
        stage="Technical Interview",
        scheduled_date=scheduled_time.strftime("%Y-%m-%d %H:%M UTC")
    )
    
    # ─── Step 8: Send Email Automatically ───
    recipient_email = resume.email or "candidate@example.com"
    send_result = send_email_notification(
        to_email=recipient_email,
        subject=email_draft["subject"],
        body=email_draft["body"]
    )
    
    if send_result.get("success"):
        candidate.email_status = "Sent"
        candidate.email_error_reason = None
        logger.info(f"Interview invitation email sent to {recipient_email}")
    else:
        candidate.email_status = "Failed"
        candidate.email_error_reason = send_result.get("error", "Unknown email sending error")
        logger.error(f"Email automation failed for candidate {candidate_id}: {candidate.email_error_reason}")
    
    # ─── Step 9: Commit ───
    db.commit()
    logger.info(f"Autonomous workflow completed successfully for candidate {candidate_id}")
    
    return {
        "success": True,
        "candidate_id": candidate_id,
        "similarity_score": candidate.similarity_score,
        "explanation": candidate.explanation,
        "summary": candidate.summary,
        "meeting_link": candidate.meeting_link,
        "calendar_event_id": candidate.calendar_event_id,
        "email_status": candidate.email_status,
        "email_error_reason": candidate.email_error_reason
    }
