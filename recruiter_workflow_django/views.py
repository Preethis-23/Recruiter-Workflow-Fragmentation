import os
import json
import hashlib
from datetime import datetime
from typing import Optional

from django.http import JsonResponse, HttpResponse, HttpResponseNotFound, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings as django_settings

from sqlalchemy.orm import joinedload
from recruiter_workflow.config import settings
from recruiter_workflow.database import SessionLocal
from recruiter_workflow.models import JobDescription, Resume, Candidate, RecruitmentStage, Meeting
from recruiter_workflow.schemas import (
    JobDescriptionCreate,
    JobDescriptionUpdate,
    JobDescriptionResponse,
    ResumeResponse,
    CandidateResponse,
    RecruitmentStageResponse,
    MeetingResponse,
)
from recruiter_workflow.services.parser_service import extract_text, parse_resume_sections
from recruiter_workflow.services.ranking_service import rank_resumes_for_jd, get_ranked_candidates
from recruiter_workflow.services.llm_service import generate_summary, generate_interview_questions
from recruiter_workflow.services.email_service import generate_email, send_email_notification
from recruiter_workflow.services.agent_service import execute_agent, execute_pipeline, AGENT_TOOLS


def _get_db():
    return SessionLocal()


def _json_body(request):
    try:
        if request.body:
            return json.loads(request.body.decode('utf-8'))
        return {}
    except Exception:
        return {}


# ─── Index & Health ─────────────────────────────────────────────────────────

def index_view(request):
    """Serve the single page recruiter dashboard."""
    index_file = os.path.join(django_settings.BASE_DIR, 'static', 'index.html')
    if os.path.exists(index_file):
        with open(index_file, 'r', encoding='utf-8') as f:
            return HttpResponse(f.read(), content_type='text/html')
    return HttpResponse("Recruiter Workflow API is running.", content_type='text/plain')


def health_check(request):
    """Health check endpoint."""
    return JsonResponse({
        "status": "healthy",
        "service": "recruiter-workflow-fragmentation",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
    })


# ─── Job Descriptions ───────────────────────────────────────────────────────

@csrf_exempt
def jds_collection(request):
    """List or create job descriptions."""
    db = _get_db()
    try:
        if request.method == 'GET':
            jds = db.query(JobDescription).order_by(JobDescription.created_at.desc()).all()
            data = [JobDescriptionResponse.model_validate(jd).model_dump(mode='json') for jd in jds]
            return JsonResponse(data, safe=False)

        elif request.method == 'POST':
            body = _json_body(request)
            try:
                payload = JobDescriptionCreate(**body)
            except Exception as e:
                return JsonResponse({"detail": str(e)}, status=422)

            existing = db.query(JobDescription).filter(JobDescription.title == payload.title).first()
            if existing:
                return JsonResponse(
                    {"detail": f"A Job Description with the title '{payload.title}' already exists."},
                    status=409
                )

            jd = JobDescription(**payload.model_dump())
            db.add(jd)
            db.commit()
            db.refresh(jd)
            data = JobDescriptionResponse.model_validate(jd).model_dump(mode='json')
            return JsonResponse(data, status=201)

        return JsonResponse({"detail": "Method not allowed"}, status=405)
    finally:
        db.close()


@csrf_exempt
def jd_detail(request, jd_id: int):
    """Get, update, or delete a single job description."""
    db = _get_db()
    try:
        jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
        if not jd:
            return JsonResponse({"detail": "Job description not found"}, status=404)

        if request.method == 'GET':
            data = JobDescriptionResponse.model_validate(jd).model_dump(mode='json')
            return JsonResponse(data)

        elif request.method in ('PUT', 'PATCH'):
            body = _json_body(request)
            try:
                payload = JobDescriptionUpdate(**body)
            except Exception as e:
                return JsonResponse({"detail": str(e)}, status=422)

            if payload.title and payload.title != jd.title:
                existing = db.query(JobDescription).filter(JobDescription.title == payload.title).first()
                if existing:
                    return JsonResponse(
                        {"detail": f"A Job Description with the title '{payload.title}' already exists."},
                        status=409
                    )

            for key, value in payload.model_dump(exclude_unset=True).items():
                setattr(jd, key, value)

            db.commit()
            db.refresh(jd)
            data = JobDescriptionResponse.model_validate(jd).model_dump(mode='json')
            return JsonResponse(data)

        elif request.method == 'DELETE':
            db.delete(jd)
            db.commit()
            return HttpResponse(status=204)

        return JsonResponse({"detail": "Method not allowed"}, status=405)
    finally:
        db.close()


