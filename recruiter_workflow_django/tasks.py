import logging
from celery import shared_task
from recruiter_workflow.database import SessionLocal

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="recruiter_workflow.tasks.rank_resumes")
def task_rank_resumes_for_jd(self, jd_id: int):
    """Asynchronous Celery task to rank candidate resumes for a given Job Description."""
    from recruiter_workflow.services.ranking_service import rank_resumes_for_jd
    db = SessionLocal()
    try:
        logger.info(f"Celery worker running rank_resumes_for_jd for JD {jd_id}")
        results = rank_resumes_for_jd(db, jd_id)
        return {"success": True, "jd_id": jd_id, "ranked_count": len(results)}
    except Exception as e:
        logger.error(f"Error in task_rank_resumes_for_jd: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task(bind=True, name="recruiter_workflow.tasks.run_candidate_workflow")
def task_run_candidate_workflow(self, candidate_id: int):
    """Asynchronous Celery task to execute autonomous AI pipeline for candidate."""
    from recruiter_workflow.services.pipeline_service import run_candidate_workflow
    db = SessionLocal()
    try:
        logger.info(f"Celery worker executing run_candidate_workflow for candidate {candidate_id}")
        run_candidate_workflow(db, candidate_id)
        return {"success": True, "candidate_id": candidate_id}
    except Exception as e:
        logger.error(f"Error in task_run_candidate_workflow: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task(bind=True, name="recruiter_workflow.tasks.send_email_notification")
def task_send_email_notification(self, to_email: str, subject: str, body: str):
    """Asynchronous Celery task to send email via SMTP."""
    from recruiter_workflow.services.email_service import send_email_notification
    try:
        logger.info(f"Celery worker sending email to {to_email}")
        res = send_email_notification(to_email, subject, body)
        return res
    except Exception as e:
        logger.error(f"Error in task_send_email_notification: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@shared_task(bind=True, name="recruiter_workflow.tasks.execute_agent_instruction")
def task_execute_agent_instruction(self, instruction: str):
    """Asynchronous Celery task to run agent instruction."""
    from recruiter_workflow.services.agent_service import execute_agent
    db = SessionLocal()
    try:
        logger.info(f"Celery worker running agent instruction: {instruction}")
        res = execute_agent(instruction, db)
        return res
    except Exception as e:
        logger.error(f"Error in task_execute_agent_instruction: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        db.close()
