from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

class JD(Base):
    __tablename__ = "jd"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)

class Resume(Base):
    __tablename__ = "resume"
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    email = Column(String, index=True)
    education = Column(String, index=True)
    skills = Column(String, index=True)
    projects = Column(String, index=True)
    experience = Column(String, index=True)
    certifications = Column(String, index=True)

class Candidate(Base):
    __tablename__ = "candidate"
    id = Column(Integer, primary_key=True, index=True)
    jd_id = Column(Integer, ForeignKey("jd.id"), index=True)
    resume_id = Column(Integer, ForeignKey("resume.id"), index=True)
    similarity_score = Column(Float, index=True)
    summary = Column(String, index=True)

class RecruitmentStage(Base):
    __tablename__ = "recruitment_stage"
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidate.id"), index=True)
    stage = Column(String, index=True)
    date = Column(String, index=True)
    notes = Column(String, index=True)

engine = create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
