#!/usr/bin/env python3
"""Trust Guard content reviewer — independent OpenAI-compatible Review-LLM check.

Returns PASS/WARN/BLOCK for an artifact's *content* (evidence support + internal
consistency), or None when no Review-LLM is configured (graceful skip, matching
the repo convention that unconfigured cross-model review is skipped).

Per shared-references/cross-model-review.md: never feed the primary model's own
judgment to the reviewer — the prompt below contains only the artifact + neighbors.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any

import _env  # noqa: F401  side-effect: load .env so LLM_* are visible

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


@dataclass
class ContentVerdict:
    status: str   # "PASS" | "WARN" | "BLOCK"
    message: str
    raw: dict[str, Any] | None = None


def _llm_env() -> dict:
    return {
        "api_key": os.environ.get("LLM_API_KEY", "").strip(),
        "base_url": os.environ.get("LLM_BASE_URL", "").strip().rstrip("/"),
        "model": os.environ.get("LLM_MODEL", "").strip(),
        "fallback_model": os.environ.get("LLM_FALLBACK_MODEL", "").strip(),
    }


_SYSTEM = (
    "You are OmegaWiki's Trust Guard content reviewer. Independently judge whether "
    "the artifact's claims are supported by its own stated evidence and are "
    "consistent with the provided neighboring memory. Use ONLY the provided text. "
    'Return strict JSON only: {"verdict": "pass|warn|block", "reason": "<one sentence>"}.'
)


def _post_chat(*, system: str, user: str, env: dict, timeout: int = 60) -> str:
    """POST to an OpenAI-compatible /chat/completions and return the message text.
    Mirrors daily_arxiv._call_openai_compatible. Patched out in unit tests."""
    assert requests is not None, "requests is required for live content review"
    url = f"{env['base_url']}/chat/completions"
    headers = {"Authorization": f"Bearer {env['api_key']}", "Content-Type": "application/json"}
    models = [env["model"]]
    if env.get("fallback_model") and env["fallback_model"] not in models:
        models.append(env["fallback_model"])
    last_error: Exception | None = None
    for model in models:
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=timeout)
            if resp.status_code >= 400 and body.get("response_format"):
                body.pop("response_format", None)
                resp = requests.post(url, headers=headers, json=body, timeout=timeout)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    raise RuntimeError(f"content review LLM call failed: {last_error}")


def _extract_json(text: str) -> dict:
    """Parse a JSON object from `text`: try the whole string first, then fall back
    to the outermost {...} slice. Using json.loads as the arbiter (rather than
    counting braces) keeps this robust to braces inside string values."""
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object in reviewer response")
    return json.loads(text[start : end + 1])


def review_artifact(artifact_text: str, *, context: dict, timeout: int = 60) -> ContentVerdict | None:
    env = _llm_env()
    if not (env["api_key"] and env["base_url"] and env["model"]):
        return None
    user = (
        "ARTIFACT:\n" + artifact_text.strip()
        + "\n\nNEIGHBORING MEMORY (for consistency):\n"
        + json.dumps(context.get("neighbors", []), ensure_ascii=False)
    )
    try:
        raw_text = _post_chat(system=_SYSTEM, user=user, env=env, timeout=timeout)
        raw = _extract_json(raw_text)
    except Exception as exc:  # noqa: BLE001 — content review unavailable; degrade to skip
        print(f"trust content review unavailable: {exc}", file=sys.stderr)
        return None
    verdict = str(raw.get("verdict", "")).strip().lower()
    status = {"pass": "PASS", "warn": "WARN", "block": "BLOCK"}.get(verdict, "WARN")
    return ContentVerdict(status=status, message=str(raw.get("reason", "")).strip(), raw=raw)