# ─── Resumes ────────────────────────────────────────────────────────────────

@csrf_exempt
def resumes_collection(request):
    """List all resumes."""
    db = _get_db()
    try:
        if request.method == 'GET':
            resumes = db.query(Resume).order_by(Resume.parsed_at.desc()).all()
            data = [ResumeResponse.model_validate(r).model_dump(mode='json') for r in resumes]
            return JsonResponse(data, safe=False)
        return JsonResponse({"detail": "Method not allowed"}, status=405)
    finally:
        db.close()


@csrf_exempt
def resume_detail(request, resume_id: int):
    """Get or delete a single resume."""
    db = _get_db()
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            return JsonResponse({"detail": "Resume not found"}, status=404)

        if request.method == 'GET':
            data = ResumeResponse.model_validate(resume).model_dump(mode='json')
            return JsonResponse(data)

        elif request.method == 'DELETE':
            db.delete(resume)
            db.commit()
            return HttpResponse(status=204)

        return JsonResponse({"detail": "Method not allowed"}, status=405)
    finally:
        db.close()


@csrf_exempt
def resume_upload(request):
    """Upload and parse a resume file (multipart/form-data)."""
    if request.method != 'POST':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    if 'file' not in request.FILES:
        return JsonResponse({"detail": "No file uploaded"}, status=400)

    uploaded_file = request.FILES['file']
    jd_id_raw = request.POST.get('jd_id')
    jd_id = int(jd_id_raw) if jd_id_raw and jd_id_raw.isdigit() else None

    filename = uploaded_file.name or "upload"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".pdf", ".docx"):
        return JsonResponse({"detail": f"Unsupported file type '{ext}'. Only .pdf and .docx are allowed."}, status=400)

    content = uploaded_file.read()
    if not content:
        return JsonResponse({"detail": "Uploaded file is empty."}, status=400)

    if len(content) > settings.MAX_FILE_SIZE:
        return JsonResponse({"detail": f"File too large. Maximum size is {settings.MAX_FILE_SIZE // (1024*1024)}MB."}, status=400)

    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)

    content_hash = hashlib.md5(content).hexdigest()[:12]
    safe_name = f"{content_hash}_{filename}"
    file_path = os.path.join(upload_dir, safe_name)

    db = _get_db()
    try:
        existing = db.query(Resume).filter(
            (Resume.file_path == file_path) | (Resume.file_path.like(f"%{filename}"))
        ).first()

        if existing:
            if jd_id:
                candidate = db.query(Candidate).filter(Candidate.resume_id == existing.id, Candidate.jd_id == jd_id).first()
                if candidate:
                    return JsonResponse({"detail": f"Resume '{filename}' is already assigned to this Job Description."}, status=409)
                else:
                    new_candidate = Candidate(jd_id=jd_id, resume_id=existing.id, status="New")
                    db.add(new_candidate)
                    db.commit()
                    db.refresh(new_candidate)

                    # Trigger autonomous workflow
                    from recruiter_workflow.services.pipeline_service import run_candidate_workflow
                    try:
                        run_candidate_workflow(db, new_candidate.id)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Error running automated workflow: {e}")

                    data = ResumeResponse.model_validate(existing).model_dump(mode='json')
                    return JsonResponse(data, status=201)
            else:
                return JsonResponse({"detail": f"A resume with filename '{filename}' already exists in the general pool."}, status=409)

        with open(file_path, "wb") as f:
            f.write(content)

        try:
            raw_text = extract_text(file_path)
        except (FileNotFoundError, ValueError) as exc:
            if os.path.exists(file_path):
                os.remove(file_path)
            return JsonResponse({"detail": str(exc)}, status=400)

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

        if jd_id:
            candidate = Candidate(jd_id=jd_id, resume_id=resume.id, status="New")
            db.add(candidate)
            db.commit()
            db.refresh(candidate)

            try:
                rank_resumes_for_jd(db, jd_id)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error auto-ranking: {e}")

            from recruiter_workflow.services.pipeline_service import run_candidate_workflow
            try:
                run_candidate_workflow(db, candidate.id)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error running automated workflow: {e}")

        data = ResumeResponse.model_validate(resume).model_dump(mode='json')
        return JsonResponse(data, status=201)
    finally:
        db.close()


