"""Recruiter Workflow Fragmentation — Unified Agentic AI API.

A single backend that replaces fragmented recruiter workflows with
AI-powered automation:
- Manage job descriptions
- Upload & parse resumes (PDF/DOCX)
- Rank candidates by similarity (NLP / TF-IDF / LLM embeddings)
- Track candidates through recruitment stages
- Generate AI-powered summaries & interview questions
- Generate templated emails (interview, offer, rejection, follow-up)
- **AI Agent** that autonomously executes multi-step recruitment workflows
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles

from recruiter_workflow.config import settings
from recruiter_workflow.logging import logger
from recruiter_workflow.database import init_db
from recruiter_workflow.routers import (
    jd_router,
    resume_router,
    candidate_router,
    stage_router,
    email_router,
    interview_router,
    agent_router,
    meeting_router,
)

description = (
    "A unified **agentic AI platform** that consolidates fragmented recruiter workflows into a single API. "
    "Manage job descriptions, parse resumes, rank candidates using NLP, "
    "track recruitment stages, generate AI-powered interview questions, "
    "send templated emails, and **automate entire recruitment pipelines** with an AI agent — all in one place.\n\n"
    "## AI Agent\n"
    "Send natural language instructions to `/api/agent/execute` and the AI agent will "
    "autonomously plan and execute the necessary steps using its available tools.\n\n"
    "Supports **OpenAI** and **Ollama** (local) as LLM backends."
)

tags_metadata = [
    {"name": "AI Agent", "description": "Agentic AI — execute natural language recruitment instructions."},
    {"name": "Job Descriptions", "description": "CRUD for job descriptions."},
    {"name": "Resumes", "description": "Upload and parse resumes (PDF/DOCX)."},
    {"name": "Candidates", "description": "Rank, summarise, and manage candidates."},
    {"name": "Recruitment Stages", "description": "Track candidate pipeline stages."},
    {"name": "Email Generation", "description": "Generate templated emails."},
    {"name": "Interview Questions", "description": "AI-powered interview question generation."},
    {"name": "Health", "description": "Service health check."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown logic."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Database: {settings.DATABASE_URL}")
    
    init_db()
    logger.info("Database initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down gracefully")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        description=description,
        version=settings.APP_VERSION,
        openapi_tags=tags_metadata,
        docs_url="/docs",
        redoc_url="/redoc",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Add middleware
    _add_middleware(app)
    
    # Add exception handlers
    _add_exception_handlers(app)

    # Register routers — Agent first (most important)
    app.include_router(agent_router.router)
    app.include_router(jd_router.router)
    app.include_router(resume_router.router)
    app.include_router(candidate_router.router)
    app.include_router(stage_router.router)
    app.include_router(email_router.router)
    app.include_router(interview_router.router)
    app.include_router(meeting_router.router)

    # Health check
    @app.get("/health", tags=["Health"])
    def health_check():
        return {
            "status": "healthy",
            "service": "recruiter-workflow-fragmentation",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "llm_provider": settings.LLM_PROVIDER,
        }

    # Mount static files at the root
    import os
    if os.path.exists("static"):
        app.mount("/", StaticFiles(directory="static", html=True), name="static")

    return app


def _add_middleware(app: FastAPI) -> None:
    """Add middleware to the FastAPI application."""
    
    # CORS middleware - use configured allowed origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all incoming requests and responses."""
        logger.info(f"Incoming request: {request.method} {request.url}")
        
        try:
            response = await call_next(request)
            logger.info(f"Response: {response.status_code} for {request.method} {request.url}")
            return response
        except Exception as e:
            logger.error(f"Error processing {request.method} {request.url}: {str(e)}")
            raise


def _add_exception_handlers(app: FastAPI) -> None:
    """Add custom exception handlers to the FastAPI application."""
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder({
                "detail": "Validation Error",
                "errors": exc.errors(),
                "body": exc.body
            }),
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle generic exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder({
                "detail": "Internal Server Error",
                "message": str(exc)
            }),
        )


app = create_app()
