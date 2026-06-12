# SQLWhisperer

A Streamlit application that translates natural language business questions into validated SQL queries, executes them against a PostgreSQL warehouse, and narrates the results using LLMs.

## Features

- **Multi-model pipeline** — separate models for drafting, validating, and summarizing SQL.
- **Two LLM backends** — Ollama (local) or Docker Model Runner (Docker Desktop ≥ 4.40).
- **Auto-repair loop** — if SQL execution fails, the agent retries with the DB error as context (configurable retries).
- **Validation severity** — info / warning / error banners with optional corrected query.
- **Read-only safety layer** — blocks multi-statement and non-`SELECT` queries at both the app and DB level.
- **EXPLAIN plan toggle** — optional `EXPLAIN (FORMAT JSON)` or `EXPLAIN ANALYZE` view.
- **Real PostgreSQL** — seeded demo schema with customers, products, orders, and support tickets.

---

## Quick Start

### 1. Start the database

```bash
docker compose -f docker/docker-compose.yml up -d postgres
```

### 2. Start an LLM backend

**Option A — Ollama**
```bash
ollama pull gemma4:12b
ollama pull llama3:8b
ollama pull gemma3:4b
```
Ollama serves on `http://localhost:11434` by default.

**Option B — Docker Model Runner**
```bash
docker model pull ai/gemma4:12B
docker model pull ai/llama3.1:8B-F16
docker model pull ai/gemma3:4B
```
Set `MODEL_BACKEND=docker` and optionally `DRAFT_MODEL`, `VALIDATION_MODEL`, `SUMMARY_MODEL`
to match the model names available in Docker Model Runner.

### 3. (Optional) Edit configuration

```bash
# All settings live in config.yaml at the project root.
# Edit it directly, or override any value with an environment variable.
# Point to a different file with CONFIG_FILE=/path/to/custom.yaml
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the app

```bash
streamlit run app.py
```

---

## Running Tests

```bash
# From the project root (conftest.py makes agentic_sql importable):
pytest tests/

# Verbose output:
pytest -v tests/

# Skip DB-dependent tests when Postgres is not running:
pytest tests/ -k "not explain"
```

Tests that require a live database (`test_explain.py`) are automatically skipped when the DB is unavailable.

---

## Configuration

All settings live in [config.yaml](config.yaml). Edit that file directly, or override any value with an environment variable (env vars take precedence). Point to a different file with `CONFIG_FILE=/path/to/custom.yaml`.

| YAML key | Env var override | Default | Purpose |
|----------|-----------------|---------|---------|
| `database_url` | `DATABASE_URL` | `postgresql+psycopg2://agentic:agentic@localhost:5433/agenticdb` | SQLAlchemy connection string |
| `backend` | `MODEL_BACKEND` | `ollama` | LLM backend: `ollama` or `docker` |
| `ollama.api_url` | `OLLAMA_API_URL` | `http://localhost:11434/api/chat` | Ollama chat endpoint |
| `docker.model_runner_url` | `DOCKER_MODEL_RUNNER_URL` | `http://localhost:12434/engines/llm/v1/chat/completions` | Docker Model Runner endpoint |
| `models.draft` | `DRAFT_MODEL` | `gemma3:4b` | SQL planner model |
| `models.validation` | `VALIDATION_MODEL` | `gemma3:4b` | SQL validator model |
| `models.summary` | `SUMMARY_MODEL` | `gemma3:270m` | Narrative summarizer model |
| `timeout` | `LLM_TIMEOUT` | `90` | Request timeout in seconds |
| `data_sample_size` | `DATA_SAMPLE_SIZE` | `10` | Rows shown in dataset previews |
| `max_sql_retries` | `MAX_SQL_RETRIES` | `2` | Max automatic repair attempts on execution failure |
| `streaming` | `STREAMING` | `false` | Enable Ollama streaming responses |
| `debug_sql` | `DEBUG_SQL` | `false` | Log SQL before execution |
| `explain_analyze` | `EXPLAIN_ANALYZE` | `false` | Include ANALYZE in EXPLAIN (adds runtime metrics) |
| `temperature.draft` | `DRAFT_TEMPERATURE` | `0.4` | Temperature for SQL drafting |
| `temperature.validation` | `VALIDATION_TEMPERATURE` | `0.1` | Temperature for SQL validation |
| `temperature.summary` | `SUMMARY_TEMPERATURE` | `0.3` | Temperature for narrative summarization |

---

## Architecture

```
app.py (Streamlit UI)
  └── agentic_sql.agent
        ├── draft_sql()          — planner model generates SQL
        ├── validate_sql()       — validator model reviews SQL
        ├── repair_sql()         — planner fixes SQL given a DB error
        ├── execute_sql()        — sanitize + run against PostgreSQL
        ├── explain_sql()        — EXPLAIN (FORMAT JSON) plan
        └── summarize_answer()   — summarizer produces business narrative
  └── agentic_sql.llm
        ├── _chat_ollama()       — Ollama /api/chat backend
        └── _chat_openai_compat() — Docker Model Runner /v1/chat/completions backend
  └── agentic_sql.database      — schema introspection, sample data, query execution
  └── agentic_sql.config        — environment-driven settings
```

### Request flow

1. User question → `draft_sql()` → candidate SQL + reasoning
2. `validate_sql()` → severity (info / warning / error) + optional corrected query
3. `execute_sql()` → result DataFrame; on failure, `repair_sql()` retries up to `MAX_SQL_RETRIES`
4. Optional `explain_sql()` → EXPLAIN JSON plan
5. `summarize_answer()` → business narrative
6. `summarize_answer()` → business narrative

---

## Database Schema (demo)

| Table | Key Columns |
|-------|-------------|
| `customers` | customer_id, name, city, loyalty_tier |
| `products` | product_id, name, category, unit_price |
| `orders` | order_id, customer_id FK, product_id FK, order_date, quantity |
| `support_tickets` | ticket_id, customer_id FK, topic, created_at, status |

The `agentic` role is granted `SELECT` only — write operations are blocked at the database level.

---

## Safety Notes

- Generated SQL is validated by a second model before execution.
- A local sanitizer enforces single-statement, read-only (`SELECT`/`WITH`) queries.
- The database role has no `INSERT`/`UPDATE`/`DELETE` privileges.

---
