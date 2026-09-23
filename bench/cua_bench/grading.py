from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class Grade:
    passed: bool
    score: float
    milestones: tuple[str, ...]
    failure_class: str | None
    detail: str


def _get(value: Any, dotted: str) -> Any:
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _answer_text(transcript: list[dict[str, Any]], include_oracle: bool = False) -> str:
    chunks = []
    for event in transcript:
        if event.get("type") == "result" and isinstance(event.get("result"), str): chunks.append(event["result"])
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "agent_message": chunks.append(str(item.get("text", "")))
        message = event.get("message")
        if event.get("type") == "assistant" and isinstance(message, dict):
            for block in message.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text": chunks.append(str(block.get("text", "")))
        if include_oracle and "request" in event and "result" in event: chunks.append(str(event["result"]))
    return "\n".join(chunks)


def grade(spec: dict[str, Any], state: dict[str, Any], transcript: list[dict[str, Any]]) -> Grade:
    checks = spec.get("checks", [])
    met: list[str] = []
    for check in checks:
        actual = _answer_text(transcript, check["path"] == "$oracle_transcript") if check["path"] in {"$transcript", "$oracle_transcript"} else _get(state, check["path"])
        op = check.get("op", "eq")
        expected = check.get("value")
        ok = (
            (op == "eq" and actual == expected)
            or (op == "contains" and expected in (actual or []))
            or (op == "regex" and isinstance(actual, str) and re.search(expected, actual, re.IGNORECASE) is not None)
            or (op == "exists" and actual is not None)
            or (op == "gte" and isinstance(actual, (int, float)) and actual >= expected)
        )
        if ok:
            met.append(check.get("name", check["path"]))
    score = len(met) / len(checks) if checks else 0.0
    violated = any(e.get("guardrail_violation") for e in transcript); tool_failed = any(e.get("tool_error") for e in transcript)
    lifecycle_failed = any(e.get("timeout") or e.get("lifecycle_error") for e in transcript)
    # Completion is an outcome measure. Recovered transport/driver errors remain
    # visible in result metadata but do not erase a verified completed state.
    passed = bool(checks) and len(met) == len(checks) and not violated
    if violated:
        failure = "violated_guardrail"
    elif passed:
        failure = None
    elif tool_failed:
        failure = "tool_error"
    elif lifecycle_failed:
        failure = "timeout" if any(e.get("timeout") for e in transcript) else "driver_error"
    elif not transcript:
        failure = "gave_up"
    else:
        failure = spec.get("failure_class", "wrong_action")
    return Grade(passed, score, tuple(met), failure, f"{len(met)}/{len(checks)} checks met")