@csrf_exempt
def resume_upload_path(request):
    """Upload and parse resume from local file path."""
    if request.method != 'POST':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    body = _json_body(request)
    file_path = body.get("file_path")
    if not file_path:
        return JsonResponse({"detail": "Missing file_path"}, status=400)

    db = _get_db()
    try:
        existing = db.query(Resume).filter(Resume.file_path == file_path).first()
        if existing:
            return JsonResponse({"detail": "Resume with this file path already exists"}, status=409)

        try:
            raw_text = extract_text(file_path)
        except (FileNotFoundError, ValueError) as exc:
            return JsonResponse({"detail": str(exc)}, status=400)

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

        data = ResumeResponse.model_validate(resume).model_dump(mode='json')
        return JsonResponse(data, status=201)
    finally:
        db.close()


# ─── Candidates ─────────────────────────────────────────────────────────────

@csrf_exempt
def candidates_collection(request):
    """List candidates, optionally filtered by jd_id and status."""
    if request.method != 'GET':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    jd_id_raw = request.GET.get('jd_id')
    status_filter = request.GET.get('status_filter')
    jd_id = int(jd_id_raw) if jd_id_raw and jd_id_raw.isdigit() else None

    db = _get_db()
    try:
        if jd_id is not None:
            unranked = db.query(Candidate).filter(Candidate.jd_id == jd_id, Candidate.similarity_score.is_(None)).count()
            if unranked > 0:
                try:
                    rank_resumes_for_jd(db, jd_id)
                except Exception:
                    pass

        query = db.query(Candidate).options(joinedload(Candidate.resume))
        if jd_id is not None:
            query = query.filter(Candidate.jd_id == jd_id)
        if status_filter:
            query = query.filter(Candidate.status == status_filter)

        candidates = query.order_by(Candidate.similarity_score.desc().nulls_last(), Candidate.created_at.desc()).all()
        data = [CandidateResponse.model_validate(c).model_dump(mode='json') for c in candidates]
        return JsonResponse(data, safe=False)
    finally:
        db.close()


@csrf_exempt
def candidate_detail(request, candidate_id: int):
    """Get single candidate by ID."""
    if request.method != 'GET':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    db = _get_db()
    try:
        candidate = db.query(Candidate).options(joinedload(Candidate.resume)).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return JsonResponse({"detail": "Candidate not found"}, status=404)

        data = CandidateResponse.model_validate(candidate).model_dump(mode='json')
        return JsonResponse(data)
    finally:
        db.close()


@csrf_exempt
def candidate_status_update(request, candidate_id: int):
    """Update candidate status."""
    if request.method != 'PUT':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    body = _json_body(request)
    new_status = body.get("status")
    if not new_status:
        return JsonResponse({"detail": "Missing status field"}, status=400)

    db = _get_db()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return JsonResponse({"detail": "Candidate not found"}, status=404)

        candidate.status = new_status
        db.commit()
        db.refresh(candidate)

        data = CandidateResponse.model_validate(candidate).model_dump(mode='json')
        return JsonResponse(data)
    finally:
        db.close()


@csrf_exempt
def candidate_notes_update(request, candidate_id: int):
    """Update candidate notes."""
    if request.method != 'PUT':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    body = _json_body(request)
    notes = body.get("notes")

    db = _get_db()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return JsonResponse({"detail": "Candidate not found"}, status=404)

        candidate.notes = notes
        db.commit()
        db.refresh(candidate)

        data = CandidateResponse.model_validate(candidate).model_dump(mode='json')
        return JsonResponse(data)
    finally:
        db.close()


