from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .catalog import Task


def _app(state: dict[str, Any], name: str) -> dict[str, Any]:
    apps = state.get("apps", {})
    if isinstance(apps, dict) and isinstance(apps.get(name), dict):
        return apps[name]
    return state if state.get("app") == name else {}


def _scripted(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    for event in events:
        value = event.get("tool_benchmark")
        if isinstance(value, dict):
            return value
    return {}


def _trusted(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Return evidence collected by the host after the action executor stops."""
    for event in events:
        value = event.get("t6_verification")
        if isinstance(value, dict):
            return value
    return {}


def _content(result: dict[str, Any]) -> list[str]:
    return [block.get("text", "") for block in result.get("content", []) if block.get("type") == "text"]


def _records(paths: Iterable[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source_number, path in enumerate(paths):
        try:
            lines = path.read_text().splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            request = row.get("request", {})
            params = request.get("params", {})
            args = params.get("arguments", {})
            result = row.get("response", {}).get("result", {})
            timing = result.get("_meta", {}).get("hypr-use/timing", {})
            records.append({
                "source": source_number,
                "tool": params.get("name"),
                "code": args.get("code", "") if isinstance(args, dict) else "",
                "arguments": args if isinstance(args, dict) else {},
                "content": _content(result),
                "is_error": result.get("isError") is True,
                "total_ms": timing.get("total_ms"),
                "operations": timing.get("operations", []),
            })
    return records


def _names(records: Iterable[dict[str, Any]]) -> list[str]:
    return [op.get("name", "") for row in records for op in row["operations"] if isinstance(op, dict)]


def _json_blocks(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    values = []
    for row in records:
        for text in row["content"]:
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                values.append(value)
    return values


def _parallel_ok(rows: list[dict[str, Any]], expected: int) -> bool:
    if len(rows) != expected:
        return False
    workspaces = [row.get("workspace") for row in rows]
    own = [row.get("ownRows") for row in rows]
    if any(not isinstance(ws, int) for ws in workspaces) or len(set(workspaces)) != expected:
        return False
    if any(not isinstance(items, list) or not items for items in own):
        return False
    if any(any(item.get("mine") is not True or item.get("workspace") != ws or not item.get("id") for item in items)
           for ws, items in zip(workspaces, own)):
        return False
    identities = [{item["id"] for item in items} for items in own]
    return all(identities[i].isdisjoint(identities[j]) for i in range(expected) for j in range(i + 1, expected))


def _parallel_matches(reported: list[dict[str, Any]], trusted: list[dict[str, Any]], expected: int) -> bool:
    if not _parallel_ok(reported, expected) or not _parallel_ok(trusted, expected):
        return False
    by_workspace = {row["workspace"]: {item["id"] for item in row["ownRows"]} for row in reported}
    return all({item["id"] for item in row["ownRows"]} <= by_workspace.get(row["workspace"], set()) for row in trusted)


def evaluate(task: Task, state: dict[str, Any], wire_paths: Iterable[Path],
             execution_events: Iterable[dict[str, Any]]) -> tuple[bool, dict[str, Any]]:
    """Evaluate a T6 run from fixture state and transport evidence.

    `tool_passed` is deliberately ignored. Scripted evidence can supply timing or
    multi-client facts that are unavailable in fixture JSON, but a state-changing
    benchmark must also match independently persisted fixture state.
    """
    if task.tier != "T6":
        raise ValueError("T6 evaluator received a non-T6 task")
    spec = task.oracle[0]["tool_benchmark"]
    kind = spec["kind"]
    paths = [Path(path) for path in wire_paths]
    records = _records(paths)
    events = list(execution_events)
    scripted = _scripted(events)
    trusted = _trusted(events)
    operations = _names(records)
    evidence: dict[str, Any] = {"kind": kind, "wire_records": len(records), "operations": operations}

    if kind == "rapid":
        expected = spec["count"]
        count = _app(state, "forms-app").get("click_count")
        operation_count = operations.count("click") if records else scripted.get("completed")
        passed = count == expected and operation_count == expected
        evidence.update(expected=expected, click_count=count, operation_count=operation_count)

    elif kind == "latency":
        limit = spec["limit_ms"]
        candidates = [row for row in records if not row["is_error"] and any("Item 1000" in text for text in row["content"])
                      and isinstance(row["total_ms"], (int, float))]
        elapsed = min((row["total_ms"] for row in candidates), default=scripted.get("elapsed_ms"))
        observed_sets = [{int(value) for value in re.findall(r"\bItem (\d+)\b", "\n".join(row["content"]))} for row in candidates]
        observed = max(observed_sets, key=len, default=set()) if records else set(range(1, 1001)) if scripted.get("all_rows_visible") is True else set()
        visible = observed == set(range(1, 1001))
        rows = _app(state, "list-app").get("rows")
        passed = rows == 1000 and visible
        evidence.update(rows=rows, observed_rows=len(observed), row_1000_visible=1000 in observed, elapsed_ms=elapsed, limit_ms=limit)

    elif kind == "launch":
        expected = spec["count"]
        launch_records = [row for row in records if "cua.launch(" in row["code"] and not row["is_error"]]
        emitted_targets = []
        for row in launch_records:
            for text in row["content"]:
                emitted_targets.extend(re.findall(r"Launched [^\n]* as (address:[^\s;(]+)", text))
        trusted_targets = [value for value in trusted.get("launch_targets", []) if isinstance(value, str)]
        passed = len(emitted_targets) == expected and len(set(emitted_targets)) == expected \
            and len(trusted_targets) == expected and set(trusted_targets) == set(emitted_targets)
        evidence.update(expected=expected, emitted_targets=emitted_targets, trusted_targets=trusted_targets)

    elif kind == "restart":
        successful_sources: dict[int, set[str]] = {}
        for row in records:
            if row["is_error"] or not any(name in {"get_ax_state", "get_app_state"} for name in _names([row])):
                continue
            targets = set(re.findall(r"Target: (address:[^\s]+)", "\n".join(row["content"])))
            if targets:
                successful_sources.setdefault(row["source"], set()).update(targets)
        common = set.intersection(*successful_sources.values()) if len(successful_sources) >= 2 else set()
        passed = len(successful_sources) >= 2 and bool(common)
        evidence.update(successful_connections=len(successful_sources), common_targets=sorted(common), rebound=scripted.get("rebound"))

    elif kind == "parallel":
        expected = spec["count"]
        reported = [row for row in _json_blocks(records) if "workspace" in row and "ownRows" in row]
        frames = trusted.get("parallel_frames", [])
        passed = _parallel_matches(reported, frames, expected)
        evidence.update(expected=expected, reported_frames=reported, trusted_frames=frames)

    elif kind == "text":
        value = spec["value"]
        multiline = "\n" in value
        actual = _app(state, "editor-app").get("content") if multiline else _app(state, "forms-app").get("name")
        expected_operation = "type_text" if multiline else "paste_text"
        operation_seen = expected_operation in operations if records else expected_operation in scripted.get("operations", [])
        passed = actual == value and operation_seen
        evidence.update(value=value, actual=actual, expected_operation=expected_operation, operation_seen=operation_seen)

    elif kind == "click":
        mode = spec["mode"]
        app_state = _app(state, "forms-app")
        click_rows = [row for row in records if not row["is_error"] and "click" in _names([row])]
        if mode == "index":
            shape_ok = any(re.search(r"\.click\(\s*\d+", row["code"]) for row in click_rows)
        else:
            shape_ok = any(re.search(r"\.click\(\s*\[", row["code"]) for row in click_rows)
        if not records:
            shape_ok = scripted.get("target_mode") == mode
        passed = app_state.get("completed") is True and app_state.get("click_count", 0) >= 1 and shape_ok
        evidence.update(mode=mode, completed=app_state.get("completed"), click_count=app_state.get("click_count"), target_shape=shape_ok)

    elif kind == "tracking":
        expected = spec["count"]
        frames = []
        for row in records:
            for text in row["content"]:
                frames.extend(re.findall(r"button Complete[^\n]*Frame: (\[[^]]+\])", text))
        if records:
            observations = sum(name in {"get_ax_state", "get_app_state"} for name in operations)
        else:
            observations = scripted.get("tracked", 0)
            frames = list(range(scripted.get("distinct_frames", 0)))
        ticks = _app(state, "forms-app").get("motion_ticks", 0)
        passed = observations >= expected and len(set(frames)) > 1 and ticks > 0
        evidence.update(expected=expected, observations=observations, distinct_frames=len(set(frames)), motion_ticks=ticks)

    else:
        raise ValueError(f"unknown T6 benchmark kind {kind}")

    evidence["passed"] = passed
    return passed, evidence
