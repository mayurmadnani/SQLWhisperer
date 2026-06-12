import json as pyjson
import pytest

from agentic_sql.agent import explain_sql
from agentic_sql.config import EXPLAIN_ANALYZE


def _db_available():
    # Very lightweight availability heuristic: attempt a simple explain.
    try:
        plan, _ = explain_sql("SELECT 1")
        return bool(plan)
    except Exception:
        return False


@pytest.mark.skipif(not _db_available(), reason="Database not available for EXPLAIN test")
def test_explain_json_shape():
    plan, raw = explain_sql("SELECT 1")
    assert raw == "SELECT 1"  # sanitized
    # Plan is a JSON array string in Postgres FORMAT JSON
    data = pyjson.loads(plan)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "Plan" in data[0]


@pytest.mark.skipif(not _db_available(), reason="Database not available for EXPLAIN test")
def test_explain_analyze_flag():
    plan, _ = explain_sql("SELECT 1")
    # We cannot guarantee ANALYZE presence without running with flag; just ensure valid JSON
    data = pyjson.loads(plan)
    assert isinstance(data, list)
    # If ANALYZE flag is set, expect Actual Rows key somewhere
    if EXPLAIN_ANALYZE:
        # Traverse nested plan nodes for 'Actual Rows'
        def contains_actual(node):
            if isinstance(node, dict):
                if any(k.lower().startswith("actual") for k in node.keys()):
                    return True
                return any(contains_actual(v) for v in node.values())
            if isinstance(node, list):
                return any(contains_actual(x) for x in node)
            return False
        assert contains_actual(data)