@csrf_exempt
def candidate_batch_decision(request):
    """Recruiter batch decision for a JD."""
    if request.method != 'POST':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    body = _json_body(request)
    jd_id = body.get("jd_id")
    selected_candidate_ids = body.get("selected_candidate_ids", [])

    if jd_id is None:
        return JsonResponse({"detail": "Missing jd_id"}, status=400)

    db = _get_db()
    try:
        jd = db.query(JobDescription).filter(JobDescription.id == jd_id).first()
        if not jd:
            return JsonResponse({"detail": f"Job Description #{jd_id} not found"}, status=404)

        candidates = db.query(Candidate).options(joinedload(Candidate.resume)).filter(Candidate.jd_id == jd_id).all()
        if not candidates:
            return JsonResponse({"detail": "No candidates found for this role."}, status=400)

        selected_ids = set(selected_candidate_ids)
        results = {
            "jd_id": jd_id,
            "role_title": jd.title,
            "selected_count": 0,
            "rejected_count": 0,
            "email_logs": []
        }

        for candidate in candidates:
            resume = candidate.resume
            candidate_name = resume.candidate_name if resume else "Candidate"
            recipient_email = (resume.email if resume and resume.email else "").strip()

            if candidate.id in selected_ids:
                candidate.status = "Interview"
                results["selected_count"] += 1

                email_draft = generate_email(
                    candidate_id=candidate.id,
                    template_type="interview_scheduling",
                    candidate_name=candidate_name,
                    position=jd.title,
                    stage="Technical Interview",
                    scheduled_date=datetime.utcnow().strftime("%Y-%m-%d")
                )

                if recipient_email:
                    send_res = send_email_notification(recipient_email, email_draft["subject"], email_draft["body"])
                    candidate.email_status = "Sent" if send_res.get("success") else "Failed"
                    candidate.email_error_reason = None if send_res.get("success") else send_res.get("error")
                    results["email_logs"].append({
                        "candidate_id": candidate.id,
                        "candidate_name": candidate_name,
                        "email": recipient_email,
                        "decision": "Selected (Next Round)",
                        "email_status": candidate.email_status,
                        "detail": send_res.get("message") or send_res.get("error")
                    })
                else:
                    candidate.email_status = "Failed"
                    candidate.email_error_reason = "No extracted email address on resume"
                    results["email_logs"].append({
                        "candidate_id": candidate.id,
                        "candidate_name": candidate_name,
                        "email": "None",
                        "decision": "Selected (Next Round)",
                        "email_status": "Failed",
                        "detail": "Missing candidate email address"
                    })
            else:
                candidate.status = "Rejected"
                results["rejected_count"] += 1

                email_draft = generate_email(
                    candidate_id=candidate.id,
                    template_type="rejection",
                    candidate_name=candidate_name,
                    position=jd.title
                )

                if recipient_email:
                    send_res = send_email_notification(recipient_email, email_draft["subject"], email_draft["body"])
                    candidate.email_status = "Sent" if send_res.get("success") else "Failed"
                    candidate.email_error_reason = None if send_res.get("success") else send_res.get("error")
                    results["email_logs"].append({
                        "candidate_id": candidate.id,
                        "candidate_name": candidate_name,
                        "email": recipient_email,
                        "decision": "Rejected",
                        "email_status": candidate.email_status,
                        "detail": send_res.get("message") or send_res.get("error")
                    })
                else:
                    candidate.email_status = "Failed"
                    candidate.email_error_reason = "No extracted email address on resume"
                    results["email_logs"].append({
                        "candidate_id": candidate.id,
                        "candidate_name": candidate_name,
                        "email": "None",
                        "decision": "Rejected",
                        "email_status": "Failed",
                        "detail": "Missing candidate email address"
                    })

        db.commit()
        return JsonResponse(results)
    finally:
        db.close()


@csrf_exempt
def candidate_rank(request, jd_id: int):
    """Rank candidates for a JD (POST to recompute, GET to fetch ranked list)."""
    db = _get_db()
    try:
        if request.method == 'POST':
            try:
                results = rank_resumes_for_jd(db, jd_id)
            except ValueError as exc:
                return JsonResponse({"detail": str(exc)}, status=404)
            return JsonResponse({"message": f"Ranked {len(results)} candidates", "results": results})

        elif request.method == 'GET':
            ranked = get_ranked_candidates(db, jd_id)
            return JsonResponse(ranked, safe=False)

        return JsonResponse({"detail": "Method not allowed"}, status=405)
    finally:
        db.close()


@csrf_exempt
def candidate_summary(request, candidate_id: int):
    """Generate AI summary for a candidate."""
    if request.method != 'POST':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    db = _get_db()
    try:
        candidate = db.query(Candidate).options(
            joinedload(Candidate.resume), joinedload(Candidate.job_description)
        ).filter(Candidate.id == candidate_id).first()

        if not candidate:
            return JsonResponse({"detail": "Candidate not found"}, status=404)
        if not candidate.resume or not candidate.resume.raw_text:
            return JsonResponse({"detail": "Resume raw text not available"}, status=400)
        if not candidate.job_description:
            return JsonResponse({"detail": "Job description not available"}, status=400)

        jd_text = (
            f"{candidate.job_description.title}\n"
            f"{candidate.job_description.description}\n"
            f"{candidate.job_description.required_skills or ''}"
        )
        summary = generate_summary(candidate.resume.raw_text, jd_text)
        candidate.summary = summary
        db.commit()

        return JsonResponse({"candidate_id": candidate_id, "summary": summary})
    finally:
        db.close()


# ─── Stages ─────────────────────────────────────────────────────────────────

@csrf_exempt
def stages_by_candidate(request, candidate_id: int):
    """List or create recruitment stages for a candidate."""
    db = _get_db()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return JsonResponse({"detail": "Candidate not found"}, status=404)

        if request.method == 'GET':
            stages = db.query(RecruitmentStage).filter(
                RecruitmentStage.candidate_id == candidate_id
            ).order_by(RecruitmentStage.created_at.asc()).all()
            data = [RecruitmentStageResponse.model_validate(s).model_dump(mode='json') for s in stages]
            return JsonResponse(data, safe=False)

        elif request.method == 'POST':
            body = _json_body(request)
            stage_name = body.get("stage")
            if not stage_name or stage_name not in RecruitmentStage.STAGE_TYPES:
                return JsonResponse(
                    {"detail": f"Invalid stage type. Must be one of: {', '.join(RecruitmentStage.STAGE_TYPES)}"},
                    status=400
                )

            scheduled_date = body.get("scheduled_date")
            if scheduled_date and isinstance(scheduled_date, str):
                try:
                    scheduled_date = datetime.fromisoformat(scheduled_date)
                except Exception:
                    pass

            stage = RecruitmentStage(
                candidate_id=candidate_id,
                stage=stage_name,
                scheduled_date=scheduled_date,
                notes=body.get("notes"),
            )
            db.add(stage)
            db.commit()
            db.refresh(stage)

            data = RecruitmentStageResponse.model_validate(stage).model_dump(mode='json')
            return JsonResponse(data, status=201)

        return JsonResponse({"detail": "Method not allowed"}, status=405)
    finally:
        db.close()


@csrf_exempt
def stage_detail(request, stage_id: int):
    """Get, update, or delete a recruitment stage."""
    db = _get_db()
    try:
        stage = db.query(RecruitmentStage).filter(RecruitmentStage.id == stage_id).first()
        if not stage:
            return JsonResponse({"detail": "Stage not found"}, status=404)

        if request.method == 'GET':
            data = RecruitmentStageResponse.model_validate(stage).model_dump(mode='json')
            return JsonResponse(data)

        elif request.method in ('PUT', 'PATCH'):
            body = _json_body(request)
            for k, v in body.items():
                if hasattr(stage, k) and v is not None:
                    if k == 'scheduled_date' and isinstance(v, str):
                        try:
                            v = datetime.fromisoformat(v)
                        except Exception:
                            pass
                    setattr(stage, k, v)

            db.commit()
            db.refresh(stage)
            data = RecruitmentStageResponse.model_validate(stage).model_dump(mode='json')
            return JsonResponse(data)

        elif request.method == 'DELETE':
            db.delete(stage)
            db.commit()
            return HttpResponse(status=204)

        return JsonResponse({"detail": "Method not allowed"}, status=405)
    finally:
        db.close()


# ─── Email ──────────────────────────────────────────────────────────────────

@csrf_exempt
def email_generate(request):
    """Generate templated email for candidate."""
    if request.method != 'POST':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    body = _json_body(request)
    candidate_id = body.get("candidate_id")
    template_type = body.get("template_type", "interview_invitation")
    custom_data = body.get("custom_data")

    if not candidate_id:
        return JsonResponse({"detail": "Missing candidate_id"}, status=400)

    db = _get_db()
    try:
        candidate = db.query(Candidate).options(
            joinedload(Candidate.job_description), joinedload(Candidate.resume)
        ).filter(Candidate.id == candidate_id).first()

        if not candidate:
            return JsonResponse({"detail": "Candidate not found"}, status=404)

        candidate_name = candidate.resume.candidate_name if candidate.resume else "Candidate"
        position = candidate.job_description.title if candidate.job_description else "Open Position"

        latest_stage = db.query(RecruitmentStage).filter(
            RecruitmentStage.candidate_id == candidate.id
        ).order_by(RecruitmentStage.created_at.desc()).first()
        stage_name = latest_stage.stage if latest_stage else ""
        scheduled = str(latest_stage.scheduled_date) if latest_stage and latest_stage.scheduled_date else None

        result = generate_email(
            candidate_id=candidate_id,
            template_type=template_type,
            custom_data=custom_data,
            candidate_name=candidate_name,
            position=position,
            stage=stage_name,
            scheduled_date=scheduled,
        )

        return JsonResponse({"subject": result["subject"], "body": result["body"]})
    finally:
        db.close()


@csrf_exempt
def email_send(request):
    """Generate and send templated email to candidate."""
    if request.method != 'POST':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    body = _json_body(request)
    candidate_id = body.get("candidate_id")
    template_type = body.get("template_type", "interview_invitation")
    custom_data = body.get("custom_data")

    if not candidate_id:
        return JsonResponse({"detail": "Missing candidate_id"}, status=400)

    db = _get_db()
    try:
        candidate = db.query(Candidate).options(
            joinedload(Candidate.job_description), joinedload(Candidate.resume)
        ).filter(Candidate.id == candidate_id).first()

        if not candidate:
            return JsonResponse({"detail": "Candidate not found"}, status=404)

        candidate_name = candidate.resume.candidate_name if candidate.resume else "Candidate"
        position = candidate.job_description.title if candidate.job_description else "Open Position"

        latest_stage = db.query(RecruitmentStage).filter(
            RecruitmentStage.candidate_id == candidate.id
        ).order_by(RecruitmentStage.created_at.desc()).first()
        stage_name = latest_stage.stage if latest_stage else ""
        scheduled = str(latest_stage.scheduled_date) if latest_stage and latest_stage.scheduled_date else None

        result = generate_email(
            candidate_id=candidate_id,
            template_type=template_type,
            custom_data=custom_data,
            candidate_name=candidate_name,
            position=position,
            stage=stage_name,
            scheduled_date=scheduled,
        )

        to_email = candidate.resume.email if candidate.resume else "candidate@example.com"
        send_result = send_email_notification(
            to_email=to_email,
            subject=result["subject"],
            body=result["body"]
        )

        if send_result.get("success"):
            candidate.email_status = "Sent"
            candidate.email_error_reason = None
            db.commit()
            return JsonResponse({"success": True, "message": f"Email successfully sent to {to_email}"})
        else:
            candidate.email_status = "Failed"
            candidate.email_error_reason = send_result.get("error", "Unknown sending error")
            db.commit()
            return JsonResponse({"success": False, "error": candidate.email_error_reason})
    finally:
        db.close()


# ─── Interview Questions ────────────────────────────────────────────────────

@csrf_exempt
def interview_questions(request, candidate_id: int):
    """Generate interview questions for candidate."""
    if request.method != 'POST':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    db = _get_db()
    try:
        candidate = db.query(Candidate).options(
            joinedload(Candidate.resume), joinedload(Candidate.job_description)
        ).filter(Candidate.id == candidate_id).first()

        if not candidate:
            return JsonResponse({"detail": "Candidate not found"}, status=404)
        if not candidate.resume or not candidate.resume.raw_text:
            return JsonResponse({"detail": "Resume raw text not available"}, status=400)
        if not candidate.job_description:
            return JsonResponse({"detail": "Job description not available"}, status=400)

        jd_text = (
            f"{candidate.job_description.title}\n"
            f"{candidate.job_description.description}\n"
            f"{candidate.job_description.required_skills or ''}"
        )

        questions = generate_interview_questions(
            resume_text=candidate.resume.raw_text,
            jd_text=jd_text,
            count=5,
        )

        candidate.interview_questions = "\n".join(questions)
        db.commit()

        return JsonResponse({"questions": questions})
    finally:
        db.close()


# ─── Meetings ───────────────────────────────────────────────────────────────

