from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from recruiter_workflow.database import Base


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    department = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    employment_type = Column(String(100), nullable=True)
    min_experience = Column(Integer, nullable=True)
    max_experience = Column(Integer, nullable=True)
    min_salary = Column(Integer, nullable=True)
    max_salary = Column(Integer, nullable=True)
    required_skills = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "department": self.department,
            "location": self.location,
            "employment_type": self.employment_type,
            "min_experience": self.min_experience,
            "max_experience": self.max_experience,
            "min_salary": self.min_salary,
            "max_salary": self.max_salary,
            "required_skills": self.required_skills,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }
