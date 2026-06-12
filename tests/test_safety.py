from agentic_sql.agent import _sanitize, READ_ONLY_PREFIXES
import pytest


def test_sanitize_allows_select():
    assert _sanitize("SELECT 1") == "SELECT 1"


def test_sanitize_rejects_update():
    with pytest.raises(ValueError):
        _sanitize("UPDATE customers SET city='X' WHERE customer_id=1")


def test_sanitize_strips_trailing_semicolon():
    assert _sanitize("SELECT 1;") == "SELECT 1"


def test_sanitize_ignores_leading_comments():
    sql = "-- comment\nSELECT 1"
    assert _sanitize(sql) == "SELECT 1"


def test_prefixes_defined():
    assert set(READ_ONLY_PREFIXES) == {"select", "with"}
