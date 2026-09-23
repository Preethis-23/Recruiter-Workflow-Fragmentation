"""Recruiter Agent — Agentic AI for autonomous recruitment workflow execution.

The agent receives a natural language instruction, plans a sequence of tool calls,
and executes them autonomously to complete recruitment tasks.

Supported tools:
- parse_resume: Extract structured data from a resume file
- create_job_description: Create a new JD
- list_job_descriptions: Get all JDs
- rank_candidates: Score all resumes against a JD
- get_ranked_candidates: Get ranked results for a JD
- generate_candidate_summary: AI summary for a candidate
- generate_interview_questions: Tailored interview questions
- generate_email: Draft recruitment emails
- update_candidate_status: Move candidate through pipeline
- create_recruitment_stage: Add pipeline stage for candidate
- list_candidates: Query candidates with filters
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from recruiter_workflow.config import settings
from recruiter_workflow.models import Candidate, JobDescription, Resume, RecruitmentStage
from recruiter_workflow.services.llm_service import _call_llm, call_llm_with_tools
from recruiter_workflow.services.ranking_service import rank_resumes_for_jd, get_ranked_candidates
from recruiter_workflow.services.parser_service import extract_text, parse_resume_sections
from recruiter_workflow.services.email_service import generate_email
from recruiter_workflow.services.embedding_service import compute_similarity

logger = logging.getLogger(__name__)


# ─── Tool Definitions (for LLM tool-calling) ────────────────────────────────

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_job_description",
            "description": "Create a new job description in the database",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Job title"},
                    "description": {"type": "string", "description": "Full job description text"},
                    "department": {"type": "string", "description": "Department name"},
                    "location": {"type": "string", "description": "Job location"},
                    "employment_type": {"type": "string", "description": "e.g., Full-time, Part-time, Contract"},
                    "required_skills": {"type": "string", "description": "Comma-separated required skills"},
                    "min_experience": {"type": "integer", "description": "Minimum years of experience"},
                    "max_experience": {"type": "integer", "description": "Maximum years of experience"},
                },
                "required": ["title", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_job_descriptions",
            "description": "List all job descriptions currently in the system",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "parse_resume",
            "description": "Parse a resume file (PDF or DOCX) and store structured data",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the resume file (.pdf or .docx)"},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_resumes",
            "description": "List all parsed resumes in the system",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rank_candidates_for_jd",
            "description": "Rank all resumes against a specific job description using similarity scoring",
            "parameters": {
                "type": "object",
                "properties": {
                    "jd_id": {"type": "integer", "description": "Job description ID to rank against"},
                },
                "required": ["jd_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_and_email_candidates",
            "description": "Schedule Google Calendar technical interviews and send automated email invitations to a list of candidate IDs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of candidate IDs to schedule and email"
                    }
                },
                "required": ["candidate_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ranked_candidates",
            "description": "Get the ranked list of candidates for a job description",
            "parameters": {
                "type": "object",
                "properties": {
                    "jd_id": {"type": "integer", "description": "Job description ID"},
                },
                "required": ["jd_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_candidate_summary",
            "description": "Generate an AI-powered summary comparing a candidate's resume to the JD",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "integer", "description": "Candidate ID"},
                },
                "required": ["candidate_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_interview_questions",
            "description": "Generate tailored interview questions for a candidate based on their resume and JD",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "integer", "description": "Candidate ID"},
                    "count": {"type": "integer", "description": "Number of questions to generate (default: 5)"},
                },
                "required": ["candidate_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_email",
            "description": "Generate a recruitment email for a candidate (interview scheduling, offer, rejection, or follow-up)",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "integer", "description": "Candidate ID"},
                    "template_type": {
                        "type": "string",
                        "enum": ["interview_scheduling", "offer", "rejection", "follow_up"],
                        "description": "Type of email to generate",
                    },
                },
                "required": ["candidate_id", "template_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_candidate_status",
            "description": "Update a candidate's recruitment status",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "integer", "description": "Candidate ID"},
                    "status": {
                        "type": "string",
                        "enum": ["New", "Screening", "Interview", "Offer", "Hired", "Rejected"],
                        "description": "New status",
                    },
                },
                "required": ["candidate_id", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_recruitment_stage",
            "description": "Create a new recruitment pipeline stage for a candidate",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "integer", "description": "Candidate ID"},
                    "stage": {
                        "type": "string",
                        "enum": ["Screening", "Phone Interview", "Technical Interview", "HR Interview", "Assignment", "Final Round", "Offer", "Hired", "Rejected"],
                        "description": "Stage type",
                    },
                    "notes": {"type": "string", "description": "Optional notes for this stage"},
                },
                "required": ["candidate_id", "stage"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_candidates",
            "description": "List candidates, optionally filtered by job description or status",
            "parameters": {
                "type": "object",
                "properties": {
                    "jd_id": {"type": "integer", "description": "Filter by job description ID"},
                    "status": {"type": "string", "description": "Filter by status"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_candidate",
            "description": "Run the entire autonomous recruitment workflow for a candidate (ranking, explanation, summary, questions, scheduling, and email)",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "integer", "description": "Candidate ID to process"},
                },
                "required": ["candidate_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hire_for_role",
            "description": "Execute a COMPLETE autonomous hiring workflow from scratch. Creates a job description, searches all existing resumes in the database, ranks candidates by AI similarity, generates summaries and interview questions for top candidates, schedules interviews, and sends emails. Use this when the user says 'hire', 'recruit', 'find candidates for', or describes a role to fill.",
            "parameters": {
                "type": "object",
                "properties": {
                    "role_title": {"type": "string", "description": "The job title to hire for, e.g. 'Python ML Engineer'"},
                    "department": {"type": "string", "description": "Department name, e.g. 'Engineering'"},
                    "location": {"type": "string", "description": "Job location, e.g. 'Remote'"},
                    "required_skills": {"type": "string", "description": "Comma-separated skills, e.g. 'Python, Machine Learning, TensorFlow'"},
                    "min_experience": {"type": "integer", "description": "Minimum years of experience"},
                    "top_n": {"type": "integer", "description": "Number of top candidates to fully process (default: 5)"}
                },
                "required": ["role_title"],
            },
        },
    },
]


# ─── Tool Execution ──────────────────────────────────────────────────────────

def _execute_tool(tool_name: str, arguments: dict, db: Session) -> dict:
    """Execute a tool by name with given arguments. Returns result dict."""
    logger.info(f"Agent executing tool: {tool_name}({arguments})")
    
    try:
        if tool_name == "create_job_description":
            title = arguments.get("title", "")
            existing = db.query(JobDescription).filter(JobDescription.title.ilike(title)).first() if title else None
            if existing:
                return {"success": True, "jd_id": existing.id, "title": existing.title, "reused": True}
            jd = JobDescription(**arguments)
            db.add(jd)
            db.commit()
            db.refresh(jd)
            return {"success": True, "jd_id": jd.id, "title": jd.title}
        
        elif tool_name == "list_job_descriptions":
            jds = db.query(JobDescription).order_by(JobDescription.created_at.desc()).all()
            return {
                "success": True,
                "count": len(jds),
                "job_descriptions": [
                    {"id": jd.id, "title": jd.title, "department": jd.department}
                    for jd in jds
                ],
            }
        
        elif tool_name == "parse_resume":
            file_path = arguments["file_path"]
            # Check for duplicate
            existing = db.query(Resume).filter(Resume.file_path == file_path).first()
            if existing:
                return {"success": True, "resume_id": existing.id, "note": "Resume already parsed", "candidate_name": existing.candidate_name}
            
            raw_text = extract_text(file_path)
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
            return {
                "success": True,
                "resume_id": resume.id,
                "candidate_name": resume.candidate_name,
                "email": resume.email,
                "skills": resume.skills,
            }
        
        elif tool_name == "list_resumes":
            resumes = db.query(Resume).order_by(Resume.parsed_at.desc()).all()
            return {
                "success": True,
                "count": len(resumes),
                "resumes": [
                    {"id": r.id, "candidate_name": r.candidate_name, "email": r.email, "skills": (r.skills or "")[:100]}
                    for r in resumes
                ],
            }
        
        elif tool_name == "rank_candidates_for_jd":
            jd_id = arguments["jd_id"]
            results = rank_resumes_for_jd(db, jd_id)
            return {"success": True, "ranked_count": len(results), "results": results[:10]}
        
        elif tool_name == "get_ranked_candidates":
            jd_id = arguments["jd_id"]
            results = get_ranked_candidates(db, jd_id)
            return {"success": True, "count": len(results), "candidates": results[:10]}
        
        elif tool_name == "generate_candidate_summary":
            candidate_id = arguments["candidate_id"]
            candidate = (
                db.query(Candidate)
                .options(joinedload(Candidate.resume), joinedload(Candidate.job_description))
                .filter(Candidate.id == candidate_id)
                .first()
            )
            if not candidate:
                return {"success": False, "error": f"Candidate {candidate_id} not found"}
            if not candidate.resume or not candidate.resume.raw_text:
                return {"success": False, "error": "Resume text not available"}
            if not candidate.job_description:
                return {"success": False, "error": "Job description not linked"}
            
            from recruiter_workflow.services.llm_service import generate_summary
            jd_text = f"{candidate.job_description.title}\n{candidate.job_description.description}\n{candidate.job_description.required_skills or ''}"
            summary = generate_summary(candidate.resume.raw_text, jd_text)
            candidate.summary = summary
            db.commit()
            return {"success": True, "candidate_id": candidate_id, "summary": summary}
        
        elif tool_name == "generate_interview_questions":
            try:
                candidate_id = int(arguments["candidate_id"])
                count = int(arguments.get("count", 5))
            except (ValueError, TypeError):
                return {"success": False, "error": "candidate_id and count must be integers"}
                
            candidate = (
                db.query(Candidate)
                .options(joinedload(Candidate.resume), joinedload(Candidate.job_description))
                .filter(Candidate.id == candidate_id)
                .first()
            )
            if not candidate:
                return {"success": False, "error": f"Candidate {candidate_id} not found"}
            if not candidate.resume or not candidate.resume.raw_text:
                return {"success": False, "error": "Resume text not available"}
            if not candidate.job_description:
                return {"success": False, "error": "Job description not linked"}
            
            from recruiter_workflow.services.llm_service import generate_interview_questions as gen_questions
            jd_text = f"{candidate.job_description.title}\n{candidate.job_description.description}\n{candidate.job_description.required_skills or ''}"
            questions = gen_questions(candidate.resume.raw_text, jd_text, count=count)
            return {"success": True, "candidate_id": candidate_id, "questions": questions}
        
        elif tool_name == "generate_email":
            candidate_id = arguments["candidate_id"]
            template_type = arguments["template_type"]
            
            candidate = (
                db.query(Candidate)
                .options(joinedload(Candidate.job_description), joinedload(Candidate.resume))
                .filter(Candidate.id == candidate_id)
                .first()
            )
            if not candidate:
                return {"success": False, "error": f"Candidate {candidate_id} not found"}
            
            candidate_name = candidate.resume.candidate_name if candidate.resume else "Candidate"
            position = candidate.job_description.title if candidate.job_description else "Open Position"
            
            latest_stage = (
                db.query(RecruitmentStage)
                .filter(RecruitmentStage.candidate_id == candidate.id)
                .order_by(RecruitmentStage.created_at.desc())
                .first()
            )
            
            result = generate_email(
                candidate_id=candidate_id,
                template_type=template_type,
                candidate_name=candidate_name,
                position=position,
                stage=latest_stage.stage if latest_stage else "",
                scheduled_date=str(latest_stage.scheduled_date) if latest_stage and latest_stage.scheduled_date else None,
            )
            return {"success": True, **result}
        
        elif tool_name == "update_candidate_status":
            candidate_id = arguments["candidate_id"]
            new_status = arguments["status"]
            candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            if not candidate:
                return {"success": False, "error": f"Candidate {candidate_id} not found"}
            candidate.status = new_status
            db.commit()
            return {"success": True, "candidate_id": candidate_id, "new_status": new_status}
        
        elif tool_name == "create_recruitment_stage":
            candidate_id = arguments["candidate_id"]
            stage_name = arguments["stage"]
            notes = arguments.get("notes")
            
            candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            if not candidate:
                return {"success": False, "error": f"Candidate {candidate_id} not found"}
            
            stage = RecruitmentStage(
                candidate_id=candidate_id,
                stage=stage_name,
                notes=notes,
            )
            db.add(stage)
            db.commit()
            db.refresh(stage)
            return {"success": True, "stage_id": stage.id, "stage": stage_name, "candidate_id": candidate_id}
        
        elif tool_name == "list_candidates":
            query = db.query(Candidate).options(joinedload(Candidate.resume))
            if "jd_id" in arguments and arguments["jd_id"]:
                query = query.filter(Candidate.jd_id == arguments["jd_id"])
            if "status" in arguments and arguments["status"]:
                query = query.filter(Candidate.status == arguments["status"])
            candidates = query.order_by(Candidate.created_at.desc()).all()
            return {
                "success": True,
                "count": len(candidates),
                "candidates": [
                    {
                        "id": c.id,
                        "jd_id": c.jd_id,
                        "candidate_name": c.resume.candidate_name if c.resume else None,
                        "similarity_score": round(c.similarity_score, 4) if c.similarity_score else None,
                        "status": c.status,
                    }
                    for c in candidates[:20]
                ],
            }
        
        elif tool_name == "process_candidate":
            try:
                candidate_id = int(arguments["candidate_id"])
            except (ValueError, TypeError):
                return {"success": False, "error": "candidate_id must be an integer"}
            
            from recruiter_workflow.services.pipeline_service import run_candidate_workflow
            return run_candidate_workflow(db, candidate_id)
        
        elif tool_name == "hire_for_role":
            return _execute_hire_workflow(arguments, db)
            
        elif tool_name == "schedule_and_email_candidates":
            candidate_ids = arguments.get("candidate_ids", [])
            from recruiter_workflow.services.pipeline_service import schedule_and_email_candidate
            results = []
            for cid in candidate_ids:
                res = schedule_and_email_candidate(db, cid)
                results.append(res)
            return {"success": True, "results": results}
        
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ─── Agent Execution Engine ──────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an autonomous AI recruitment agent. You execute complete hiring workflows independently without asking for confirmation.

CRITICAL RULES:
1. When someone says "hire", "recruit", "find candidates for", "I need a", or describes ANY role to fill → ALWAYS use the `hire_for_role` tool. This is your PRIMARY tool.
2. The `hire_for_role` tool will short-list candidates and prepare summaries. IT WILL NOT SCHEDULE OR SEND EMAILS. You MUST display the shortlisted candidates to the user and explicitly ASK FOR CONFIRMATION via chat ("Should I go ahead and schedule interviews and send outreach emails to these candidates?").
3. ONLY AFTER the user confirms via chat, you will use the `schedule_and_email_candidates` tool.
4. When asked to "process a candidate" or "run pipeline" for a specific candidate ID → use `process_candidate`.
5. Chain multiple tools autonomously if needed, except for scheduling/emailing which requires explicit chat confirmation.

Your capabilities:
- `hire_for_role` — Autonomous workflow: create JD → search resumes → rank → summarize → interview questions (STOPS HERE)
- `schedule_and_email_candidates` — Schedules calendar invites and sends emails (REQUIRES CHAT CONFIRMATION)
- `process_candidate` — Process a single candidate through the full pipeline
- `create_job_description` — Create a new job description
- `rank_candidates_for_jd` — Rank all resumes against a JD
- `generate_candidate_summary` — AI summary for a candidate
- `generate_interview_questions` — Tailored interview questions
- `generate_email` — Draft recruitment emails
- `update_candidate_status` — Move candidate through pipeline
- `list_job_descriptions`, `list_resumes`, `list_candidates` — Query data

You are an AGENTIC system. You decide what to do, execute it, and report results."""


