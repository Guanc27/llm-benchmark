"""
Benchmark API endpoints (async version).

REST API design:
    POST   /benchmarks      - Create and run a new benchmark
    GET    /benchmarks      - List all benchmarks
    GET    /benchmarks/{id} - Get a specific benchmark with results
    DELETE /benchmarks/{id} - Delete a benchmark

Note on async in FastAPI:
    When you mark an endpoint as 'async def', FastAPI runs it in the
    async event loop. This means:
    - You can use 'await' for async operations
    - The server can handle other requests while waiting for I/O
    - You get better throughput under load

    For database operations with SQLAlchemy (which is sync by default),
    FastAPI automatically runs them in a thread pool to avoid blocking.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Benchmark, BenchmarkResult
from src.schemas import BenchmarkCreate, BenchmarkResponse, BenchmarkSummary
from src.services.benchmark_runner import run_benchmark_async

router = APIRouter(
    prefix="/benchmarks",
    tags=["benchmarks"],
)


@router.post(
    "",
    response_model=BenchmarkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and run a benchmark",
    description="""
    Creates a new benchmark and runs all prompts against the specified model.

    **Features:**
    - Prompts run concurrently (faster than sequential)
    - Streaming enabled for accurate TTFT measurement
    - Returns timing metrics: TTFT, total latency, tokens/second

    **Note:** This endpoint blocks until all prompts complete. For many prompts,
    this could take a while. Future versions may support background execution.
    """,
)
async def create_benchmark(
    benchmark_in: BenchmarkCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new benchmark and run it.

    The 'async def' allows us to use 'await' for the benchmark runner,
    which runs all LLM calls concurrently.
    """
    # Create the benchmark record
    benchmark = Benchmark(
        name=benchmark_in.name,
        model=benchmark_in.model,
        status="pending",
    )
    db.add(benchmark)
    db.commit()
    db.refresh(benchmark)

    # Run the benchmark asynchronously
    # 'await' pauses this function until run_benchmark_async completes,
    # but other requests can be handled in the meantime
    benchmark = await run_benchmark_async(db, benchmark, benchmark_in.prompts)

    return benchmark


@router.get(
    "",
    response_model=list[BenchmarkSummary],
    summary="List all benchmarks",
)
async def list_benchmarks(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """
    List all benchmarks with pagination.

    Even though database queries are sync, FastAPI handles this gracefully
    by running them in a thread pool when the endpoint is async.
    """
    benchmarks = db.query(Benchmark).offset(skip).limit(limit).all()

    summaries = []
    for b in benchmarks:
        result_count = db.query(BenchmarkResult).filter(
            BenchmarkResult.benchmark_id == b.id
        ).count()

        summaries.append(
            BenchmarkSummary(
                id=b.id,
                name=b.name,
                model=b.model,
                status=b.status,
                created_at=b.created_at,
                result_count=result_count,
            )
        )

    return summaries


@router.get(
    "/{benchmark_id}",
    response_model=BenchmarkResponse,
    summary="Get a benchmark by ID",
)
async def get_benchmark(
    benchmark_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific benchmark with all its results."""
    benchmark = db.query(Benchmark).filter(Benchmark.id == benchmark_id).first()

    if benchmark is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark with id {benchmark_id} not found",
        )

    return benchmark


@router.delete(
    "/{benchmark_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a benchmark",
)
async def delete_benchmark(
    benchmark_id: int,
    db: Session = Depends(get_db),
):
    """Delete a benchmark and all its results."""
    benchmark = db.query(Benchmark).filter(Benchmark.id == benchmark_id).first()

    if benchmark is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark with id {benchmark_id} not found",
        )

    db.delete(benchmark)
    db.commit()

    return None
