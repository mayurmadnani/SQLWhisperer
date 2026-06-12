import streamlit as st

from agentic_sql import config
from agentic_sql.agent import (
    MAX_SQL_RETRIES,
    SqlDraft,
    draft_sql,
    execute_sql,
    explain_sql,
    repair_sql,
    summarize_answer,
    validate_sql,
)
from agentic_sql.database import fetch_schema_description, list_tables, sample_table
from agentic_sql.questions import get_questions


@st.cache_data(show_spinner=False)
def cached_schema_doc() -> str:
    """Avoid recomputing the schema markdown on every rerun."""
    return fetch_schema_description()


def render_sidebar() -> None:
    st.sidebar.header("Models in play")
    st.sidebar.markdown(
        f"- **Backend:** `{config.MODEL_BACKEND}`\n"
        f"- **Draft:** `{config.DRAFT_MODEL}` (plans SQL queries)\n"
        f"- **Validation:** `{config.VALIDATION_MODEL}` (reviews SQL)\n"
        f"- **Summary:** `{config.SUMMARY_MODEL}` (narrates results)"
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Try these questions:**")
    for q in get_questions():
        st.sidebar.code(q)


def render_dataset_preview() -> None:
    st.markdown("### Demo datasets")
    for table in list_tables():
        try:
            df = sample_table(table)
        except Exception as exc:  # pragma: no cover - surfaced in UI
            st.error(f"Failed to load preview for {table}: {exc}")
            continue
        with st.expander(table):
            st.dataframe(df, use_container_width=True)


def _run_with_repair(
    question: str,
    schema_doc: str,
    candidate_sql: str,
) -> tuple[object, str] | tuple[None, None]:
    """Execute SQL, retrying up to MAX_SQL_RETRIES times via the repair agent.

    Returns (result_df, final_sql) on success, or (None, None) after exhausting retries.
    """
    current_sql = candidate_sql
    for attempt in range(MAX_SQL_RETRIES + 1):
        try:
            result_df = execute_sql(current_sql)
            return result_df, current_sql
        except Exception as exc:
            error_msg = str(exc)
            if attempt == MAX_SQL_RETRIES:
                st.error(
                    f"SQL execution failed after {MAX_SQL_RETRIES} repair attempt(s). "
                    f"Last error: {error_msg}"
                )
                return None, None
            st.warning(
                f"Execution error (attempt {attempt + 1}/{MAX_SQL_RETRIES + 1}): "
                f"{error_msg}\n\nAsking agent to repair…"
            )
            with st.spinner(f"Repairing SQL (attempt {attempt + 2})…"):
                repaired: SqlDraft = repair_sql(question, schema_doc, current_sql, error_msg)
            if not repaired.sql_query:
                st.error("Repair agent returned an empty query. Aborting.")
                return None, None
            current_sql = repaired.sql_query
            st.markdown("##### Repaired SQL")
            st.code(current_sql, language="sql")
            if repaired.reasoning:
                st.markdown(f"**Repair notes:** {repaired.reasoning}")
    return None, None  # unreachable but satisfies type checker


def main() -> None:
    st.set_page_config(page_title="Agentic SQL Demo", page_icon="🧠", layout="wide")
    st.title("Agentic SQL Demo")
    st.caption(
        f"Models: draft `{config.DRAFT_MODEL}` · validate `{config.VALIDATION_MODEL}` · "
        f"summarize `{config.SUMMARY_MODEL}` · backend `{config.MODEL_BACKEND}`"
    )

    render_sidebar()

    try:
        schema_doc = cached_schema_doc()
    except Exception as exc:  # pragma: no cover - surfaced in UI
        st.error(f"Unable to fetch schema description: {exc}")
        return
    with st.expander("See schema context"):
        st.code(schema_doc)

    render_dataset_preview()

    st.markdown("---")
    question = st.text_area("Ask a question in natural language", height=100)
    col_run, col_explain = st.columns([1, 1])
    trigger = col_run.button("Run agent", type="primary")
    want_explain = col_explain.checkbox("Show EXPLAIN plan", value=False)

    if trigger and question.strip():
        with st.spinner(f"Drafting SQL with {config.DRAFT_MODEL}..."):
            draft = draft_sql(question, schema_doc)
        if not draft.sql_query:
            st.error("Planner did not return a SQL query. Check model logs and retry.")
            if draft.reasoning:
                st.info(draft.reasoning)
            return

        st.markdown("#### SQL draft")
        st.code(draft.sql_query, language="sql")
        if draft.reasoning:
            st.markdown(f"**Model notes:** {draft.reasoning}")

        with st.spinner(f"Validating with {config.VALIDATION_MODEL}..."):
            validation = validate_sql(draft.sql_query, question, schema_doc)
        st.markdown("#### Validation")
        if validation.severity == "warning":
            st.warning(validation.explanation)
        elif validation.severity == "error":
            st.error(validation.explanation)
        else:
            st.info(validation.explanation)

        candidate_sql = draft.sql_query
        if not validation.is_valid and validation.suggested_query:
            st.warning("Using validator's suggested query")
            candidate_sql = validation.suggested_query
            st.code(candidate_sql, language="sql")
        elif not validation.is_valid:
            st.error("Validation failed and no alternative was provided. Adjust the question and retry.")
            return

        result_df, final_sql = _run_with_repair(question, schema_doc, candidate_sql)
        if result_df is None:
            return

        st.markdown("#### Query result")
        st.dataframe(result_df, use_container_width=True)

        if want_explain:
            try:
                with st.spinner("Generating EXPLAIN plan..."):
                    plan_json, raw_sql = explain_sql(final_sql)
                with st.expander("EXPLAIN plan (JSON)"):
                    st.code(plan_json, language="json")
            except Exception as exc:  # pragma: no cover
                st.error(f"EXPLAIN failed: {exc}")

        with st.spinner(f"Summarizing with {config.SUMMARY_MODEL}..."):
            summary = summarize_answer(question, final_sql, result_df)
        st.markdown("#### Narrative summary")
        st.write(summary)

        st.success("Agentic flow complete.")

    elif trigger:
        st.warning("Please supply a question before running the agent.")


if __name__ == "__main__":
    main()
