# 🤖 Recruiter Workflow Fragmentation — Agentic AI Platform

> **A High-Performance, Unified Agentic AI Recruitment Platform** built with **Python · Django · PostgreSQL · SQLAlchemy · Redis · Celery · Docker · AWS EC2**.

Replaces fragmented recruiter workflows with a single intelligent automation platform backed by an autonomous AI agent, distributed asynchronous processing, and high-throughput candidate-to-job matching.

---

## ✨ Features & Capabilities

- 🤖 **Agentic AI**: Autonomously parses recruitment instructions, schedules meetings, reasons, and executes multi-step actions.
- ⚡ **High-Throughput Matching**: Local TF-IDF similarity engine processing **6,000+ candidate-to-job matches per second** (0.167ms/match) with two-tier cloud/local fallback.
- 📄 **Resume Parsing**: High-speed extraction (average 56.7ms per document) for PDF and DOCX files.
- 🔄 **Autonomous Pipeline**: Seamless stage progression, interview question generation, and recruiter batch decisions.
- 📬 **Automated Outreach**: Templated email generation and asynchronous SMTP delivery via Celery & Redis.
- 🐳 **Enterprise Ready**: Containerized with Docker & Docker Compose, PostgreSQL database, and Redis task broker.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Django Web & API Layer                          │
├────────────────────┬──────────────────────┬────────────────────────────┤
│   REST Endpoints   │  AI Agent Orchestrator│     Pipeline Engine       │
├────────────────────┴──────────────────────┴────────────────────────────┤
│                  Asynchronous Task Broker (Celery + Redis)              │
│  ┌───────────────────────┐          ┌───────────────────────────────┐  │
│  │ Background Tasks      │ ◄──────► │ Redis Broker & Result Backend │  │
│  │ • Batch Decisions     │          └───────────────────────────────┘  │
│  │ • Email Outreach      │                                             │
│  │ • Candidate Workflows │                                             │
│  └───────────────────────┘                                             │
├────────────────────────────────────────────────────────────────────────┤
│                          Domain Services Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ LLM Engine   │  │ NLP Matching │  │ Parser       │  │ Email /    │  │
│  │ (Ollama/OAI) │  │ (TF-IDF local)│ │ (PDF/DOCX)   │  │ Scheduler  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
├────────────────────────────────────────────────────────────────────────┤
│                   Data Layer (SQLAlchemy ORM)                          │
│            PostgreSQL (Production) / SQLite (Local Dev)                │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Option 1: Run with Docker Compose (Recommended)

```bash
# Build and start all services (PostgreSQL, Redis, Django Web, Celery Worker)
docker-compose up --build
```

The system will start:
- **Web UI & API**: http://localhost:8000
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`
- **Celery Worker**: running in background container

---

### Option 2: Local Development

#### 1. Setup Environment
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment
```bash
# Copy example configuration
cp env.example .env
```

#### 3. Run Server & Celery Worker
```bash
# Run Django web server
python manage.py runserver 0.0.0.0:8000
# or: python app.py

# In a separate terminal, run Celery worker:
celery -A recruiter_project worker -l info
```

Access the UI and API at **http://localhost:8000**.

---

## 📡 API Endpoints

### AI Agent (Agentic AI)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agent/execute` | Execute natural language recruitment instruction |
| POST | `/api/agent/pipeline/{jd_id}` | Run complete end-to-end recruitment pipeline |
| GET | `/api/agent/tools` | List all available AI agent tools |

### Job Descriptions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jds/` | List all job descriptions |
| GET | `/api/jds/{id}` | Get job description by ID |
| POST | `/api/jds/` | Create new job description |
| PUT | `/api/jds/{id}` | Update job description |
| DELETE | `/api/jds/{id}` | Delete job description |

### Resumes & Parsing
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/resumes/` | List all uploaded resumes |
| GET | `/api/resumes/{id}` | Get resume by ID |
| POST | `/api/resumes/upload` | Upload & parse resume file (PDF/DOCX) |
| POST | `/api/resumes/upload-path` | Parse resume from file path |
| DELETE | `/api/resumes/{id}` | Delete resume |

### Candidate Evaluation & Outreach
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/candidates/` | List candidates (filterable by JD and status) |
| GET | `/api/candidates/{id}` | Get candidate details |
| PUT | `/api/candidates/{id}/status` | Update candidate pipeline stage |
| PUT | `/api/candidates/{id}/notes` | Update candidate interview notes |
| POST | `/api/candidates/batch-decision` | Recruiter batch decision & email outreach |
| POST | `/api/candidates/rank/{jd_id}` | Re-compute similarity ranking |
| GET | `/api/candidates/rank/{jd_id}` | Retrieve ranked candidate list |
| POST | `/api/candidates/{id}/summary` | AI resume vs JD summary generation |
| POST | `/api/interview/questions/{id}`| Tailored interview question generation |
| POST | `/api/email/generate` | Generate email template draft |
| POST | `/api/email/send` | Send templated email to candidate |

---

## 🧪 Testing

Run the automated test suite:

```bash
python -m pytest tests/ -v
```

---

## 📜 License

MIT License.
