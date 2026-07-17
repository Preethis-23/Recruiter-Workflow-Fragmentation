"""LLM service for generating summaries, interview questions, and agent reasoning.

Supports two providers:
- **Ollama** (local, free) — default
- **OpenAI** (cloud, API key required)

Falls back to heuristic methods if no LLM is available.
"""

import os
import re
import json
import logging
from typing import Optional

from recruiter_workflow.config import settings

logger = logging.getLogger(__name__)


# ─── Provider abstraction ────────────────────────────────────────────────────

def _call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 500,
    temperature: float = 0.3,
    tools: Optional[list] = None,
) -> Optional[str]:
    """Call the configured LLM provider. Returns the response text or None on failure."""
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "ollama":
        return _call_ollama(system_prompt, user_prompt, max_tokens, temperature, tools)
    elif provider == "openai":
        return _call_openai(system_prompt, user_prompt, max_tokens, temperature, tools)
    else:
        logger.warning(f"Unknown LLM provider: {provider}")
        return None


def _call_ollama(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 500,
    temperature: float = 0.3,
    tools: Optional[list] = None,
) -> Optional[str]:
    """Call Ollama local LLM."""
    try:
        import ollama
        client = ollama.Client(host=settings.OLLAMA_BASE_URL)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        kwargs = {
            "model": settings.OLLAMA_MODEL,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        
        if tools:
            kwargs["tools"] = tools
        
        response = client.chat(**kwargs)
        return response["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        return None


def _call_openai(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 500,
    temperature: float = 0.3,
    tools: Optional[list] = None,
) -> Optional[str]:
    """Call OpenAI API."""
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not set")
        return None
    
    try:
        import openai
        client_kwargs = {"api_key": settings.OPENAI_API_KEY}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL
        client = openai.OpenAI(**client_kwargs)
        
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI call failed: {e}")
        return None


def call_llm_with_tools(
    system_prompt: str,
    user_prompt: str,
    tools: list[dict],
    temperature: float = 0.1,
) -> dict:
    """Call LLM with tool definitions for agentic behavior.
    
    Returns dict with 'content' and optionally 'tool_calls'.
    """
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "ollama":
        return _call_ollama_with_tools(system_prompt, user_prompt, tools, temperature)
    elif provider == "openai":
        return _call_openai_with_tools(system_prompt, user_prompt, tools, temperature)
    else:
        return {"content": "No LLM provider configured.", "tool_calls": []}


def _call_ollama_with_tools(
    system_prompt: str,
    user_prompt: str,
    tools: list[dict],
    temperature: float = 0.1,
) -> dict:
    """Call Ollama with tool-calling support."""
    try:
        import ollama
        client = ollama.Client(host=settings.OLLAMA_BASE_URL)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        response = client.chat(
            model=settings.OLLAMA_MODEL,
            messages=messages,
            tools=tools,
            options={"temperature": temperature},
        )
        
        msg = response["message"]
        result = {"content": msg.get("content", ""), "tool_calls": []}
        
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                result["tool_calls"].append({
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"],
                })
        
        return result
    except Exception as e:
        logger.error(f"Ollama tool call failed: {e}")
        return {"content": f"Error: {e}", "tool_calls": []}


def _call_openai_with_tools(
    system_prompt: str,
    user_prompt: str,
    tools: list[dict],
    temperature: float = 0.1,
) -> dict:
    """Call OpenAI with tool-calling support."""
    if not settings.OPENAI_API_KEY:
        return {"content": "OpenAI API key not set.", "tool_calls": []}
    
    try:
        import openai
        client_kwargs = {"api_key": settings.OPENAI_API_KEY}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL
        client = openai.OpenAI(**client_kwargs)
        
        # Convert tools to OpenAI format
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": tool["function"] if "function" in tool else tool,
            })
        
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=openai_tools if openai_tools else None,
            temperature=temperature,
        )
        
        msg = response.choices[0].message
        result = {"content": msg.content or "", "tool_calls": []}
        
        if msg.tool_calls:
            for tc in msg.tool_calls:
                result["tool_calls"].append({
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })
        
        return result
    except Exception as e:
        logger.error(f"OpenAI tool call failed: {e}")
        return {"content": f"Error: {e}", "tool_calls": []}


# ─── High-level functions ────────────────────────────────────────────────────

def generate_summary(resume_text: str, jd_text: str) -> str:
    """Generate a brief candidate summary by comparing the resume to the JD.
    
    Uses the configured LLM provider; falls back to heuristic if unavailable.
    """
    result = _call_llm(
        system_prompt=(
            "You are a technical recruiter. Write a 3–4 sentence summary "
            "comparing the candidate's resume to the job description. "
            "Highlight matching skills, experience gaps, and overall fit."
        ),
        user_prompt=f"Job Description:\n{jd_text[:2000]}\n\nResume:\n{resume_text[:2000]}",
        max_tokens=200,
        temperature=0.3,
    )
    return result if result else _heuristic_summary(resume_text, jd_text)


def generate_interview_questions(resume_text: str, jd_text: str, count: int = 5) -> list[str]:
    """Generate technical interview questions based on resume + JD.
    
    Uses the configured LLM provider; falls back to generic questions.
    """
    result = _call_llm(
        system_prompt=(
            f"You are a technical interviewer. Generate exactly {count} concise "
            "interview questions that assess the candidate's fit based on their "
            "resume and the job description. Mix technical and behavioural questions. "
            "Return ONLY the questions, one per line, numbered."
        ),
        user_prompt=f"Job Description:\n{jd_text[:2000]}\n\nResume:\n{resume_text[:2000]}",
        max_tokens=500,
        temperature=0.4,
    )
    
    if result:
        questions = [q.lstrip("0123456789. )-").strip() for q in result.split("\n") if q.strip()]
        return questions[:count]
    
    return _fallback_questions(count)


# ─── Fallback helpers ─────────────────────────────────────────────────────────

def _heuristic_summary(resume_text: str, jd_text: str) -> str:
    resume_skills = set(_extract_skills(resume_text))
    jd_skills = set(_extract_skills(jd_text))
    matched = resume_skills & jd_skills
    missing = jd_skills - resume_skills

    lines = []
    if matched:
        lines.append(f"The candidate's skills match the JD in: {', '.join(sorted(matched)[:8])}.")
    if missing:
        lines.append(f"Missing/not mentioned skills: {', '.join(sorted(missing)[:6])}.")
    if not lines:
        lines.append("The candidate's profile has been parsed. No strong skill overlap detected.")

    lines.append("Review the full resume for detailed experience fit.")
    return " ".join(lines)


_KNOWN_TECH_SKILLS = {
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
    "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "docker", "kubernetes", "aws", "gcp", "azure", "terraform",
    "machine learning", "deep learning", "nlp", "computer vision",
    "git", "ci/cd", "jenkins", "github actions",
}


def _extract_skills(text: str) -> list[str]:
    lower = text.lower()
    found = set()
    for skill in _KNOWN_TECH_SKILLS:
        if skill in lower:
            found.add(skill)
    return sorted(found)


def _fallback_questions(count: int) -> list[str]:
    pool = [
        "Describe your most challenging technical project and how you approached it.",
        "How do you stay current with industry trends and new technologies?",
        "Tell us about a time you worked in a cross-functional team.",
        "How do you handle conflicting priorities or deadlines?",
        "Describe a situation where you had to debug a complex production issue.",
        "What is your experience with agile / scrum methodologies?",
        "How do you ensure code quality in your projects?",
        "Walk us through your approach to designing a scalable system.",
    ]
    return pool[:count]
