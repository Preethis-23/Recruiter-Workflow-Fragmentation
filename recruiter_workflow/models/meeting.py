from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from recruiter_workflow.database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    meeting_link = Column(String(500), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True, default=30)
    attendees = Column(Text, nullable=True)  # comma-separated emails
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    candidate = relationship("Candidate", backref="meetings")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "title": self.title,
            "meeting_link": self.meeting_link,
            "scheduled_at": str(self.scheduled_at) if self.scheduled_at else None,
            "duration_minutes": self.duration_minutes,
            "attendees": self.attendees,
            "notes": self.notes,
            "created_at": str(self.created_at) if self.created_at else None,
        }
