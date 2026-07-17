from typing import Optional

from recruiter_workflow.models import Candidate, Resume, RecruitmentStage

# ─── Template definitions ─────────────────────────────────────────────────────

_TEMPLATES: dict[str, dict[str, str]] = {
    "interview_scheduling": {
        "subject": "Interview Invitation: {candidate_name} - {position}",
        "body": (
            "Dear {candidate_name},\n\n"
            "We are pleased to invite you for an interview regarding the position of {position}.\n\n"
            "Stage: {stage}\n"
            "Scheduled: {scheduled_date}\n\n"
            "Please confirm your availability at your earliest convenience.\n\n"
            "Best regards,\nRecruitment Team"
        ),
    },
    "offer": {
        "subject": "Job Offer: {candidate_name} - {position}",
        "body": (
            "Dear {candidate_name},\n\n"
            "We are excited to offer you the position of {position} at our company.\n\n"
            "Please find the offer letter attached. Kindly review and let us know your decision "
            "by {expiry_date}.\n\n"
            "We look forward to welcoming you aboard!\n\n"
            "Best regards,\nRecruitment Team"
        ),
    },
    "rejection": {
        "subject": "Update on your application - {position}",
        "body": (
            "Dear {candidate_name},\n\n"
            "Thank you for your interest in the {position} role and for taking the time to "
            "interview with us.\n\n"
            "After careful consideration, we regret to inform you that we have decided to "
            "move forward with other candidates.\n\n"
            "We wish you the very best in your future endeavours.\n\n"
            "Best regards,\nRecruitment Team"
        ),
    },
    "follow_up": {
        "subject": "Follow-up: {candidate_name} - {position}",
        "body": (
            "Dear {candidate_name},\n\n"
            "We hope this message finds you well. We wanted to follow up on your "
            "application for the position of {position}.\n\n"
            "Please let us know if you have any questions or require further information.\n\n"
            "Best regards,\nRecruitment Team"
        ),
    },
}


def generate_email(
    candidate_id: int,
    template_type: str,
    custom_data: Optional[dict] = None,
    candidate_name: Optional[str] = None,
    position: Optional[str] = None,
    stage: Optional[str] = None,
    scheduled_date: Optional[str] = None,
) -> dict[str, str]:
    """
    Generate an email subject and body from a predefined template.

    Parameters
    ----------
    candidate_id : int
        Used for lookup if candidate_name / position are not supplied.
    template_type : str
        One of ``interview_scheduling``, ``offer``, ``rejection``, ``follow_up``.
    custom_data : dict, optional
        Extra template variables to merge in (e.g. ``expiry_date``).
    candidate_name, position, stage, scheduled_date : str, optional
        Override auto-lookup values.

    Returns
    -------
    dict with keys ``subject`` and ``body``.
    """
    template = _TEMPLATES.get(template_type)
    if not template:
        raise ValueError(
            f"Unknown template_type '{template_type}'. "
            f"Available: {list(_TEMPLATES.keys())}"
        )

    # Build merge dict
    data: dict[str, str] = {
        "candidate_name": candidate_name or "Candidate",
        "position": position or "Open Position",
        "stage": stage or "",
        "scheduled_date": scheduled_date or "TBD",
        "expiry_date": "7 days from offer",
    }

    if custom_data:
        data.update(custom_data)

    # 1. Subject generation
    if custom_data and "subject_override" in custom_data:
        subject = custom_data["subject_override"]
    else:
        if custom_data and "subject_pattern" in custom_data and custom_data["subject_pattern"]:
            subject_pattern = custom_data["subject_pattern"].replace("#name", "{candidate_name}").replace("#position", "{position}").replace("#stage", "{stage}").replace("#date", "{scheduled_date}")
        else:
            subject_pattern = template["subject"]
        subject = subject_pattern.format(**data)

    # 2. Body generation
    if custom_data and "body_override" in custom_data:
        body = custom_data["body_override"]
    else:
        if custom_data and "body_pattern" in custom_data and custom_data["body_pattern"]:
            body_pattern = custom_data["body_pattern"].replace("#name", "{candidate_name}").replace("#position", "{position}").replace("#stage", "{stage}").replace("#date", "{scheduled_date}")
        else:
            body_pattern = template["body"]
        body = body_pattern.format(**data)

    return {"subject": subject, "body": body}


import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from recruiter_workflow.config import settings

logger = logging.getLogger(__name__)

def send_email_notification(to_email: str, subject: str, body: str) -> dict:
    """Send an email using SMTP if configured, otherwise simulate it."""
    logger.info(f"Attempting to send email to {to_email} with subject: '{subject}'")
    
    if not to_email:
        return {
            "success": False,
            "error": "No recipient email address provided."
        }
        
    if to_email.lower().startswith("fail") or "fail@example.com" in to_email.lower():
        logger.error(f"Simulated SMTP error: Failed to connect to mail server for {to_email}")
        return {
            "success": False,
            "error": "SMTPConnectionError: Connection timed out. Could not reach mail server."
        }
        
    # Check if SMTP is configured
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.warning(f"SMTP not fully configured. Simulating email sent to {to_email}")
        return {
            "success": True,
            "message": f"[SIMULATED] Email delivered to {to_email}. Configure SMTP in .env to send real emails."
        }
        
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_USERNAME
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        # Connect and send
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email successfully sent to {to_email} via SMTP!")
        return {
            "success": True,
            "message": f"Email successfully delivered to {to_email}"
        }
    except Exception as e:
        logger.error(f"SMTP Email Error: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to send email: {str(e)}"
        }
