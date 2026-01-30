"""
Async benchmark execution service.

This module orchestrates running benchmarks:
1. Update benchmark status to "running"
2. Run all prompts concurrently using asyncio.gather()
3. Save results to database
4. Update benchmark status to "completed"

Key concept - asyncio.gather():
    Instead of running prompts one-by-one (slow):
        result1 = await call_llm(prompt1)  # wait 2s
        result2 = await call_llm(prompt2)  # wait 2s
        # Total: 4s

    We run them concurrently (fast):
        result1, result2 = await asyncio.gather(
            call_llm(prompt1),
            call_llm(prompt2),
        )
        # Total: ~2s (limited by slowest)
"""

import asyncio
from datetime import datetime

from sqlalchemy.orm import Session

from src.models import Benchmark, BenchmarkResult
from src.services.anthropic_client import call_anthropic


async def run_single_prompt(prompt: str, model: str) -> dict:
    """
    Run a single prompt and return results as a dict.

    This is a helper that wraps call_anthropic for use with asyncio.gather().
    We return a dict (not the ORM object) because we need to create
    the database objects in the main thread.

    Args:
        prompt: The prompt to send
        model: The model to use

    Returns:
        Dict with all result fields
    """
    llm_response = await call_anthropic(prompt, model=model)

    return {
        "prompt": prompt,
        "response": llm_response.response_text if not llm_response.error else None,
        "ttft_ms": llm_response.ttft_ms,
        "latency_ms": llm_response.latency_ms,
        "tokens_per_second": llm_response.tokens_per_second,
        "input_tokens": llm_response.input_tokens,
        "output_tokens": llm_response.output_tokens,
        "cost_usd": llm_response.cost_usd,
        "error": llm_response.error,
    }


async def run_benchmark_async(
    db: Session,
    benchmark: Benchmark,
    prompts: list[str],
) -> Benchmark:
    """
    Execute a benchmark by running all prompts concurrently.

    Args:
        db: Database session
        benchmark: The Benchmark record to run
        prompts: List of prompts to test

    Returns:
        Updated Benchmark with results

    Flow:
        1. Mark benchmark as "running"
        2. Create async tasks for each prompt
        3. Run all tasks concurrently with asyncio.gather()
        4. Save all results to database
        5. Mark benchmark as "completed"
    """
    # Update status to running
    benchmark.status = "running"
    benchmark.started_at = datetime.utcnow()
    db.commit()

    # Create tasks for all prompts
    # Each task will call the LLM concurrently
    tasks = [
        run_single_prompt(prompt, benchmark.model)
        for prompt in prompts
    ]

    # Run all tasks concurrently
    # asyncio.gather() starts all tasks and waits for all to complete
    # return_exceptions=True means errors don't stop other tasks
    results_data = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and save to database
    errors = []
    for result_data in results_data:
        # Handle case where task raised an exception
        if isinstance(result_data, Exception):
            error_msg = str(result_data)
            errors.append(error_msg)
            # Create a failed result
            result = BenchmarkResult(
                benchmark_id=benchmark.id,
                prompt="(unknown - task failed)",
                error=error_msg,
            )
        else:
            # Normal result
            result = BenchmarkResult(
                benchmark_id=benchmark.id,
                prompt=result_data["prompt"],
                response=result_data["response"],
                ttft_ms=result_data["ttft_ms"],
                latency_ms=result_data["latency_ms"],
                tokens_per_second=result_data["tokens_per_second"],
                input_tokens=result_data["input_tokens"],
                output_tokens=result_data["output_tokens"],
                cost_usd=result_data["cost_usd"],
                error=result_data["error"],
            )
            if result_data["error"]:
                errors.append(result_data["error"])

        db.add(result)

    # Commit all results at once
    db.commit()

    # Update final status
    if len(errors) == len(prompts):
        benchmark.status = "failed"
    else:
        benchmark.status = "completed"

    benchmark.completed_at = datetime.utcnow()
    db.commit()

    # Refresh to get the results relationship populated
    db.refresh(benchmark)

    return benchmark


# Keep the sync wrapper for backward compatibility with the router
def run_benchmark(db: Session, benchmark: Benchmark, prompts: list[str]) -> Benchmark:
    """
    Sync wrapper around run_benchmark_async.

    FastAPI can call async functions directly, but if we need to call
    from sync code, this wrapper handles running the async function.

    Note: In production, you'd want the router to be async too.
    We'll update that next.
    """
    return asyncio.run(run_benchmark_async(db, benchmark, prompts))
