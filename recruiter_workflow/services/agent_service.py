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
]


# ─── Tool Execution ──────────────────────────────────────────────────────────

def _execute_tool(tool_name: str, arguments: dict, db: Session) -> dict:
    """Execute a tool by name with given arguments. Returns result dict."""
    logger.info(f"Agent executing tool: {tool_name}({arguments})")
    
    try:
        if tool_name == "create_job_description":
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
        
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ─── Agent Execution Engine ──────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI recruitment assistant agent. You help recruiters automate their workflow by executing tasks using the available tools.

Your capabilities:
1. Create and manage job descriptions
2. Parse and analyze resumes
3. Rank candidates against job descriptions using AI similarity scoring
4. Generate AI-powered candidate summaries
5. Generate tailored interview questions
6. Draft recruitment emails (interview scheduling, offers, rejections, follow-ups)
7. Update candidate statuses and track recruitment pipeline stages

When given an instruction:
- Break it down into concrete steps
- Use the appropriate tools to complete each step
- Provide a clear summary of what you accomplished

Always think about what tools you need to call to fulfill the request. If you need data first (e.g., listing JDs to find an ID), call the appropriate tool first."""


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
    
    if any(kw in lower for kw in ["list candidate", "show candidate", "all candidate"]):
        candidates = db.query(Candidate).options(joinedload(Candidate.resume)).order_by(Candidate.created_at.desc()).all()
        if candidates:
            results.append(f"Found {len(candidates)} candidate(s):")
            for c in candidates:
                name = c.resume.candidate_name if c.resume else "Unknown"
                results.append(f"  • [ID:{c.id}] {name} — Status: {c.status}, Score: {c.similarity_score or 'N/A'}")
        else:
            results.append("No candidates found. Rank resumes against a JD first.")
    
    if results:
        return "\n".join(results)
    
    return (
        "I understood your instruction but couldn't determine the specific tools to call. "
        "Try being more specific, for example:\n"
        "  • 'List all job descriptions'\n"
        "  • 'Rank all resumes against job description ID 1'\n"
        "  • 'Generate interview questions for candidate ID 3'\n"
        "  • 'Create a job description for a Senior Python Developer'\n"
        "  • 'Send an interview scheduling email for candidate ID 2'\n"
        "  • 'Show me all candidates with status Interview'"
    )


# ─── Pipeline execution (pre-built workflow) ────────────────────────────────

def execute_pipeline(jd_id: int, db: Session) -> dict:
    """Execute a full recruitment pipeline for a job description.
    
    Steps:
    1. Rank all resumes against the JD
    2. Generate summaries for top candidates
    3. Generate interview questions for top candidates
    4. Create screening stages for top candidates
    5. Draft interview scheduling emails
    
    Returns a comprehensive report.
    """
    logger.info(f"Running recruitment pipeline for JD #{jd_id}")
    
    pipeline_results = {
        "jd_id": jd_id,
        "steps": [],
        "success": True,
    }
    
    # Step 1: Rank candidates
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
    
    # Step 2: Get ranked candidates and process top ones
    ranked = get_ranked_candidates(db, jd_id)
    top_candidates = ranked[:5]  # Top 5
    
    pipeline_results["steps"].append({
        "step": "identify_top_candidates",
        "count": len(top_candidates),
        "candidates": [
            {"id": c["id"], "name": c.get("candidate_name"), "score": c.get("similarity_score")}
            for c in top_candidates
        ],
    })
    
    # Step 3-5: Process each top candidate
    for candidate_data in top_candidates:
        cid = candidate_data["id"]
        
        # Generate summary
        summary_result = _execute_tool("generate_candidate_summary", {"candidate_id": cid}, db)
        pipeline_results["steps"].append({
            "step": f"summary_candidate_{cid}",
            "result": summary_result,
        })
        
        # Generate interview questions
        questions_result = _execute_tool(
            "generate_interview_questions", {"candidate_id": cid, "count": 5}, db
        )
        pipeline_results["steps"].append({
            "step": f"questions_candidate_{cid}",
            "result": questions_result,
        })
        
        # Create screening stage
        stage_result = _execute_tool(
            "create_recruitment_stage",
            {"candidate_id": cid, "stage": "Screening", "notes": "Auto-created by pipeline"},
            db,
        )
        pipeline_results["steps"].append({
            "step": f"stage_candidate_{cid}",
            "result": stage_result,
        })
        
        # Update status
        _execute_tool("update_candidate_status", {"candidate_id": cid, "status": "Screening"}, db)
        
        # Generate interview scheduling email
        email_result = _execute_tool(
            "generate_email",
            {"candidate_id": cid, "template_type": "interview_scheduling"},
            db,
        )
        pipeline_results["steps"].append({
            "step": f"email_candidate_{cid}",
            "result": email_result,
        })
    
    # Generate final summary
    summary_text = _call_llm(
        system_prompt="Summarize this recruitment pipeline execution concisely.",
        user_prompt=f"Pipeline processed JD #{jd_id} with {len(top_candidates)} top candidates. "
                     f"Steps: ranking, summary generation, interview questions, stage creation, email drafting.",
        max_tokens=200,
    )
    
    pipeline_results["summary"] = summary_text or (
        f"Pipeline completed: Ranked candidates for JD #{jd_id}, "
        f"processed {len(top_candidates)} top candidates with summaries, "
        f"interview questions, screening stages, and email drafts."
    )
    
    return pipeline_results
