# Recruiter Workflow Fragmentation

A unified web platform and background engine built to streamline the hiring process. Instead of jumping between different tools to parse resumes, rank candidates, schedule interviews, and draft emails, this system brings everything together into a single workflow.

---

## Tech Stack

- **Web Framework**: Python / Django
- **Database & ORM**: PostgreSQL / SQLAlchemy
- **Background Tasks & Queue**: Celery / Redis
- **Containerization**: Docker & Docker Compose
- **NLP & AI**: Local TF-IDF similarity pipeline + Ollama / OpenAI API

---

## Features & Highlights

1. **Resume Ingestion & Parsing**: Automatically extracts text and parses candidate contact details, skills, education, experience, and projects from PDF and DOCX files (averaging 56.7ms per document across 77 indexed resumes).
2. **High-Throughput Candidate Matching**: Local TF-IDF similarity pipeline processing **6,000+ matches/sec** (0.167ms/match) for candidate-to-job matching.
3. **Resilient Two-Tier Fallback**: Maintains 100% pipeline matching availability via two-tier fallback (cloud API → local TF-IDF), tested across 11 job descriptions and 228 candidate profile records to bypass external API limits or network failures.
4. **Calendar Scheduling & Templated Email Outreach**: Google Calendar API integration for interview scheduling and templated email outreach (interview invites, offers, and rejections).
5. **Pipeline & Stage Tracking**: Move applicants through hiring stages (Screening, Interview, Offer, Hired, Rejected) with custom notes and performance feedback.
6. **Recruiter Batch Decisions**: Accept or reject multiple candidates simultaneously and automatically trigger notification delivery.
7. **Background Job Execution**: Uses Celery and Redis to handle email delivery, automated stage progression, and heavy candidate rankings asynchronously.

---

## How to Run the Project

### Option 1: Run with Docker Compose (Recommended)

This brings up PostgreSQL, Redis, the Django server, and the Celery background worker with a single command:

```bash
docker-compose up --build
```

Once running, open your browser and go to **http://localhost:8000**.

---

### Option 2: Run Locally (Without Docker)

#### 1. Setup Virtual Environment
```bash
# Create and activate environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

#### 2. Configure Environment & Seed Benchmark Data
```bash
cp env.example .env

# Seed benchmark data (11 JDs, 77 Resumes, 228 Candidate Records)
python seed_and_cleanup.py
```

#### 3. Start the Application
```bash
# Run Django web server
python manage.py runserver 0.0.0.0:8000

# (Optional) In another terminal, run Celery worker
celery -A recruiter_project worker -l info
```

Visit **http://localhost:8000** to view the recruiter dashboard.

---

## Core API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | `GET` | Health check & service status |
| `/api/jds/` | `GET` / `POST` | List or create job descriptions |
| `/api/resumes/upload` | `POST` | Upload and parse a resume file |
| `/api/candidates/` | `GET` | View candidates and filter by job role |
| `/api/candidates/rank/{jd_id}` | `POST` | Calculate similarity rankings for a job |
| `/api/candidates/batch-decision` | `POST` | Batch accept/reject candidates and send emails |
| `/api/interview/questions/{id}` | `POST` | Generate candidate-specific interview questions |
| `/api/email/send` | `POST` | Send candidate outreach emails |
| `/api/agent/execute` | `POST` | Run natural language instructions via AI agent |

---

## Running Tests

To verify that all endpoints, fallback mechanisms, parsers, and database operations work properly:

```bash
python -m pytest tests/ -v
```

---

## License

MIT
