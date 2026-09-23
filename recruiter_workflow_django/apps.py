import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class RecruiterWorkflowDjangoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recruiter_workflow_django'

    def ready(self):
        try:
            from recruiter_workflow.database import init_db
            init_db()
            logger.info("Recruiter Workflow database models initialized successfully.")
        except Exception as e:
            logger.warning(f"Database initialization deferred or encountered: {e}")
