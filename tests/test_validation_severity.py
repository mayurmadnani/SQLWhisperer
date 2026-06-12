import pytest
from agentic_sql import agent as agent_module

class DummyError(Exception):
    pass


def test_severity_info(monkeypatch):
    def fake_chat_json(**kwargs):
        return {"is_valid": True, "explanation": "Looks good"}
    monkeypatch.setattr(agent_module, "chat_json", fake_chat_json)
    result = agent_module.validate_sql("SELECT 1", "Question", "Schema")
    assert result.severity == "info"
    assert result.is_valid


def test_severity_warning(monkeypatch):
    def fake_chat_json(**kwargs):
        return {"is_valid": False, "explanation": "Minor issue", "suggested_query": "SELECT 1"}
    monkeypatch.setattr(agent_module, "chat_json", fake_chat_json)
    result = agent_module.validate_sql("SELECT 1", "Question", "Schema")
    assert result.severity == "warning"
    assert not result.is_valid
    assert result.suggested_query == "SELECT 1"


def test_severity_error(monkeypatch):
    def fake_chat_json(**kwargs):
        return {"is_valid": False, "explanation": "Broken"}
    monkeypatch.setattr(agent_module, "chat_json", fake_chat_json)
    result = agent_module.validate_sql("SELECT 1", "Question", "Schema")
    assert result.severity == "error"
    assert not result.is_valid
    assert result.suggested_query is None
