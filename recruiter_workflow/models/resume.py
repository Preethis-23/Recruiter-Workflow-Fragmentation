from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from recruiter_workflow.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_path = Column(String(500), unique=True, nullable=False)
    candidate_name = Column(String(255), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    education = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)
    projects = Column(Text, nullable=True)
    experience = Column(Text, nullable=True)
    certifications = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)
    parsed_at = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def applied_roles(self) -> list[str]:
        return [c.job_description.title for c in self.candidates if c.job_description]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_path": self.file_path,
            "candidate_name": self.candidate_name,
            "email": self.email,
            "phone": self.phone,
            "education": self.education,
            "skills": self.skills,
            "projects": self.projects,
            "experience": self.experience,
            "certifications": self.certifications,
            "parsed_at": str(self.parsed_at) if self.parsed_at else None,
        }
