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

    subject = template["subject"].format(**data)
    body = template["body"].format(**data)

    return {"subject": subject, "body": body}
