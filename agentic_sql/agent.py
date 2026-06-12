"""Agentic workflow for translating natural language into SQL insights."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import pandas as pd

from . import config
from .database import get_engine
from .logging_util import logger
from .llm import LLMError, chat_json, chat_with_model


@dataclass
class SqlDraft:
    sql_query: str
    reasoning: str


@dataclass
class SqlValidation:
    is_valid: bool
    explanation: str
    suggested_query: Optional[str] = None
    severity: str = "info"  # one of: info|warning|error


def draft_sql(question: str, schema_doc: str) -> SqlDraft:
    """Ask the planner model for a candidate SQL query."""
    system_prompt = (
        "You are a senior analytics engineer writing safe PostgreSQL queries. "
        "Use ONLY the exact column names shown in the schema. Do not guess or invent column names. "
        "Prefer CTEs for readability when useful. Double-check every column name against the schema."
    )
    user_prompt = (
        "Given the schema below, translate the business question into a SQL query.\n\n"
        "**CRITICAL:** Use ONLY the exact column names listed in the schema tables. "
        "Review the sample data to understand the actual column structure.\n\n"
        f"Schema:\n{schema_doc}\n\n"
        f"Business question: {question}\n\n"
        "Respond in JSON with keys 'sql_query' and 'reasoning'. "
        "Verify every column name exists in the schema before responding."
    )
    format_schema: Dict = {
        "type": "object",
        "properties": {
            "sql_query": {"type": "string"},
            "reasoning": {"type": "string"},
        },
        "required": ["sql_query"],
    }
    try:
        parsed = chat_json(
            model=config.DRAFT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=format_schema,
            temperature=config.DRAFT_TEMPERATURE,
        )
    except LLMError as exc:
        return SqlDraft(sql_query="", reasoning=str(exc))
    return SqlDraft(
        sql_query=parsed.get("sql_query", ""),
        reasoning=parsed.get("reasoning", ""),
    )


def validate_sql(sql_text: str, question: str, schema_doc: str) -> SqlValidation:
    """Ask the smaller validator model to inspect SQL for safety and correctness."""
    system_prompt = (
        "You are a meticulous SQL reviewer. Validate PostgreSQL queries for correctness and safety. "
        "Your primary task is to verify that ALL column names in the query exist exactly as shown in the schema."
    )
    user_prompt = (
        "Review the SQL statement for the given question and schema.\n\n"
        "**Validation Checklist:**\n"
        "1. Verify EVERY column name exists exactly in the schema (case-sensitive check)\n"
        "2. Check all table names are correct\n"
        "3. Validate JOIN conditions reference real columns\n"
        "4. Ensure query is read-only (SELECT/WITH only)\n"
        "5. Check for syntax errors\n\n"
        "If ANY column name is wrong or doesn't exist, set is_valid to false and provide a corrected query.\n\n"
        f"Schema:\n{schema_doc}\n\n"
        f"Question:\n{question}\n\n"
        f"SQL to review:\n{sql_text}\n\n"
        "Return JSON with keys 'is_valid' (boolean), 'explanation', and 'suggested_query' (corrected SQL if needed, or null)."
    )
    format_schema: Dict = {
        "type": "object",
        "properties": {
            "is_valid": {"type": "boolean"},
            "explanation": {"type": "string"},
            "suggested_query": {"type": "string"},
        },
        "required": ["is_valid", "explanation"],
    }
    try:
        parsed = chat_json(
            model=config.VALIDATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=format_schema,
            temperature=config.VALIDATION_TEMPERATURE,
        )
    except LLMError as exc:
        return SqlValidation(is_valid=False, explanation=str(exc))

    is_valid = bool(parsed.get("is_valid", False))
    explanation = parsed.get("explanation") or "Query reviewed — no explanation provided."
    suggested_query = parsed.get("suggested_query")
    severity = "info"
    if not is_valid and suggested_query:
        severity = "warning"
    elif not is_valid:
        severity = "error"
    return SqlValidation(
        is_valid=is_valid,
        explanation=explanation,
        suggested_query=suggested_query,
        severity=severity,
    )


READ_ONLY_PREFIXES = ("select", "with")


def _strip_leading_comments(sql_text: str) -> str:
    lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    return "\n".join(lines)


def _sanitize(sql_text: str) -> str:
    """Basic safety: enforce single statement, strip semicolon, ensure read-only."""
    sql_text = _strip_leading_comments(sql_text)
    cleaned = sql_text.strip().rstrip(";")
    lowered = cleaned.lower().lstrip()
    if not any(lowered.startswith(p) for p in READ_ONLY_PREFIXES):
        raise ValueError("Only read-only SELECT/WITH queries are permitted in this demo")
    if ";" in cleaned:
        raise ValueError("Multiple statements are not allowed")
    return cleaned


def execute_sql(sql_text: str) -> pd.DataFrame:
    """Run the validated SQL against the demo database (read-only)."""
    engine = get_engine()
    safe_sql = _sanitize(sql_text)
    if config.DEBUG_SQL:
        logger.info("Executing SQL: %s", safe_sql)
    return pd.read_sql_query(safe_sql, engine)


def explain_sql(sql_text: str) -> Tuple[str, str]:
    """Return (plan_json, raw_sql) using EXPLAIN (FORMAT JSON)."""
    engine = get_engine()
    safe_sql = _sanitize(sql_text)
    explain_clause = "EXPLAIN (FORMAT JSON) " + safe_sql
    if config.EXPLAIN_ANALYZE:
        explain_clause = "EXPLAIN (ANALYZE, FORMAT JSON) " + safe_sql
    raw_conn = engine.raw_connection()
    try:
        cur = raw_conn.cursor()
        cur.execute(explain_clause)
        rows = cur.fetchall()
    finally:
        raw_conn.close()
    # PostgreSQL returns JSON as a Python list/dict already parsed by psycopg2
    plan = rows[0][0] if rows else []
    # Return as JSON string for display
    return json.dumps(plan, indent=2), safe_sql


def summarize_answer(question: str, sql_text: str, result_df: pd.DataFrame) -> str:
    """Summarize the result set for a business stakeholder."""
    preview = result_df.head(config.DATA_SAMPLE_SIZE).to_markdown(index=False)
    stats = {
        "rowcount": len(result_df),
        "columns": list(result_df.columns),
    }
    system_prompt = (
        "Analyze the query results and provide a concise business summary. "
        "Focus on the actual data values, key findings, and comparisons. "
        "Do not describe the query or acknowledge instructions."
    )
    user_prompt = (
        f"Business question: {question}\n\n"
        f"Data results:\n{preview}\n\n"
        f"Total rows: {stats['rowcount']}\n\n"
        "Write a 2-4 sentence summary that:\n"
        "- States specific numbers and findings from the data\n"
        "- Identifies highest/lowest values or notable patterns\n"
        "- Compares values across rows if applicable\n"
        "- Uses plain business language\n\n"
        "Start directly with the findings, not with phrases like 'I understand' or 'Let me analyze'."
    )
    try:
        return chat_with_model(
            model=config.SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=config.SUMMARY_TEMPERATURE,
        )
    except LLMError as exc:
        return f"Summary unavailable: {exc}"

MAX_SQL_RETRIES = config.MAX_SQL_RETRIES


def repair_sql(
    question: str,
    schema_doc: str,
    failed_sql: str,
    error_msg: str,
) -> SqlDraft:
    """Ask the planner model to fix a SQL query given the database error it produced."""
    system_prompt = (
        "You are a senior analytics engineer fixing broken PostgreSQL queries. "
        "You are given the original query and the exact database error it raised. "
        "Produce a corrected SQL query that avoids the error. "
        "Use ONLY the exact column and table names shown in the schema."
    )
    user_prompt = (
        f"Schema:\n{schema_doc}\n\n"
        f"Business question: {question}\n\n"
        f"Failed SQL:\n{failed_sql}\n\n"
        f"Database error:\n{error_msg}\n\n"
        "Respond in JSON with keys 'sql_query' and 'reasoning'. "
        "The sql_query must be a corrected SELECT query that fixes the error above."
    )
    format_schema: Dict = {
        "type": "object",
        "properties": {
            "sql_query": {"type": "string"},
            "reasoning": {"type": "string"},
        },
        "required": ["sql_query"],
    }
    try:
        parsed = chat_json(
            model=config.DRAFT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=format_schema,
            temperature=config.DRAFT_TEMPERATURE,
        )
    except LLMError as exc:
        return SqlDraft(sql_query="", reasoning=str(exc))
    return SqlDraft(
        sql_query=parsed.get("sql_query", ""),
        reasoning=parsed.get("reasoning", ""),
    )


__all__ = [
    "SqlDraft",
    "SqlValidation",
    "MAX_SQL_RETRIES",
    "draft_sql",
    "validate_sql",
    "execute_sql",
    "explain_sql",
    "summarize_answer",
    "repair_sql",
]
