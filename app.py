"""Entry point for the Recruiter Workflow Fragmentation API.

Run with::

    uvicorn app:app --reload
"""

import uvicorn
from recruiter_workflow.main import app

if __name__ == "__main__":
    uvicorn.run(
        "recruiter_workflow.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
