"""Logging configuration for Recruiter Workflow API."""

import logging
import sys
from typing import Dict, Any
from recruiter_workflow.config import settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    
    # Set root logger level
    logging.basicConfig(
        level=settings.get_log_level(),
        format=settings.LOG_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Configure specific loggers
    loggers: Dict[str, Dict[str, Any]] = {
        "uvicorn": {"level": logging.INFO, "propagate": False},
        "uvicorn.access": {"level": logging.INFO, "propagate": False},
        "uvicorn.error": {"level": logging.WARNING, "propagate": False},
        "sqlalchemy": {"level": logging.WARNING, "propagate": False},
        "fastapi": {"level": logging.INFO, "propagate": False},
        "recruiter_workflow": {"level": settings.get_log_level(), "propagate": False},
    }
    
    for logger_name, config in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(config["level"])
        logger.propagate = config.get("propagate", True)
        
        # Add console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(config["level"])
        formatter = logging.Formatter(settings.LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def get_logger(name: str = "recruiter_workflow") -> logging.Logger:
    """Get a configured logger instance."""
    return logging.getLogger(name)


# Configure logging when module is imported
configure_logging()

# Module-level logger
logger = get_logger(__name__)