def execute_agent(instruction: str, db: Session) -> dict:
    """Execute an agentic workflow from a natural language instruction.
    
    The agent will:
    1. Understand the instruction
    2. Plan tool calls
    3. Execute tools iteratively
    4. Return a summary with all actions taken
    
    Returns dict with 'summary', 'actions', and 'success'.
    """
    logger.info(f"Agent received instruction: {instruction}")
    
    actions_log: list[dict] = []
    max_iterations = settings.AGENT_MAX_ITERATIONS
    
    # Build conversation context
    conversation = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": instruction},
    ]
    
    for iteration in range(max_iterations):
        logger.info(f"Agent iteration {iteration + 1}/{max_iterations}")
        
        # Call LLM with tools
        response = call_llm_with_tools(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=_build_context(instruction, actions_log, iteration),
            tools=AGENT_TOOLS,
            temperature=0.1,
        )
        
        tool_calls = response.get("tool_calls", [])
        content = response.get("content", "")
        
        # If no tool calls, the agent is done reasoning
        if not tool_calls:
            logger.info(f"Agent completed after {iteration + 1} iterations")
            
            # If we have no actions and no content, provide a helpful response
            if not actions_log and not content:
                content = _generate_fallback_response(instruction, db)
            
            return {
                "success": True,
                "summary": content or "Task completed successfully.",
                "actions": actions_log,
                "iterations": iteration + 1,
            }
        
        # Execute each tool call
        for tc in tool_calls:
            tool_name = tc["name"]
            arguments = tc["arguments"]
            
            result = _execute_tool(tool_name, arguments, db)
            
            action_entry = {
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
                "iteration": iteration + 1,
                "timestamp": datetime.utcnow().isoformat(),
            }
            actions_log.append(action_entry)
            
            if settings.AGENT_VERBOSE:
                logger.info(f"  Tool: {tool_name} -> success={result.get('success', False)}")
    
    # Max iterations reached
    logger.warning(f"Agent hit max iterations ({max_iterations})")
    
    # Generate final summary
    summary = _call_llm(
        system_prompt="Summarize what was accomplished in these recruitment actions.",
        user_prompt=json.dumps(actions_log, default=str)[:3000],
        max_tokens=300,
    )
    
    return {
        "success": True,
        "summary": summary or "Agent completed the maximum number of iterations.",
        "actions": actions_log,
        "iterations": max_iterations,
    }


