"""
Database connection and session management.

Key concepts:
- Engine: The connection pool to the database
- Session: A "conversation" with the database (groups queries into transactions)
- Base: Parent class for all our database models
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.config import settings

# Create the database engine
# - The engine manages a pool of connections to the database
# - echo=True logs all SQL queries (helpful for learning, disable in production)

# SQLite needs special handling for FastAPI (multi-threaded)
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    echo=True,  # Log SQL queries to console (helpful for debugging)
    connect_args=connect_args,
)

# Create a session factory
# - Each request gets its own session
# - Sessions track changes and commit them as a transaction
SessionLocal = sessionmaker(
    autocommit=False,  # We manually call commit()
    autoflush=False,   # We manually control when changes are sent to DB
    bind=engine,
)

# Base class for all database models
# All our models (Benchmark, Result) will inherit from this
Base = declarative_base()


def get_db():
    """
    Dependency that provides a database session.

    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    The 'yield' makes this a context manager:
    1. Create session
    2. Yield it to the route function
    3. Close session when request is done (even if there's an error)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
