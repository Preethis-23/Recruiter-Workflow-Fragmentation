"""Resume router — handles file uploads and resume CRUD."""

import os
import hashlib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from recruiter_workflow.database import get_db
from recruiter_workflow.config import settings
from recruiter_workflow.models import Resume, Candidate
from recruiter_workflow.schemas import ResumeCreate, ResumeResponse
from recruiter_workflow.services.parser_service import extract_text, parse_resume_sections

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])


@router.get("/", response_model=list[ResumeResponse])
def list_resumes(db: Session = Depends(get_db)):
    """Return all uploaded resumes."""
    return db.query(Resume).order_by(Resume.parsed_at.desc()).all()


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: int, db: Session = Depends(get_db)):
    """Return a single resume by ID."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.post("/upload", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
def upload_resume_file(
    file: UploadFile = File(...), 
    jd_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload a resume file (PDF or DOCX) via multipart form, parse and store it.
    
    If jd_id is provided, automatically creates a Candidate record linking it to that role.
    If the file is already uploaded, allows assigning the existing resume to a new jd_id.
    """
    # Validate file extension
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Only .pdf and .docx are allowed.")

    # Read file content
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Check file size
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE // (1024*1024)}MB.")

    # Create uploads directory
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename using content hash to prevent duplicates
    content_hash = hashlib.md5(content).hexdigest()[:12]
    safe_name = f"{content_hash}_{filename}"
    file_path = os.path.join(upload_dir, safe_name)

    # Check if this exact content has already been uploaded, or if the filename matches exactly
    existing = db.query(Resume).filter(
        (Resume.file_path == file_path) | (Resume.file_path.like(f"%{filename}"))
    ).first()

    if existing:
        if jd_id:
            # Check if this resume is already applied to this JD
            candidate = db.query(Candidate).filter(Candidate.resume_id == existing.id, Candidate.jd_id == jd_id).first()
            if candidate:
                raise HTTPException(status_code=409, detail=f"Resume '{filename}' is already assigned to this Job Description.")
            else:
                # Link existing resume to the new JD
                new_candidate = Candidate(jd_id=jd_id, resume_id=existing.id, status="New")
                db.add(new_candidate)
                db.commit()
                return existing # Successfully linked
        else:
            raise HTTPException(status_code=409, detail=f"A resume with filename '{filename}' already exists in the general pool. Select a specific Job Description to assign it to a new role.")

    # Save file to disk since it's truly new
    with open(file_path, "wb") as f:
        f.write(content)

    # Extract and parse
    try:
        raw_text = extract_text(file_path)
    except (FileNotFoundError, ValueError) as exc:
        os.remove(file_path)  # Clean up on failure
        raise HTTPException(status_code=400, detail=str(exc))

    parsed = parse_resume_sections(raw_text)

    resume = Resume(
        file_path=file_path,
        candidate_name=parsed.get("candidate_name"),
        email=parsed.get("email"),
        phone=parsed.get("phone"),
        education=parsed.get("education"),
        skills=parsed.get("skills"),
        projects=parsed.get("projects"),
        experience=parsed.get("experience"),
        certifications=parsed.get("certifications"),
        raw_text=raw_text,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # If a JD was selected during upload, automatically create the Candidate link
    if jd_id:
        candidate = Candidate(jd_id=jd_id, resume_id=resume.id, status="New")
        db.add(candidate)
        db.commit()

    return resume


@router.post("/upload-path", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
def upload_resume_by_path(payload: ResumeCreate, db: Session = Depends(get_db)):
    """Upload and parse a resume using a local file path (for agent/CLI use)."""
    # Check for duplicate file path
    existing = db.query(Resume).filter(Resume.file_path == payload.file_path).first()
    if existing:
        raise HTTPException(status_code=409, detail="Resume with this file path already exists")

    # Extract text
    try:
        raw_text = extract_text(payload.file_path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Parse sections
    parsed = parse_resume_sections(raw_text)

    resume = Resume(
        file_path=payload.file_path,
        candidate_name=parsed.get("candidate_name"),
        email=parsed.get("email"),
        phone=parsed.get("phone"),
        education=parsed.get("education"),
        skills=parsed.get("skills"),
        projects=parsed.get("projects"),
        experience=parsed.get("experience"),
        certifications=parsed.get("certifications"),
        raw_text=raw_text,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    """Delete a resume record."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    db.delete(resume)
    db.commit()