def _build_context(instruction: str, actions_log: list[dict], iteration: int) -> str:
    """Build the prompt context including past actions for the current iteration."""
    if iteration == 0:
        return instruction
    
    context_parts = [
        f"Original instruction: {instruction}\n",
        "Actions completed so far:\n",
    ]
    
    for action in actions_log:
        result_summary = json.dumps(action["result"], default=str)[:200]
        context_parts.append(f"  - {action['tool']}({action['arguments']}) → {result_summary}")
    
    context_parts.append("\nContinue with the next step, or if all steps are done, provide a final summary without calling any tools.")
    
    return "\n".join(context_parts)


def _generate_fallback_response(instruction: str, db: Session) -> str:
    """Generate a helpful response when the LLM doesn't call any tools.
    
    This handles cases where the LLM model doesn't support tool calling
    or decides to answer directly.
    """
    # Try to understand the instruction and execute manually
    lower = instruction.lower()
    
    results = []
    
    import re
    
    # ── Hire / Recruit detection (HIGHEST PRIORITY) ──
    hire_keywords = ["hire", "recruit", "find candidates for", "i need a", "looking for", "search for", "fill the role", "open a position", "start hiring"]
    if any(kw in lower for kw in hire_keywords):
        # Extract the role title from the instruction
        role_title = instruction.strip()
        # Try to clean common prefixes
        for prefix in ["hire a", "hire an", "recruit a", "recruit an", "find candidates for", "find candidates for a", "i need a", "i need an", "looking for a", "looking for an", "search for a", "search for an"]:
            if lower.startswith(prefix):
                role_title = instruction[len(prefix):].strip()
                break
        
        workflow_result = _execute_hire_workflow({"role_title": role_title}, db)
        if workflow_result.get("success"):
            results.append(f"✅ Autonomous hiring workflow completed for: {role_title}")
            results.append(f"")
            results.append(f"📋 JD Created: ID #{workflow_result.get('jd_id')} — {workflow_result.get('jd_title')}")
            results.append(f"👥 Candidates Found: {workflow_result.get('total_candidates', 0)}")
            results.append(f"🏆 Top Candidates Processed: {workflow_result.get('processed_count', 0)}")
            results.append(f"")
            for step in workflow_result.get("steps", []):
                icon = "✅" if step.get("status") == "success" else "❌"
                results.append(f"  {icon} {step.get('step')}: {step.get('detail', '')}")
        else:
            results.append(f"❌ Hiring workflow failed: {workflow_result.get('error', 'Unknown error')}")
        return "\n".join(results)
    
    # ── Process candidate detection ──
    match = re.search(r"(?:process|run workflow|automate|run pipeline|pipeline)(?:\s+for|\s+on|\s+candidate)?(?:\s+id)?\s*#?\s*(\d+)", lower)
    if match:
        candidate_id = int(match.group(1))
        from recruiter_workflow.services.pipeline_service import run_candidate_workflow
        try:
            workflow_res = run_candidate_workflow(db, candidate_id)
            if workflow_res.get("success"):
                results.append(f"Successfully processed candidate ID {candidate_id} through the automated workflow:")
                results.append(f"  • Match Score: {int(workflow_res.get('similarity_score', 0) * 100)}%")
                results.append(f"  • Explanation: {workflow_res.get('explanation')}")
                results.append(f"  • Meeting Link: {workflow_res.get('meeting_link')}")
                results.append(f"  • Calendar Event ID: {workflow_res.get('calendar_event_id')}")
                results.append(f"  • Email Status: {workflow_res.get('email_status')}")
                if workflow_res.get("email_error_reason"):
                    results.append(f"  • Email Error: {workflow_res.get('email_error_reason')}")
            else:
                results.append(f"Failed to process candidate ID {candidate_id}: {workflow_res.get('error')}")
        except Exception as e:
            results.append(f"Error running automated workflow for candidate ID {candidate_id}: {e}")
            
    if any(kw in lower for kw in ["list jd", "show jd", "job description", "all jobs", "open position"]):
        jds = db.query(JobDescription).order_by(JobDescription.created_at.desc()).all()
        if jds:
            results.append(f"Found {len(jds)} job description(s):")
            for jd in jds:
                results.append(f"  • [ID:{jd.id}] {jd.title} — {jd.department or 'N/A'}")
        else:
            results.append("No job descriptions found. Create one first.")
    
    if any(kw in lower for kw in ["list resume", "show resume", "all resume", "parsed resume"]):
        resumes = db.query(Resume).order_by(Resume.parsed_at.desc()).all()
        if resumes:
            results.append(f"Found {len(resumes)} resume(s):")
            for r in resumes:
                results.append(f"  • [ID:{r.id}] {r.candidate_name or 'Unknown'} — {r.email or 'N/A'}")
        else:
            results.append("No resumes found. Upload and parse one first.")
    
    if any(kw in lower for kw in ["sorted candidate", "rank candidate", "list candidate", "show candidate", "all candidate", "top candidate"]):
        # Check if a specific JD or role is mentioned
        jds = db.query(JobDescription).all()
        target_jd = None
        for jd in jds:
            if jd.title.lower() in lower or str(jd.id) in lower:
                target_jd = jd
                break

        if target_jd:
            # Auto-rank if needed
            rank_resumes_for_jd(db, target_jd.id)
            candidates = db.query(Candidate).options(joinedload(Candidate.resume)).filter(Candidate.jd_id == target_jd.id).order_by(Candidate.similarity_score.desc().nulls_last()).all()
            results.append(f"🏆 Sorted Candidates for Role: '{target_jd.title}' (JD #{target_jd.id})")
            results.append(f"")
            for idx, c in enumerate(candidates, 1):
                name = c.resume.candidate_name if c.resume else "Unknown Candidate"
                email = c.resume.email if (c.resume and c.resume.email) else "No email"
                score_pct = int((c.similarity_score or 0) * 100)
                results.append(f"  #{idx} [ID:{c.id}] {name} ({email}) — Match Score: {score_pct}% | Status: {c.status}")
        else:
            candidates = db.query(Candidate).options(joinedload(Candidate.resume)).order_by(Candidate.similarity_score.desc().nulls_last()).all()
            if candidates:
                results.append(f"Found {len(candidates)} candidate(s) sorted by AI similarity score:")
                for c in candidates:
                    name = c.resume.candidate_name if c.resume else "Unknown Candidate"
                    email = c.resume.email if (c.resume and c.resume.email) else "No email"
                    score_pct = int((c.similarity_score or 0) * 100)
                    results.append(f"  • [ID:{c.id}] {name} ({email}) — Match Score: {score_pct}% | Status: {c.status}")
            else:
                results.append("No candidates found. Upload resumes and assign to a role first.")
    
    if results:
        return "\n".join(results)
    
    return (
        "I understood your instruction but couldn't determine the specific tools to call. "
        "Try being more specific, for example:\n"
        "  • 'Hire a Python ML Engineer'\n"
        "  • 'Show sorted candidates for Python ML Engineer'\n"
        "  • 'Rank all resumes against job description ID 1'\n"
        "  • 'Generate interview questions for candidate ID 3'\n"
        "  • 'Show me all candidates with status Interview'"
    )


