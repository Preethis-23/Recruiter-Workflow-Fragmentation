from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from recruiter_workflow.database import Base


class RecruitmentStage(Base):
    __tablename__ = "recruitment_stages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(100), nullable=False, index=True)
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="Pending")
    notes = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    candidate = relationship("Candidate", backref="stages")

    STAGE_TYPES = [
        "Screening",
        "Phone Interview",
        "Technical Interview",
        "HR Interview",
        "Assignment",
        "Final Round",
        "Offer",
        "Hired",
        "Rejected",
    ]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "stage": self.stage,
            "scheduled_date": str(self.scheduled_date) if self.scheduled_date else None,
            "status": self.status,
            "notes": self.notes,
            "feedback": self.feedback,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }
