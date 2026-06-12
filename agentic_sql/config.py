"""Configuration — loaded from config.yaml; environment variables override any value."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_HERE = Path(__file__).parent          # agentic_sql/
_ROOT = _HERE.parent                   # project root
_CONFIG_PATH = Path(os.getenv("CONFIG_FILE", str(_ROOT / "config.yaml")))


def _load_yaml() -> dict:
    if _CONFIG_PATH.exists():
        with _CONFIG_PATH.open() as fh:
            return yaml.safe_load(fh) or {}
    return {}


_cfg = _load_yaml()


def _get(dotted_key: str, env_var: str, default: Any = None) -> Any:
    """Return: env var (if set) > YAML value (dotted path) > default."""
    env = os.getenv(env_var)
    if env is not None:
        return env
    node: Any = _cfg
    for key in dotted_key.split("."):
        if not isinstance(node, dict):
            return default
        node = node.get(key)
        if node is None:
            return default
    return node


def _bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).lower() in {"1", "true", "yes"}


# ── LLM backend ───────────────────────────────────────────────────────────
MODEL_BACKEND = _get("backend", "MODEL_BACKEND", "ollama")
OLLAMA_API_URL = _get("ollama.api_url", "OLLAMA_API_URL", "http://localhost:11434/api/chat")
DOCKER_MODEL_RUNNER_URL = _get(
    "docker.model_runner_url",
    "DOCKER_MODEL_RUNNER_URL",
    "http://localhost:12434/engines/llm/v1/chat/completions",
)

# ── Models ────────────────────────────────────────────────────────────────
DRAFT_MODEL = _get("models.draft", "DRAFT_MODEL", "gemma4:12b")
VALIDATION_MODEL = _get("models.validation", "VALIDATION_MODEL", "llama3:8b")
SUMMARY_MODEL = _get("models.summary", "SUMMARY_MODEL", "gemma3:4b")

# ── Temperatures ──────────────────────────────────────────────────────────
DRAFT_TEMPERATURE = float(_get("temperature.draft", "DRAFT_TEMPERATURE", "0.4"))
VALIDATION_TEMPERATURE = float(_get("temperature.validation", "VALIDATION_TEMPERATURE", "0.1"))
SUMMARY_TEMPERATURE = float(_get("temperature.summary", "SUMMARY_TEMPERATURE", "0.3"))

# ── Database ──────────────────────────────────────────────────────────────
DATABASE_URL = _get(
    "database_url",
    "DATABASE_URL",
    "postgresql+psycopg2://agentic:agentic@localhost:5433/agenticdb",
)

# ── Application ───────────────────────────────────────────────────────────
REQUEST_TIMEOUT = int(_get("timeout", "LLM_TIMEOUT", "90"))
DATA_SAMPLE_SIZE = int(_get("data_sample_size", "DATA_SAMPLE_SIZE", "10"))
MAX_SQL_RETRIES = int(_get("max_sql_retries", "MAX_SQL_RETRIES", "2"))

# ── Feature flags ─────────────────────────────────────────────────────────
STREAMING = _bool(_get("streaming", "STREAMING", False))
DEBUG_SQL = _bool(_get("debug_sql", "DEBUG_SQL", False))
EXPLAIN_ANALYZE = _bool(_get("explain_analyze", "EXPLAIN_ANALYZE", False))

__all__ = [
    "MODEL_BACKEND",
    "OLLAMA_API_URL",
    "DOCKER_MODEL_RUNNER_URL",
    "DRAFT_MODEL",
    "VALIDATION_MODEL",
    "SUMMARY_MODEL",
    "DRAFT_TEMPERATURE",
    "VALIDATION_TEMPERATURE",
    "SUMMARY_TEMPERATURE",
    "DATABASE_URL",
    "REQUEST_TIMEOUT",
    "DATA_SAMPLE_SIZE",
    "MAX_SQL_RETRIES",
    "STREAMING",
    "DEBUG_SQL",
    "EXPLAIN_ANALYZE",
]