# ─── Pipeline execution (pre-built workflow) ────────────────────────────────

def execute_pipeline(jd_id: int, db: Session) -> dict:
    """Execute a full autonomous recruitment pipeline for a job description.
    
    Steps:
    1. Rank all resumes against the JD
    2. Run candidate workflow automation (scoring, explanation, summary, questions, stages, calendar scheduling, email sending)
    
    Returns a comprehensive report.
    """
    logger.info(f"Running recruitment pipeline for JD #{jd_id}")
    
    pipeline_results = {
        "jd_id": jd_id,
        "steps": [],
        "success": True,
    }
    
    # Step 1: Rank candidates to make sure scores and mappings are ready
    try:
        ranking_result = _execute_tool("rank_candidates_for_jd", {"jd_id": jd_id}, db)
        pipeline_results["steps"].append({
            "step": "rank_candidates",
            "result": ranking_result,
        })
        
        if not ranking_result.get("success"):
            pipeline_results["success"] = False
            pipeline_results["error"] = ranking_result.get("error", "Ranking failed")
            return pipeline_results
    except Exception as e:
        pipeline_results["success"] = False
        pipeline_results["error"] = f"Ranking failed: {e}"
        return pipeline_results
    
    # Step 2: Get all candidates linked to this JD
    candidates = db.query(Candidate).filter(Candidate.jd_id == jd_id).all()
    
    pipeline_results["steps"].append({
        "step": "identify_candidates",
        "count": len(candidates),
        "candidates": [
            {"id": c.id, "name": c.resume.candidate_name if c.resume else None}
            for c in candidates
        ],
    })
    
    # Step 3: Run the complete autonomous candidate workflow for each candidate
    from recruiter_workflow.services.pipeline_service import run_candidate_workflow
    for candidate in candidates:
        try:
            workflow_res = run_candidate_workflow(db, candidate.id)
            pipeline_results["steps"].append({
                "step": f"workflow_candidate_{candidate.id}",
                "result": workflow_res,
            })
        except Exception as e:
            logger.error(f"Error executing automated workflow for candidate {candidate.id}: {e}", exc_info=True)
            pipeline_results["steps"].append({
                "step": f"workflow_candidate_{candidate.id}",
                "result": {"success": False, "error": str(e)},
            })
    
    # Generate final summary
    summary_text = _call_llm(
        system_prompt="Summarize this recruitment pipeline execution concisely.",
        user_prompt=f"Pipeline processed JD #{jd_id} with {len(candidates)} candidates. "
                     f"Steps executed: ranking, match explanation, summaries, interview questions, stage advancement, Google calendar scheduling, and automated interview emails.",
        max_tokens=200,
    )
    
    pipeline_results["summary"] = summary_text or (
        f"Pipeline completed: Ranked candidates for JD #{jd_id}, "
        f"fully automated candidate workflow processing for {len(candidates)} candidates, "
        f"updating their matches, summaries, questions, calendar events, and email invitations."
    )
    
    return pipeline_results


