"""
Pydantic schemas for API request/response validation.

These define:
1. What JSON the client must send (request schemas)
2. What JSON we send back (response schemas)

Pydantic automatically validates incoming data and returns
helpful error messages if validation fails.
"""

from datetime import datetime
from pydantic import BaseModel, Field


# =============================================================================
# REQUEST SCHEMAS (what the client sends us)
# =============================================================================


class BenchmarkCreate(BaseModel):
    """
    Request body for POST /benchmarks

    Example:
    {
        "name": "Claude speed test",
        "model": "claude-3-5-sonnet-20241022",
        "prompts": ["Hello, how are you?", "Explain quantum computing"]
    }
    """

    name: str = Field(
        ...,  # ... means required
        min_length=1,
        max_length=255,
        description="A descriptive name for this benchmark",
        examples=["Claude speed test"],
    )
    model: str = Field(
        default="claude-3-haiku-20240307",
        description="The model to benchmark. Options: claude-3-haiku-20240307, claude-3-5-haiku-20241022, claude-3-5-sonnet-20241022",
    )
    prompts: list[str] = Field(
        ...,
        min_length=1,  # At least one prompt required
        description="List of prompts to test",
        examples=[["Hello!", "Explain quantum computing in simple terms"]],
    )


# =============================================================================
# RESPONSE SCHEMAS (what we send back to the client)
# =============================================================================


class BenchmarkResultResponse(BaseModel):
    """Single result within a benchmark."""

    id: int
    prompt: str
    response: str | None = None

    # Timing metrics
    ttft_ms: float | None = None        # Time to First Token (streaming)
    latency_ms: float | None = None     # Total request time
    tokens_per_second: float | None = None  # Output generation speed

    # Token counts
    input_tokens: int | None = None
    output_tokens: int | None = None

    # Cost
    cost_usd: float | None = None

    # Error (if any)
    error: str | None = None

    # This allows Pydantic to read from SQLAlchemy models
    # Without this, it can't convert ORM objects to JSON
    model_config = {"from_attributes": True}


class BenchmarkResponse(BaseModel):
    """Response for GET /benchmarks/{id}"""

    id: int
    name: str
    model: str
    status: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    results: list[BenchmarkResultResponse] = []

    model_config = {"from_attributes": True}


class BenchmarkSummary(BaseModel):
    """
    Brief summary for listing benchmarks (GET /benchmarks).
    Doesn't include full results to keep response small.
    """

    id: int
    name: str
    model: str
    status: str
    created_at: datetime
    result_count: int = 0

    model_config = {"from_attributes": True}
