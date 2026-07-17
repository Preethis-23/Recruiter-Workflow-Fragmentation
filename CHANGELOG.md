# Changelog

All notable changes to this project will be documented in this file.

---

## [2026-07-16] — Agentic AI Transformation

### Added
- **`hire_for_role` Orchestrator Tool** (`agent_service.py`): New autonomous tool that executes a complete hiring workflow from a single natural language instruction. It chains: Create JD → Search Resumes → Link Candidates → AI Ranking → Process Top N (summaries, interview questions, calendar scheduling, email notifications).
- **`_execute_hire_workflow()` Function** (`agent_service.py`): Core orchestrator function implementing the 4-step autonomous pipeline with structured step logging and error handling at each stage.
- **Upgraded System Prompt** (`agent_service.py`): Rewrote `SYSTEM_PROMPT` to instruct the LLM to act as a fully autonomous agent — prioritizing `hire_for_role` for any hiring/recruiting instructions and never asking for clarification.
- **Hire-Keyword Fallback** (`agent_service.py`): Enhanced `_generate_fallback_response()` to detect hire/recruit keywords (e.g., "hire a", "recruit a", "find candidates for") and route them to the orchestrator when the LLM doesn't produce tool calls (Ollama fallback).
- **Quick Action Chips** (`index.html`): Added suggestion buttons ("Hire a Python ML Engineer", "Hire a Data Scientist", "List all job descriptions") to the Agent Console for one-click workflow triggering.
- **Enhanced Execution Log UI** (`app.js`): Upgraded the Agent Console's tool trace rendering from raw JSON dumps to a clean, styled execution log with step numbers, success/failure icons, and color-coded left borders.
- **This CHANGELOG.md**: Created to track all project changes.

### Changed
- **Agent Console Welcome Message** (`index.html`): Updated suggested prompts from generic "List all job descriptions" to agentic examples like "Hire a Python ML Engineer".
- **Fallback Suggestions** (`agent_service.py`): Updated the "try being more specific" hint list to prioritize agentic commands like "Hire a Python ML Engineer" and "Recruit a Data Scientist".

---

## [2026-07-13] — Email, Notes, and Bug Fixes

### Fixed
- **Resume Email Parsing Bug** (`parser_service.py`): Fixed PDF ligature issue where the `envelope` icon text was prepended to parsed email addresses (e.g., `pepreethiswarang@gmail.com` → `preethiswarang@gmail.com`). Applied regex cleanup filter.
- **Database Email Correction**: Ran SQL update on `resumes` table to fix existing incorrect email addresses.

### Added
- **Candidate Notes** (`candidate.py`, `candidate_router.py`, `schemas.py`): Added `notes` column to the database, a `CandidateNotesUpdate` schema, and a `PUT /api/candidates/{id}/notes` API endpoint.
- **Notes Pop-up Modal** (`index.html`, `app.js`): Implemented a modal-based notes editor for recording candidate performance observations, replacing the previous inline input.
- **Email Sender Settings** (`index.html`, General Settings tab): Added SMTP sender email and password configuration fields.
- **Pipeline Stage Display Fix** (`app.js`): Changed pipeline stage labels from confusing "JD#1, JD#2" to meaningful info.

### Changed
- **All Dropdown Menus**: Standardized dropdown styling across the project UI.
- **Email Service**: Configured to extract recipient email from the resume and send predefined status emails with replaceable values (#name, #position, #status).
