from sqlalchemy.orm import Session, joinedload

from recruiter_workflow.models import JobDescription, Resume, Candidate
from recruiter_workflow.services.embedding_service import compute_similarity
from recruiter_workflow.services.parser_service import extract_text


def rank_resumes_for_jd(db: Session, jd_id: int) -> list[dict]:
    """Compute similarity scores between a JD and all resumes assigned to this JD."""
    jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
    if not jd:
        raise ValueError(f"JobDescription with id={jd_id} not found")

    jd_text = f"{jd.title}\n{jd.description}\n{jd.required_skills or ''}"
    
    # Only get candidates that applied for this specific JD
    candidates = db.query(Candidate).options(joinedload(Candidate.resume)).filter(Candidate.jd_id == jd_id).all()
    
    results = []

    for candidate in candidates:
        if not candidate.resume or not candidate.resume.raw_text:
            continue

        similarity = compute_similarity(jd_text, candidate.resume.raw_text)

        # Update candidate record
        candidate.similarity_score = similarity

        db.flush()
        results.append(
            {
                "candidate_id": candidate.id,
                "resume_id": candidate.resume.id,
                "candidate_name": candidate.resume.candidate_name,
                "email": candidate.resume.email,
                "similarity_score": round(similarity, 4),
            }
        )

    db.commit()

    # Sort by score descending
    results.sort(key=lambda r: r["similarity_score"], reverse=True)
    return results


def get_ranked_candidates(db: Session, jd_id: int) -> list[dict]:
    """Return candidates for a JD sorted by similarity score (descending)."""
    candidates = (
        db.query(Candidate)
        .options(joinedload(Candidate.resume))
        .filter(Candidate.jd_id == jd_id)
        .order_by(Candidate.similarity_score.desc())
        .all()
    )

    return [
        {
            "id": c.id,
            "jd_id": c.jd_id,
            "resume_id": c.resume_id,
            "candidate_name": c.resume.candidate_name if c.resume else None,
            "email": c.resume.email if c.resume else None,
            "similarity_score": round(c.similarity_score, 4) if c.similarity_score else 0.0,
            "summary": c.summary,
            "status": c.status,
        }
        for c in candidates
    ]
