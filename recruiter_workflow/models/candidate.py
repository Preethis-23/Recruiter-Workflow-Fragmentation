from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from recruiter_workflow.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    jd_id = Column(Integer, ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    similarity_score = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    interview_questions = Column(Text, nullable=True)
    email_status = Column(String(100), nullable=True)
    email_error_reason = Column(Text, nullable=True)
    calendar_event_id = Column(String(255), nullable=True)
    meeting_link = Column(String(500), nullable=True)
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="New", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job_description = relationship("JobDescription", backref="candidates")
    resume = relationship("Resume", backref="candidates")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "jd_id": self.jd_id,
            "resume_id": self.resume_id,
            "similarity_score": self.similarity_score,
            "summary": self.summary,
            "explanation": self.explanation,
            "interview_questions": self.interview_questions,
            "email_status": self.email_status,
            "email_error_reason": self.email_error_reason,
            "calendar_event_id": self.calendar_event_id,
            "meeting_link": self.meeting_link,
            "scheduled_date": str(self.scheduled_date) if self.scheduled_date else None,
            "status": self.status,
            "notes": self.notes,
            "created_at": str(self.created_at) if self.created_at else None,
        }
