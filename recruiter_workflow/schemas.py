from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ─── Job Description ──────────────────────────────────────────────────────────

class JobDescriptionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    min_experience: Optional[int] = Field(None, ge=0)
    max_experience: Optional[int] = Field(None, ge=0)
    min_salary: Optional[int] = Field(None, ge=0)
    max_salary: Optional[int] = Field(None, ge=0)
    required_skills: Optional[str] = None


class JobDescriptionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    min_experience: Optional[int] = Field(None, ge=0)
    max_experience: Optional[int] = Field(None, ge=0)
    min_salary: Optional[int] = Field(None, ge=0)
    max_salary: Optional[int] = Field(None, ge=0)
    required_skills: Optional[str] = None


class JobDescriptionResponse(BaseModel):
    id: int
    title: str
    description: str
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    min_experience: Optional[int] = None
    max_experience: Optional[int] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    required_skills: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Resume ───────────────────────────────────────────────────────────────────

class ResumeCreate(BaseModel):
    file_path: str = Field(..., min_length=1)


class ResumeResponse(BaseModel):
    id: int
    file_path: str
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    education: Optional[str] = None
    skills: Optional[str] = None
    projects: Optional[str] = None
    experience: Optional[str] = None
    certifications: Optional[str] = None
    parsed_at: Optional[datetime] = None
    applied_roles: list[str] = []

    model_config = {"from_attributes": True}


# ─── Candidate ────────────────────────────────────────────────────────────────

class CandidateResponse(BaseModel):
    id: int
    jd_id: int
    resume_id: int
    resume: Optional[ResumeResponse] = None
    similarity_score: Optional[float] = None
    summary: Optional[str] = None
    explanation: Optional[str] = None
    interview_questions: Optional[str] = None
    email_status: Optional[str] = None
    email_error_reason: Optional[str] = None
    calendar_event_id: Optional[str] = None
    meeting_link: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    status: str = "New"
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CandidateStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1)

class CandidateNotesUpdate(BaseModel):
    notes: Optional[str] = None


# ─── Recruitment Stage ────────────────────────────────────────────────────────

class RecruitmentStageCreate(BaseModel):
    stage: str = Field(..., min_length=1)
    scheduled_date: Optional[datetime] = None
    notes: Optional[str] = None


class RecruitmentStageUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    feedback: Optional[str] = None
    scheduled_date: Optional[datetime] = None


class RecruitmentStageResponse(BaseModel):
    id: int
    candidate_id: int
    stage: str
    scheduled_date: Optional[datetime] = None
    status: str = "Pending"
    notes: Optional[str] = None
    feedback: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Interview Questions ─────────────────────────────────────────────────────

class InterviewQuestionRequest(BaseModel):
    resume_id: int
    jd_id: int


class InterviewQuestionResponse(BaseModel):
    questions: list[str]


# ─── Email ────────────────────────────────────────────────────────────────────

class EmailRequest(BaseModel):
    candidate_id: int
    template_type: str = Field(..., pattern=r"^(interview_scheduling|offer|rejection|follow_up)$")
    custom_data: Optional[dict] = None


class EmailResponse(BaseModel):
    subject: str
    body: str


# ─── Meeting ──────────────────────────────────────────────────────────────────

class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    meeting_link: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(30, ge=5, le=480)
    attendees: Optional[str] = None
    notes: Optional[str] = None
    calendar_event_id: Optional[str] = None


class MeetingUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    meeting_link: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    attendees: Optional[str] = None
    notes: Optional[str] = None
    calendar_event_id: Optional[str] = None


class MeetingResponse(BaseModel):
    id: int
    candidate_id: int
    title: str
    meeting_link: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    attendees: Optional[str] = None
    notes: Optional[str] = None
    calendar_event_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Ranking ──────────────────────────────────────────────────────────────────

class RankedCandidateResponse(BaseModel):
    candidate: CandidateResponse
    similarity_score: float
