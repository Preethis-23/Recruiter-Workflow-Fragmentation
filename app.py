"""Entry point for the Recruiter Workflow Fragmentation Application.

Run the Django server with:
    python manage.py runserver 0.0.0.0:8000
    or
    python app.py

Run Celery background workers with:
    celery -A recruiter_project worker -l info
"""

import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "recruiter_project.settings")
    from django.core.management import execute_from_command_line
    if len(sys.argv) == 1:
        execute_from_command_line(["manage.py", "runserver", "0.0.0.0:8000"])
    else:
        execute_from_command_line(sys.argv)