@csrf_exempt
def meetings_by_candidate(request, candidate_id: int):
    """List or schedule meetings for candidate."""
    db = _get_db()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return JsonResponse({"detail": "Candidate not found"}, status=404)

        if request.method == 'GET':
            meetings = db.query(Meeting).filter(
                Meeting.candidate_id == candidate_id
            ).order_by(Meeting.scheduled_at.asc()).all()
            data = [MeetingResponse.model_validate(m).model_dump(mode='json') for m in meetings]
            return JsonResponse(data, safe=False)

        elif request.method == 'POST':
            body = _json_body(request)
            scheduled_at = body.get("scheduled_at")
            if scheduled_at and isinstance(scheduled_at, str):
                try:
                    scheduled_at = datetime.fromisoformat(scheduled_at)
                except Exception:
                    pass

            meeting = Meeting(
                candidate_id=candidate_id,
                title=body.get("title", "Interview"),
                meeting_link=body.get("meeting_link"),
                scheduled_at=scheduled_at,
                duration_minutes=body.get("duration_minutes", 45),
                attendees=body.get("attendees"),
                notes=body.get("notes"),
            )
            db.add(meeting)
            db.commit()
            db.refresh(meeting)

            data = MeetingResponse.model_validate(meeting).model_dump(mode='json')
            return JsonResponse(data, status=201)

        return JsonResponse({"detail": "Method not allowed"}, status=405)
    finally:
        db.close()


@csrf_exempt
def meeting_detail(request, meeting_id: int):
    """Update or delete a scheduled meeting."""
    db = _get_db()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return JsonResponse({"detail": "Meeting not found"}, status=404)

        if request.method in ('PUT', 'PATCH'):
            body = _json_body(request)
            for k, v in body.items():
                if hasattr(meeting, k) and v is not None:
                    if k == 'scheduled_at' and isinstance(v, str):
                        try:
                            v = datetime.fromisoformat(v)
                        except Exception:
                            pass
                    setattr(meeting, k, v)

            db.commit()
            db.refresh(meeting)
            data = MeetingResponse.model_validate(meeting).model_dump(mode='json')
            return JsonResponse(data)

        elif request.method == 'DELETE':
            db.delete(meeting)
            db.commit()
            return HttpResponse(status=204)

        return JsonResponse({"detail": "Method not allowed"}, status=405)
    finally:
        db.close()


# ─── AI Agent ───────────────────────────────────────────────────────────────

@csrf_exempt
def agent_execute_view(request):
    """Execute AI agent natural language instruction."""
    if request.method != 'POST':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    body = _json_body(request)
    instruction = body.get("instruction", "").strip()
    if not instruction:
        return JsonResponse({"detail": "Missing instruction"}, status=400)

    db = _get_db()
    try:
        result = execute_agent(instruction, db)
        return JsonResponse({
            "success": result.get("success", True),
            "summary": result.get("summary", ""),
            "actions": result.get("actions", []),
            "iterations": result.get("iterations", 0),
        })
    except Exception as e:
        return JsonResponse({"detail": f"Agent execution failed: {str(e)}"}, status=500)
    finally:
        db.close()


@csrf_exempt
def agent_pipeline_view(request, jd_id: int):
    """Run recruitment pipeline for a JD."""
    if request.method != 'POST':
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    db = _get_db()
    try:
        result = execute_pipeline(jd_id, db)
        return JsonResponse({
            "success": result.get("success", True),
            "jd_id": jd_id,
            "summary": result.get("summary"),
            "steps": result.get("steps", []),
            "error": result.get("error"),
        })
    except ValueError as e:
        return JsonResponse({"detail": str(e)}, status=404)
    except Exception as e:
        return JsonResponse({"detail": f"Pipeline execution failed: {str(e)}"}, status=500)
    finally:
        db.close()


def agent_tools_view(request):
    """List available AI Agent tools."""
    tools_summary = []
    for tool in AGENT_TOOLS:
        func = tool.get("function", tool)
        tools_summary.append({
            "name": func["name"],
            "description": func["description"],
            "parameters": list(func.get("parameters", {}).get("properties", {}).keys()),
        })
    return JsonResponse({"total_tools": len(tools_summary), "tools": tools_summary})


# ─── Celery Task Status ─────────────────────────────────────────────────────

def celery_task_status(request, task_id: str):
    """Query background Celery task status."""
    from celery.result import AsyncResult
    result = AsyncResult(task_id)
    response_data = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "result": result.result if result.ready() else None,
    }
    return JsonResponse(response_data)
