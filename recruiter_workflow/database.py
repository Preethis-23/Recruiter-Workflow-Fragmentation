import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from recruiter_workflow.config import settings

DATABASE_URL = os.environ.get("DATABASE_URL", settings.DATABASE_URL)

engine_kwargs = {"echo": settings.DATABASE_ECHO}
if "sqlite" in DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Safe to call multiple times."""
    import recruiter_workflow.models  # noqa: F401 – ensure models are imported
    Base.metadata.create_all(bind=engine)
