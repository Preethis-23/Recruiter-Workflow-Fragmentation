"""Agent router — API endpoints for the Recruiter AI Agent.

Provides:
- POST /api/agent/execute — Send natural language instructions to the agent
- POST /api/agent/pipeline/{jd_id} — Run a full recruitment pipeline
- GET  /api/agent/tools — List available agent tools
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from recruiter_workflow.database import get_db
from recruiter_workflow.services.agent_service import execute_agent, execute_pipeline, AGENT_TOOLS

router = APIRouter(prefix="/api/agent", tags=["AI Agent"])


class AgentRequest(BaseModel):
    """Request body for the agent execution endpoint."""
    instruction: str = Field(
        ...,
        min_length=3,
        description="Natural language instruction for the agent",
        json_schema_extra={
            "examples": [
                "List all job descriptions",
                "Rank all resumes against job description ID 1",
                "Generate interview questions for candidate ID 3",
                "Create a job description for a Senior Python Developer in the Engineering department",
                "Send an interview scheduling email for candidate ID 2",
            ]
        },
    )


class AgentResponse(BaseModel):
    """Response from the agent execution."""
    success: bool
    summary: str
    actions: list[dict] = []
    iterations: int = 0


class PipelineResponse(BaseModel):
    """Response from the pipeline execution."""
    success: bool
    jd_id: int
    summary: Optional[str] = None
    steps: list[dict] = []
    error: Optional[str] = None


@router.post("/execute", response_model=AgentResponse)
def agent_execute(payload: AgentRequest, db: Session = Depends(get_db)):
    """Execute a natural language instruction using the AI recruitment agent.
    
    The agent will:
    1. Understand your instruction
    2. Plan the necessary tool calls
    3. Execute them autonomously
    4. Return a summary of what was accomplished
    
    **Examples:**
    - "List all job descriptions"
    - "Rank candidates against JD #1 and summarize the top 3"
    - "Create a Software Engineer job description for the backend team"
    - "Generate interview questions for candidate #5"
    - "Send a rejection email to candidate #7"
    """
    try:
        result = execute_agent(payload.instruction, db)
        return AgentResponse(
            success=result.get("success", True),
            summary=result.get("summary", ""),
            actions=result.get("actions", []),
            iterations=result.get("iterations", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


@router.post("/pipeline/{jd_id}", response_model=PipelineResponse)
def run_pipeline(jd_id: int, db: Session = Depends(get_db)):
    """Run a complete recruitment pipeline for a job description.
    
    This automates the full workflow:
    1. **Rank** all resumes against the JD
    2. **Summarize** top candidates with AI
    3. **Generate** tailored interview questions
    4. **Create** screening stages in the pipeline
    5. **Draft** interview scheduling emails
    
    This is a pre-built workflow for common recruitment tasks.
    """
    try:
        result = execute_pipeline(jd_id, db)
        return PipelineResponse(
            success=result.get("success", True),
            jd_id=jd_id,
            summary=result.get("summary"),
            steps=result.get("steps", []),
            error=result.get("error"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


@router.get("/tools")
def list_tools():
    """List all tools available to the AI recruitment agent.
    
    These are the actions the agent can take when processing instructions.
    """
    tools_summary = []
    for tool in AGENT_TOOLS:
        func = tool.get("function", tool)
        tools_summary.append({
            "name": func["name"],
            "description": func["description"],
            "parameters": list(func.get("parameters", {}).get("properties", {}).keys()),
        })
    
    return {
        "total_tools": len(tools_summary),
        "tools": tools_summary,
    }
