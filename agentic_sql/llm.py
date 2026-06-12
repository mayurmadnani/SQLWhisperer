"""LLM client utilities supporting Ollama and Docker Model Runner backends."""

from __future__ import annotations

import json
from typing import Dict, List, Optional

import requests

from . import config
from .logging_util import logger


class LLMError(RuntimeError):
    """Raised when the LLM API call fails."""


# ---------------------------------------------------------------------------
# Ollama backend  (/api/chat)
# ---------------------------------------------------------------------------

def _chat_ollama(
    model: str,
    messages: List[Dict[str, str]],
    response_format: Optional[Dict] = None,
    temperature: Optional[float] = None,
) -> str:
    payload: Dict = {"model": model, "messages": messages, "stream": False}
    if response_format:
        payload["format"] = response_format
    if temperature is not None:
        payload.setdefault("options", {})["temperature"] = temperature
    response = requests.post(config.OLLAMA_API_URL, json=payload, timeout=config.REQUEST_TIMEOUT)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:  # pragma: no cover - surfaced in UI
        raise LLMError(str(exc)) from exc
    data = response.json()
    message = data.get("message", {})
    return message.get("content", "").strip()


# ---------------------------------------------------------------------------
# Docker Model Runner backend  (OpenAI-compatible /v1/chat/completions)
# ---------------------------------------------------------------------------

def _chat_openai_compat(
    model: str,
    messages: List[Dict[str, str]],
    response_format: Optional[Dict] = None,
    temperature: Optional[float] = None,
) -> str:
    payload: Dict = {"model": model, "messages": messages}
    if response_format:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "response", "schema": response_format},
        }
    if temperature is not None:
        payload["temperature"] = temperature
    response = requests.post(
        config.DOCKER_MODEL_RUNNER_URL, json=payload, timeout=config.REQUEST_TIMEOUT
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:  # pragma: no cover - surfaced in UI
        raise LLMError(str(exc)) from exc
    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Unexpected Docker Model Runner response shape: {data}") from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chat_with_model(
    model: str,
    messages: List[Dict[str, str]],
    response_format: Optional[Dict] = None,
    temperature: Optional[float] = None,
) -> str:
    """Send a chat completion request to the configured LLM backend."""
    if config.MODEL_BACKEND == "docker":
        return _chat_openai_compat(model, messages, response_format, temperature)
    return _chat_ollama(model, messages, response_format, temperature)


def stream_with_model(
    model: str,
    messages: List[Dict[str, str]],
    response_format: Optional[Dict] = None,
    temperature: Optional[float] = None,
):  # pragma: no cover - streaming not used in tests
    """Yield content chunks. Docker Model Runner falls back to non-streaming."""
    if config.MODEL_BACKEND == "docker" or not config.STREAMING:
        yield chat_with_model(model, messages, response_format, temperature)
        return
    payload: Dict = {"model": model, "messages": messages, "stream": True}
    if response_format:
        payload["format"] = response_format
    if temperature is not None:
        payload.setdefault("options", {})["temperature"] = temperature
    with requests.post(
        config.OLLAMA_API_URL, json=payload, timeout=config.REQUEST_TIMEOUT, stream=True
    ) as resp:
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise LLMError(str(exc)) from exc
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                logger.debug("Skipping non-JSON stream line: %r", line[:100])
                continue
            content = chunk.get("message", {}).get("content")
            if content:
                yield content


def chat_json(
    model: str,
    messages: List[Dict[str, str]],
    response_format: Dict,
    temperature: Optional[float] = None,
) -> Dict:
    """Helper that expects the model to return JSON."""
    raw = chat_with_model(
        model=model,
        messages=messages,
        response_format=response_format,
        temperature=temperature,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model response was not valid JSON: {raw[:300]!r}") from exc
