"""
LLM Benchmark API - Main Application Entry Point

This is where we:
1. Create the FastAPI application
2. Register all routers (groups of endpoints)
3. Create database tables on startup

To run:
    uvicorn src.main:app --reload

Then visit:
    http://localhost:8000/docs  - Swagger UI (interactive API docs)
    http://localhost:8000/redoc - ReDoc (alternative docs)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database import engine, Base
from src.routers import benchmarks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager - runs code on startup and shutdown.

    Startup:
        - Create database tables if they don't exist

    Shutdown:
        - (Nothing for now, but could close connections, etc.)

    This is the modern way to handle startup/shutdown in FastAPI
    (replaces the deprecated @app.on_event decorators).
    """
    # === STARTUP ===
    # Create all tables defined in models.py
    # If tables already exist, this does nothing (safe to run multiple times)
    Base.metadata.create_all(bind=engine)
    print("Database tables created (if they didn't exist)")

    yield  # App runs here

    # === SHUTDOWN ===
    print("Shutting down...")


# Create the FastAPI application
app = FastAPI(
    title="LLM Benchmark API",
    description="Benchmark LLM latency, throughput, and cost across providers",
    version="0.1.0",
    lifespan=lifespan,
)


# Register routers
# This adds all the /benchmarks/* endpoints to our app
app.include_router(benchmarks.router)


# Root endpoint - useful for health checks
@app.get("/", tags=["health"])
def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "LLM Benchmark API is running",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",  # TODO: Actually check DB connection
    }
