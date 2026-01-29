"""
Database models (SQLAlchemy ORM).

Each class here becomes a table in PostgreSQL.
Each attribute becomes a column.

Example:
    class Benchmark -> creates table "benchmarks"
    id: int         -> creates column "id" of type INTEGER
    name: str       -> creates column "name" of type VARCHAR
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from src.database import Base


class Benchmark(Base):
    """
    A benchmark job that tests one or more prompts against an LLM.

    Table: benchmarks
    """

    __tablename__ = "benchmarks"

    # Primary key - unique identifier, auto-incremented
    id = Column(Integer, primary_key=True, index=True)

    # User-provided name for this benchmark
    name = Column(String(255), nullable=False)

    # Which model to test (e.g., "claude-3-5-sonnet-20241022")
    model = Column(String(100), nullable=False)

    # Status: pending, running, completed, failed
    status = Column(String(50), default="pending")

    # When was this benchmark created/started/finished
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationship: one Benchmark has many Results
    # This lets us do: benchmark.results to get all associated results
    results = relationship("BenchmarkResult", back_populates="benchmark")


class BenchmarkResult(Base):
    """
    A single LLM call result within a benchmark.

    Table: benchmark_results
    """

    __tablename__ = "benchmark_results"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key - links this result to a benchmark
    # ON DELETE CASCADE: if benchmark is deleted, delete its results too
    benchmark_id = Column(
        Integer,
        ForeignKey("benchmarks.id", ondelete="CASCADE"),
        nullable=False,
    )

    # The prompt that was sent
    prompt = Column(Text, nullable=False)

    # The response received
    response = Column(Text, nullable=True)

    # Timing metrics (in milliseconds)
    ttft_ms = Column(Float, nullable=True)     # Time to First Token (streaming only)
    latency_ms = Column(Float, nullable=True)  # Total time for request

    # Derived metrics
    tokens_per_second = Column(Float, nullable=True)  # Output generation speed

    # Token counts (from API response)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)

    # Estimated cost in USD
    cost_usd = Column(Float, nullable=True)

    # If something went wrong
    error = Column(Text, nullable=True)

    # When this specific call was made
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship back to parent benchmark
    benchmark = relationship("Benchmark", back_populates="results")
