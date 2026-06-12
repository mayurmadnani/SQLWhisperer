"""Database helpers for the Agentic SQL demo."""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, Iterable, List

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import DATA_SAMPLE_SIZE, DATABASE_URL
from .logging_util import logger

DEMO_TABLES = ("customers", "products", "orders", "support_tickets")


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create (and cache) a SQLAlchemy engine for the demo database."""
    return create_engine(DATABASE_URL, pool_pre_ping=True, future=True)


@lru_cache(maxsize=1)
def fetch_schema_description() -> str:
    """Generate a detailed schema summary with column names, types, sample data, and relationships."""
    engine = get_engine()
    
    # Fetch column info
    col_query = text(
        """
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name ASC, ordinal_position ASC
        """
    )
    df = pd.read_sql_query(col_query, engine)
    
    # Fetch primary keys
    pk_query = text(
        """
        SELECT tc.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'public'
        """
    )
    pk_df = pd.read_sql_query(pk_query, engine)
    
    # Fetch foreign keys
    fk_query = text(
        """
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
        """
    )
    fk_df = pd.read_sql_query(fk_query, engine)
    
    lines: List[str] = ["# Database Schema (PostgreSQL)\n"]
    
    # Group columns by table
    for table_name in df["table_name"].unique():
        table_cols = df[df["table_name"] == table_name]
        lines.append(f"\n## Table: {table_name}\n")
        
        # Column details table
        lines.append("| Column Name | Type | Nullable |")
        lines.append("|-------------|------|----------|")
        for _, row in table_cols.iterrows():
            lines.append(f"| {row['column_name']} | {row['data_type']} | {row['is_nullable']} |")
        
        # Primary keys
        table_pks = pk_df[pk_df["table_name"] == table_name]
        if not table_pks.empty:
            pk_cols = ", ".join(table_pks["column_name"].tolist())
            lines.append(f"\n**Primary Key:** {pk_cols}")
        
        # Foreign keys
        table_fks = fk_df[fk_df["table_name"] == table_name]
        if not table_fks.empty:
            lines.append("\n**Foreign Keys:**")
            for _, fk in table_fks.iterrows():
                lines.append(
                    f"- {fk['column_name']} → {fk['foreign_table_name']}.{fk['foreign_column_name']}"
                )
        
        # Sample data
        try:
            sample_query = text(f"SELECT * FROM {table_name} LIMIT 3")
            sample_df = pd.read_sql_query(sample_query, engine)
            if not sample_df.empty:
                lines.append(f"\n**Sample data:**")
                lines.append("```")
                # Show column headers
                lines.append(" | ".join(sample_df.columns))
                lines.append("-" * (sum(len(col) for col in sample_df.columns) + 3 * len(sample_df.columns)))
                # Show sample rows
                for _, sample_row in sample_df.iterrows():
                    lines.append(" | ".join(str(val) for val in sample_row))
                lines.append("```")
        except Exception as exc:
            logger.warning("Sample data unavailable for %s: %s", table_name, exc)
    
    return "\n".join(lines)


def sample_table(table_name: str, limit: int | None = None) -> pd.DataFrame:
    """Fetch a preview of a demo table."""
    if table_name not in DEMO_TABLES:
        raise ValueError(f"Unknown demo table: {table_name}")
    engine = get_engine()
    query = text(f"SELECT * FROM {table_name} ORDER BY 1 LIMIT :limit")
    rows = pd.read_sql_query(query, engine, params={"limit": limit or DATA_SAMPLE_SIZE})
    return rows


def list_tables() -> Iterable[str]:
    """List the demo tables exposed in the UI."""
    return DEMO_TABLES

__all__ = [
    "get_engine",
    "fetch_schema_description",
    "sample_table",
    "list_tables",
    "DEMO_TABLES",
]
