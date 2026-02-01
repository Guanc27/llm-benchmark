# LLM Benchmark API

A FastAPI-based platform for benchmarking LLM inference performance. Measure latency, throughput, and cost across providers with precision timing metrics.

## Why This Exists

Every team integrating LLMs faces the same questions:
- Which model is fastest for my use case?
- What's my actual cost per request?
- How does latency vary with prompt complexity?
- What's the Time to First Token (TTFT) for streaming responses?

This tool answers those questions with real data and persistent storage for historical analysis.

## Features

- **Streaming Support**: Measures Time to First Token (TTFT) using streaming responses
- **Async Execution**: Runs multiple prompts concurrently for faster benchmarking
- **Persistent Storage**: SQLite/PostgreSQL database stores all results for historical analysis
- **REST API**: Clean API with auto-generated Swagger documentation
- **Cost Tracking**: Calculates USD cost based on token usage and model pricing

## Metrics Captured

| Metric | Description |
|--------|-------------|
| **TTFT (Time to First Token)** | Milliseconds until first token arrives - critical for UX |
| **Total Latency** | End-to-end request time in milliseconds |
| **Tokens Per Second** | Output generation speed after first token |
| **Input/Output Tokens** | Token counts from API response |
| **Cost (USD)** | Estimated cost based on model pricing |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Client                                      │
│                    (Browser / curl / Application)                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP/JSON
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Server                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │ POST /benchmarks│  │ GET /benchmarks │  │ GET /benchmarks/{id}    │  │
│  │ (create & run)  │  │ (list all)      │  │ (get with results)      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                │                                          │
                │                                          │
                ▼                                          ▼
┌───────────────────────────┐              ┌───────────────────────────────┐
│   Anthropic SDK           │              │   SQLite / PostgreSQL         │
│   (Async Streaming)       │              │   (Persistent Storage)        │
│                           │              │                               │
│   - Streaming responses   │              │   benchmarks                  │
│   - TTFT measurement      │              │   ├── id, name, model         │
│   - Token counting        │              │   ├── status, timestamps      │
│                           │              │   └── results (1:many)        │
└───────────────────────────┘              │       ├── prompt, response    │
                │                          │       ├── ttft_ms, latency_ms │
                │                          │       └── tokens, cost        │
                ▼                          └───────────────────────────────┘
