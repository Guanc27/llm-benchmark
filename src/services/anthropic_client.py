"""
Anthropic API client wrapper with async streaming support.

This module handles:
1. Sending prompts to Claude via streaming
2. Measuring Time to First Token (TTFT)
3. Measuring total latency
4. Calculating tokens per second and cost

Key concepts:
- async/await: Allows concurrent execution while waiting for API
- streaming: Receive tokens as they're generated, not all at once
- TTFT: Time from request sent to first token received
"""

import time
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from src.config import settings


@dataclass
class LLMResponse:
    """
    Structured response from an LLM call.

    All timing is in milliseconds for consistency.
    """

    response_text: str
    ttft_ms: float | None      # Time to First Token (None if not streaming)
    latency_ms: float          # Total request time
    tokens_per_second: float   # Output generation speed
    input_tokens: int
    output_tokens: int
    cost_usd: float
    error: str | None = None


# Pricing per million tokens (as of 2025)
# Source: https://www.anthropic.com/pricing
ANTHROPIC_PRICING = {
    # Claude 4 models
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    # Claude 3.5 models
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    # Claude 3 models
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate the cost of an API call based on token usage."""
    pricing = ANTHROPIC_PRICING.get(model, {"input": 3.00, "output": 15.00})
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


def calculate_tokens_per_second(
    output_tokens: int,
    total_time_seconds: float,
    ttft_seconds: float | None
) -> float:
    """
    Calculate tokens per second during generation phase.

    We subtract TTFT from total time because:
    - TTFT is "thinking" time before generation starts
    - TPS measures how fast tokens are generated AFTER the first one

    Timeline:
        [Request] ---TTFT--- [First Token] ---Generation--- [Last Token]
                             |<-------- TPS measured here -------->|
    """
    if output_tokens == 0:
        return 0.0

    if ttft_seconds is not None:
        # Generation time = total time minus time-to-first-token
        generation_time = total_time_seconds - ttft_seconds
    else:
        # If no TTFT (non-streaming), use total time
        generation_time = total_time_seconds

    if generation_time <= 0:
        return 0.0

    return output_tokens / generation_time


async def call_anthropic_streaming(
    prompt: str,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 1024,
) -> LLMResponse:
    """
    Send a prompt to Claude using streaming and measure performance.

    This function:
    1. Opens a streaming connection to Claude
    2. Records when the first token arrives (TTFT)
    3. Collects all tokens as they stream in
    4. Calculates final metrics when stream completes

    Args:
        prompt: The user prompt to send
        model: Which Claude model to use
        max_tokens: Maximum tokens in response

    Returns:
        LLMResponse with text, timing, and token metrics
    """
    # Create async client
    # AsyncAnthropic is the async version of the Anthropic client
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Track timing
    start_time = time.perf_counter()
    first_token_time: float | None = None

    # Collect streamed text
    response_text = ""

    try:
        # Open streaming connection
        # 'async with' ensures the stream is properly closed when done
        async with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:

            # Iterate over tokens as they arrive
            # 'async for' yields each chunk without blocking other tasks
            async for text in stream.text_stream:
                # Record TTFT on first non-empty chunk
                if first_token_time is None and text:
                    first_token_time = time.perf_counter()

                response_text += text

            # Get final message with usage stats
            # This is available after the stream completes
            final_message = await stream.get_final_message()

        # Calculate timing
        end_time = time.perf_counter()
        total_time_seconds = end_time - start_time
        ttft_seconds = (first_token_time - start_time) if first_token_time else None

        # Extract token counts
        input_tokens = final_message.usage.input_tokens
        output_tokens = final_message.usage.output_tokens

        # Calculate derived metrics
        tps = calculate_tokens_per_second(output_tokens, total_time_seconds, ttft_seconds)
        cost = calculate_cost(model, input_tokens, output_tokens)

        return LLMResponse(
            response_text=response_text,
            ttft_ms=ttft_seconds * 1000 if ttft_seconds else None,
            latency_ms=total_time_seconds * 1000,
            tokens_per_second=tps,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            error=None,
        )

    except Exception as e:
        # Handle errors gracefully
        end_time = time.perf_counter()
        total_time_seconds = end_time - start_time

        return LLMResponse(
            response_text="",
            ttft_ms=None,
            latency_ms=total_time_seconds * 1000,
            tokens_per_second=0.0,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            error=str(e),
        )


# Alias for cleaner imports
call_anthropic = call_anthropic_streaming
