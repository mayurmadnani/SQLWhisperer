"""CLI script to exercise the agentic SQL pipeline outside Streamlit."""
from __future__ import annotations

from dotenv import load_dotenv
from rich import print
from rich.table import Table

from agentic_sql import config
from agentic_sql.agent import draft_sql, execute_sql, summarize_answer, validate_sql
from agentic_sql.database import fetch_schema_description
from agentic_sql.questions import get_questions
import random

load_dotenv()


def main() -> None:
    schema_doc = fetch_schema_description()
    for q in random.sample(get_questions(), k=5):
        print(f"\n[bold cyan]Question:[/bold cyan] {q}")
        draft = draft_sql(q, schema_doc)
        if not draft.sql_query:
            print(f"[red]Failed to draft SQL: {draft.reasoning}[/red]")
            continue
        print("[bold]Draft SQL:[/bold]\n", draft.sql_query)
        val = validate_sql(draft.sql_query, q, schema_doc)
        print(f"[bold]Validation:[/bold] {val.explanation}")
        sql_to_run = draft.sql_query
        if not val.is_valid and val.suggested_query:
            sql_to_run = val.suggested_query
            print("[yellow]Using suggested query[/yellow]\n", sql_to_run)
        elif not val.is_valid:
            print("[red]No valid query available[/red]")
            continue
        try:
            df = execute_sql(sql_to_run)
        except Exception as exc:  # safety errors etc.
            print(f"[red]Execution error:[/red] {exc}")
            continue
        tbl = Table(title="Result preview", show_lines=False)
        for col in df.columns:
            tbl.add_column(str(col))
        for _, row in df.head(config.DATA_SAMPLE_SIZE).iterrows():
            tbl.add_row(*[str(v) for v in row.tolist()])
        print(tbl)
        summary = summarize_answer(q, sql_to_run, df)
        print("[green]Summary:[/green]", summary)


if __name__ == "__main__":
    main()
