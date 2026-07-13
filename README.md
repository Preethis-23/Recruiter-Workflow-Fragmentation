# 🤖 Recruiter Workflow Fragmentation — Agentic AI

> **An AI-powered recruitment automation platform** that replaces fragmented recruiter workflows with a single, intelligent API backed by an autonomous AI agent.

## ✨ What It Does

This project consolidates the entire recruitment workflow into one system, powered by an **AI agent** that can autonomously execute multi-step recruitment tasks from natural language instructions.

### AI Agent Capabilities

| Capability | Description |
|-----------|-------------|
| 📝 **Job Description Management** | Create, update, delete, and search job descriptions |
| 📄 **Resume Parsing** | Upload and automatically parse PDF/DOCX resumes |
| 🏆 **Candidate Ranking** | AI-powered similarity scoring between resumes and JDs |
| 📊 **Candidate Summaries** | Generate AI summaries comparing candidates to JDs |
| ❓ **Interview Questions** | Generate tailored technical + behavioral questions |
| 📧 **Email Generation** | Draft interview, offer, rejection, and follow-up emails |
| 🔄 **Pipeline Tracking** | Track candidates through recruitment stages |
| 🚀 **Full Pipeline Automation** | Run the entire workflow with a single API call |

### Example Agent Interactions

```
"List all job descriptions"
"Create a Senior Python Developer position for the Backend team"
"Rank all resumes against job description #1"
"Generate interview questions for candidate #3"
"Send an interview scheduling email for candidate #5"
"Run the full pipeline for JD #2"
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                    │
├─────────────┬──────────────┬────────────────────────────┤
│  REST APIs  │  AI Agent    │  Pipeline Engine            │
│  (CRUD)     │  (Tool-Call) │  (Automated Workflow)       │
├─────────────┴──────────────┴────────────────────────────┤
│                    Services Layer                         │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────────┐  │
│  │ LLM      │ │ Embedding│ │ Parser │ │ Email        │  │
│  │ Service  │ │ Service  │ │ Service│ │ Service      │  │
│  └────┬─────┘ └────┬─────┘ └────────┘ └──────────────┘  │
│       │             │                                     │
│  ┌────▼─────────────▼─────┐                              │
│  │   LLM Provider         │                              │
│  │   • Ollama (local)     │                              │
│  │   • OpenAI (cloud)     │                              │
│  └────────────────────────┘                              │
├──────────────────────────────────────────────────────────┤
│                 SQLite / PostgreSQL                       │
└──────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Ollama** (recommended, for local LLM) — [Install Ollama](https://ollama.ai)
- OR **OpenAI API key**

### 1. Clone and Setup

```bash
cd "Recruiter Worflow Fragmentation"

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example env file
cp env.example .env

# Edit .env to set your LLM provider
# Default is Ollama (local, free)
```

### 3. Setup Ollama (Recommended)

```bash
# Install and start Ollama, then pull a model:
ollama pull llama3.2
```

### 4. Run the Server

```bash
python app.py
```

The API will be available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📡 API Endpoints

### AI Agent (Agentic AI)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agent/execute` | Send natural language instructions |
| POST | `/api/agent/pipeline/{jd_id}` | Run full recruitment pipeline |
| GET | `/api/agent/tools` | List available agent tools |

### Job Descriptions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jds/` | List all JDs |
| GET | `/api/jds/{id}` | Get JD by ID |
| POST | `/api/jds/` | Create JD |
| PUT | `/api/jds/{id}` | Update JD |
| DELETE | `/api/jds/{id}` | Delete JD |

### Resumes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/resumes/` | List all resumes |
| GET | `/api/resumes/{id}` | Get resume by ID |
| POST | `/api/resumes/upload` | Upload and parse resume |
| DELETE | `/api/resumes/{id}` | Delete resume |

### Candidates

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/candidates/` | List candidates |
| GET | `/api/candidates/{id}` | Get candidate |
| PUT | `/api/candidates/{id}/status` | Update status |
| POST | `/api/candidates/rank/{jd_id}` | Rank candidates |
| GET | `/api/candidates/rank/{jd_id}` | Get rankings |
| POST | `/api/candidates/{id}/summary` | Generate summary |

### Email & Interview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/email/generate` | Generate email |
| POST | `/api/interview/questions/{id}` | Generate questions |

### Recruitment Stages

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stages/candidate/{id}` | List stages for candidate |
| POST | `/api/stages/candidate/{id}` | Create stage |
| PUT | `/api/stages/{id}` | Update stage |
| DELETE | `/api/stages/{id}` | Delete stage |

## 🔧 Configuration

Key environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | LLM backend: `ollama` or `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | OpenAI model |
| `DATABASE_URL` | `sqlite:///./recruiter_workflow.db` | Database connection |
| `AGENT_MAX_ITERATIONS` | `10` | Max agent reasoning loops |

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
```

## 📁 Project Structure

```
├── app.py                          # Entry point
├── requirements.txt                # Dependencies
├── .env                            # Environment config
├── env.example                     # Example config
├── recruiter_workflow/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory
│   ├── config.py                   # Settings (pydantic-settings)
│   ├── database.py                 # SQLAlchemy setup
│   ├── logging.py                  # Logging config
│   ├── schemas.py                  # Pydantic request/response models
│   ├── models/
│   │   ├── job_description.py      # JD model
│   │   ├── resume.py               # Resume model
│   │   ├── candidate.py            # Candidate model
│   │   └── recruitment_stage.py    # Pipeline stage model
│   ├── routers/
│   │   ├── agent_router.py         # 🤖 AI Agent endpoints
│   │   ├── jd_router.py            # JD CRUD
│   │   ├── resume_router.py        # Resume upload/parse
│   │   ├── candidate_router.py     # Candidate management
│   │   ├── stage_router.py         # Pipeline stages
│   │   ├── email_router.py         # Email generation
│   │   └── interview_router.py     # Interview questions
│   └── services/
│       ├── agent_service.py        # 🤖 Core AI agent engine
│       ├── llm_service.py          # LLM provider (Ollama/OpenAI)
│       ├── embedding_service.py    # Similarity scoring
│       ├── ranking_service.py      # Candidate ranking
│       ├── parser_service.py       # Resume parsing
│       └── email_service.py        # Email templates
└── tests/
    ├── conftest.py                 # Test fixtures
    ├── test_health.py              # Health check tests
    └── test_jd_routes.py           # JD endpoint tests
```

## 📜 License

MIT
