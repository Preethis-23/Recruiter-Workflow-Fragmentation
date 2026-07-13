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
    status = Column(String(50), nullable=False, default="New", index=True)
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
            "status": self.status,
            "created_at": str(self.created_at) if self.created_at else None,
        }
