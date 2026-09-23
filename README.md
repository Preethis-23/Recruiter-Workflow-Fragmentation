# Recruiter Workflow Fragmentation — Unified Agentic AI Platform

> A high-performance, unified AI platform that consolidates resume parsing, candidate ranking, stage tracking, meeting scheduling, and templated outreach into an autonomous recruitment system.

---

## ⚡ Tech Stack

- **Backend & Web**: Python, Django
- **Database & ORM**: PostgreSQL, SQLAlchemy
- **Async Queue & Cache**: Redis, Celery
- **Infrastructure & Deployment**: Docker, Docker Compose, AWS EC2
- **AI & NLP**: Local TF-IDF Vector Engine, Ollama / OpenAI LLM APIs

---

## 🚀 Key Highlights & Performance

- **High-Throughput Matching**: Local TF-IDF similarity engine processing **6,000+ candidate-to-job matches/sec** (0.167ms/match).
- **Sub-60ms Resume Parsing**: Automated text extraction and section segmentation averaging **56.7ms per document** (PDF & DOCX).
- **Two-Tier Resilient Fallback**: 100% pipeline matching availability by architecting automatic failover from Cloud LLM to local TF-IDF on rate limits or network failures.
- **Autonomous Agentic Automation**: Natural language task execution, candidate shortlisting, interview question generation, and batch recruiter decision workflows.
- **Asynchronous Task Queue**: Celery & Redis handling background email delivery, candidate pipeline progression, and batch ranking.

---

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                 Django Web & REST API Layer                     │
├─────────────────┬──────────────────────┬────────────────────────┤
│  Recruiter Web  │   AI Agent Router    │   Pipeline Engine      │
│  UI Dashboard   │   (Tool-Calling)     │   (Auto-Progression)   │
├─────────────────┴──────────────────────┴────────────────────────┤
│             Asynchronous Worker Layer (Celery + Redis)          │
│       • Batch Decision Outreach  • Heavy Matching & Tasks       │
├─────────────────────────────────────────────────────────────────┤
│                     Domain Services Layer                       │
│  • Resume Parser (PDF/DOCX)      • Local TF-IDF Matcher         │
│  • LLM Summaries & Questions     • Email & Meeting Scheduler    │
├─────────────────────────────────────────────────────────────────┤
│                   Data Layer (SQLAlchemy ORM)                   │
│             PostgreSQL (Production) / SQLite (Dev)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏁 Quick Start

### 1. Run with Docker Compose (Recommended)

```bash
# Build and launch all services (PostgreSQL, Redis, Django, Celery)
docker-compose up --build
```
Access the application at **http://localhost:8000**.

---

### 2. Run Locally

#### Prerequisites
- Python 3.11+
- Virtualenv

```bash
# 1. Clone & create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp env.example .env

# 4. Start the Django web server
python manage.py runserver 0.0.0.0:8000
# or: python app.py

# 5. Start Celery worker (optional, in separate terminal)
celery -A recruiter_project worker -l info
```

---

## 📡 Essential API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health and environment status |
| `POST` | `/api/agent/execute` | Execute natural language recruitment instruction |
| `POST` | `/api/agent/pipeline/{jd_id}` | Trigger automated end-to-end recruitment workflow |
| `GET` / `POST` | `/api/jds/` | List or create Job Descriptions |
| `POST` | `/api/resumes/upload` | Upload & parse resume (PDF/DOCX) |
| `GET` / `POST` | `/api/candidates/` | List, filter, or evaluate candidates |
| `POST` | `/api/candidates/batch-decision` | Recruiter batch accept/reject & email trigger |
| `POST` | `/api/candidates/rank/{jd_id}` | Re-compute candidate similarity ranking |
| `POST` | `/api/interview/questions/{id}` | Generate tailored interview questions |
| `POST` | `/api/email/send` | Send automated recruiter email |

---

## 🧪 Verification & Tests

Run the full automated test suite:

```bash
python -m pytest tests/ -v
```

---

## 📜 License

MIT License.
