import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recruiter_project.settings')

app = Celery('recruiter_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(['recruiter_workflow_django'])

# Explicitly import tasks to ensure registration
import recruiter_workflow_django.tasks  # noqa: F401, E402


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