┌───────────────────────────┐
│   Anthropic API           │
│   (Claude Models)         │
└───────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key ([get one here](https://console.anthropic.com))

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/llm-benchmark.git
cd llm-benchmark

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Run the Server

```bash
uvicorn src.main:app --reload
```

### Open the API Docs

Visit: **http://localhost:8000/docs**

You'll see interactive Swagger UI documentation.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/benchmarks` | Create and run a new benchmark |
| `GET` | `/benchmarks` | List all benchmarks (paginated) |
| `GET` | `/benchmarks/{id}` | Get benchmark with full results |
| `DELETE` | `/benchmarks/{id}` | Delete a benchmark |
| `GET` | `/health` | Health check endpoint |

## Usage Examples

### Create a Benchmark

```bash
curl -X POST http://localhost:8000/benchmarks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Haiku Speed Test",
    "model": "claude-3-haiku-20240307",
    "prompts": [
      "Say hello in exactly 3 words",
      "What is 2+2?",
      "Explain quantum computing in one sentence"
    ]
  }'
```

### Response

```json
{
  "id": 1,
  "name": "Haiku Speed Test",
  "model": "claude-3-haiku-20240307",
  "status": "completed",
  "created_at": "2025-01-15T10:30:00Z",
  "started_at": "2025-01-15T10:30:00Z",
  "completed_at": "2025-01-15T10:30:02Z",
  "results": [
    {
      "id": 1,
      "prompt": "Say hello in exactly 3 words",
      "response": "Hello there, friend!",
      "ttft_ms": 142.5,
      "latency_ms": 823.4,
      "tokens_per_second": 48.2,
      "input_tokens": 18,
      "output_tokens": 5,
      "cost_usd": 0.000011,
      "error": null
    },
    {
      "id": 2,
      "prompt": "What is 2+2?",
      "response": "2 + 2 = 4",
      "ttft_ms": 138.2,
      "latency_ms": 654.1,
      "tokens_per_second": 52.1,
      "input_tokens": 12,
      "output_tokens": 8,
      "cost_usd": 0.000013,
      "error": null
    }
  ]
}
```

## Supported Models

| Provider | Model | Input Cost | Output Cost |
|----------|-------|------------|-------------|
| Anthropic | `claude-3-haiku-20240307` | $0.25/1M | $1.25/1M |
| Anthropic | `claude-3-5-haiku-20241022` | $0.80/1M | $4.00/1M |
| Anthropic | `claude-3-5-sonnet-20241022` | $3.00/1M | $15.00/1M |
| Anthropic | `claude-3-opus-20240229` | $15.00/1M | $75.00/1M |

## Project Structure

```
llm-benchmark/
├── src/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Environment configuration (pydantic-settings)
│   ├── database.py          # SQLAlchemy engine and session management
│   ├── models.py            # Database models (Benchmark, BenchmarkResult)
│   ├── schemas.py           # Pydantic schemas for API validation
│   ├── routers/
│   │   └── benchmarks.py    # REST API endpoints
│   └── services/
│       ├── anthropic_client.py   # Async streaming LLM client
│       └── benchmark_runner.py   # Orchestrates concurrent benchmark execution
├── tests/
│   └── test_benchmarks.py   # Pytest test suite
├── docker-compose.yml       # PostgreSQL for production
├── pyproject.toml           # Python dependencies
├── .env.example             # Environment template
└── README.md
```

## Key Design Decisions

### 1. Async + Concurrent Execution
Prompts run concurrently using `asyncio.gather()`, not sequentially. A benchmark with 5 prompts takes ~2 seconds, not ~10 seconds.

### 2. Streaming for TTFT
We use streaming responses to measure Time to First Token accurately. This metric is critical for user-facing applications where perceived latency matters.

### 3. Separation of Concerns
- **Routers**: Handle HTTP (request/response, status codes)
- **Services**: Handle business logic (LLM calls, timing)
- **Models**: Handle persistence (database schemas)

### 4. Database Abstraction
Works with SQLite (zero setup) or PostgreSQL (production scale). Same codebase, different connection string.

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./llm_benchmark.db` |
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Required |

### Using PostgreSQL (Production)

```bash
# Start PostgreSQL with Docker
docker-compose up -d

# Update .env
DATABASE_URL=postgresql://benchmark:benchmark@localhost:5432/llm_benchmark
```

## Understanding the Metrics

### Time to First Token (TTFT)

```
Request ─────────────────────────────────────────────────▶ Response Complete
         │                                               │
         │◄─── TTFT ───►│◄───── Generation Time ────────►│
         │    (150ms)   │          (700ms)               │
         │              │                                │
       Request      First token                     Last token
        sent         appears                        arrives
```

**Why TTFT matters**: Users perceive an app as "fast" when they see immediate feedback. A 150ms TTFT feels snappy even if total latency is 2 seconds.

### Tokens Per Second (TPS)

```
TPS = output_tokens / generation_time
    = output_tokens / (total_latency - ttft)
```

We subtract TTFT because it's "thinking time" before generation starts.

## Roadmap

- [ ] Add OpenAI provider support
- [ ] Add concurrent request load testing
- [ ] P50/P95/P99 latency percentiles
- [ ] Web dashboard for visualization
- [ ] Export results to CSV
- [ ] Webhook notifications on completion
- [ ] Background job queue (Redis + RQ)

## Tech Stack

| Component | Technology |
|-----------|------------|
| Web Framework | FastAPI |
| Database ORM | SQLAlchemy 2.0 |
| Validation | Pydantic 2.0 |
| LLM Client | Anthropic SDK (async) |
| Server | Uvicorn (ASGI) |
| Database | SQLite / PostgreSQL |