def _execute_hire_workflow(arguments: dict, db: Session) -> dict:
    """Core autonomous orchestrator for the 'hire_for_role' workflow."""
    role_title = arguments.get("role_title", "New Position")
    dept = arguments.get("department", "Engineering")
    req_skills = arguments.get("required_skills", "")
    top_n = arguments.get("top_n", 5)
    
    logger.info(f"Starting FULL autonomous hiring workflow for: {role_title}")
    
    result = {
        "success": True,
        "steps": [],
        "jd_id": None,
        "jd_title": role_title,
        "total_candidates": 0,
        "processed_count": 0
    }
    
    # 1. Create or Reuse JD
    try:
        existing_jd = db.query(JobDescription).filter(JobDescription.title.ilike(role_title)).first()
        if existing_jd:
            jd_id = existing_jd.id
            result["jd_id"] = jd_id
            result["steps"].append({"step": "Job Description", "status": "success", "detail": f"Reused existing JD #{jd_id} '{existing_jd.title}'"})
        else:
            desc_prompt = f"Write a professional 2-paragraph job description for a {role_title} in {dept}. Required skills: {req_skills}."
            description = _call_llm("You are an expert technical recruiter.", desc_prompt, max_tokens=300) or f"Job Description for {role_title}"
            
            jd = JobDescription(
                title=role_title,
                department=dept,
                description=description,
                required_skills=req_skills
            )
            db.add(jd)
            db.commit()
            db.refresh(jd)
            jd_id = jd.id
            result["jd_id"] = jd_id
            result["steps"].append({"step": "Create Job Description", "status": "success", "detail": f"Created JD #{jd_id} '{role_title}'"})
    except Exception as e:
        result["success"] = False
        result["error"] = f"Failed to create JD: {e}"
        return result
        
    # 2. Search all existing resumes and link to JD
    try:
        resumes = db.query(Resume).all()
        for r in resumes:
            existing_candidate = db.query(Candidate).filter(Candidate.jd_id == jd_id, Candidate.resume_id == r.id).first()
            if not existing_candidate:
                c = Candidate(jd_id=jd_id, resume_id=r.id)
                db.add(c)
        db.commit()
        result["total_candidates"] = len(resumes)
        result["steps"].append({"step": "Search Resumes", "status": "success", "detail": f"Found {len(resumes)} existing resumes in database."})
    except Exception as e:
        result["success"] = False
        result["error"] = f"Failed to link resumes: {e}"
        return result
        
    # 3. Rank Candidates
    try:
        from recruiter_workflow.services.ranking_service import rank_resumes_for_jd
        rank_resumes_for_jd(db, jd_id)
        result["steps"].append({"step": "AI Resume Ranking", "status": "success", "detail": "Ranked all candidates against JD."})
    except Exception as e:
        result["success"] = False
        result["error"] = f"Failed to rank resumes: {e}"
        return result
        
    # 4. Process Top N Candidates
    try:
        top_candidates = db.query(Candidate).filter(Candidate.jd_id == jd_id).order_by(Candidate.similarity_score.desc().nulls_last()).limit(top_n).all()
        from recruiter_workflow.services.pipeline_service import run_candidate_workflow
        
        for c in top_candidates:
            run_candidate_workflow(db, c.id)
            result["processed_count"] += 1
            
        result["steps"].append({"step": "Candidate Processing", "status": "success", "detail": f"Shortlisted {result['processed_count']} candidates (summaries & questions generated, status set to Screening)."})
    except Exception as e:
        result["success"] = False
        result["error"] = f"Failed to process candidates: {e}"
        return result
        
    return result
