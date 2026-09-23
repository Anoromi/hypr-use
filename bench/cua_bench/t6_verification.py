from __future__ import annotations

import json
import os
import signal
from pathlib import Path
from typing import Any, Callable

from .catalog import Task


def process_starttime(pid: int) -> int:
    return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19])


def _state(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _workspace(row: dict[str, Any]) -> int | None:
    value = row.get("workspace")
    if isinstance(value, dict):
        value = value.get("id")
    return value if isinstance(value, int) else None


def _inventory(clients: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    found = {}
    for row in clients:
        if not isinstance(row, dict) or row.get("mapped") is False or not isinstance(row.get("pid"), int):
            continue
        address = str(row.get("address", ""))
        workspace = _workspace(row)
        if address and workspace is not None:
            found[row["pid"]] = {"id": "address:" + address.removeprefix("address:"), "workspace": workspace, "pid": row["pid"]}
    return found


def _fixture(path: Path, clients: dict[int, dict[str, Any]],
             read_starttime: Callable[[int], int]) -> dict[str, Any] | None:
    state = _state(path)
    if not state or not isinstance(state.get("pid"), int) or not isinstance(state.get("starttime"), int):
        return None
    pid = state["pid"]
    try:
        if read_starttime(pid) != state["starttime"]:
            return None
    except (OSError, ValueError, IndexError, ProcessLookupError):
        return None
    row = clients.get(pid)
    if not row:
        return None
    return {**row, "app": state.get("app"), "starttime": state["starttime"]}


def _owned_paths(task: Task, directory: Path) -> list[tuple[Path, str]]:
    spec = task.oracle[0].get("tool_benchmark", {})
    kind = spec.get("kind")
    if task.tier != "T6" or kind not in {"launch", "parallel"}:
        return []
    if kind == "launch":
        expected = spec["count"]
        agent = [(directory / f"agent-launch-{number + 1}" / "forms-app.json", "forms-app")
                 for number in range(expected)]
        if any(path.exists() for path, _app in agent):
            return agent
        return [(directory / f"launch-{number}" / "forms-app.json", "forms-app")
                for number in range(expected)]
    paths = []
    for phase, app in enumerate(task.setup_apps[:spec["count"]], 1):
        agent = directory / f"agent-launch-{phase}" / f"{app}.json"
        paths.append((agent if agent.exists() else directory / f"parallel-{app}" / f"{app}.json", app))
    return paths


def cleanup(task: Task, directory: Path, *,
            read_starttime: Callable[[int], int] = process_starttime,
            terminate: Callable[[int, int], None] = os.kill) -> list[int]:
    """Terminate only launch fixtures owned by this benchmark run."""
    terminated = []
    for path, expected_app in _owned_paths(task, directory):
        state = _state(path)
        if not state or state.get("app") != expected_app:
            continue
        pid, starttime = state.get("pid"), state.get("starttime")
        if not isinstance(pid, int) or not isinstance(starttime, int):
            continue
        try:
            if read_starttime(pid) != starttime:
                continue
            terminate(pid, signal.SIGTERM)
        except (OSError, ValueError, IndexError, ProcessLookupError):
            continue
        terminated.append(pid)
    return terminated


def verify(task: Task, directory: Path, clients: list[dict[str, Any]], *,
           read_starttime: Callable[[int], int] = process_starttime,
           agent_workspaces: dict[str, int] | None = None,
           before_clients: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build trusted T6 launch/parallel evidence from fixture processes.

    The executor controls each fixture state directory. A row counts only when
    its saved PID/start time still identifies a mapped compositor client.
    Optional agent_workspaces adds a registry cross-check keyed by the runner's
    known agent IDs.
    """
    if task.tier != "T6":
        return {}
    spec = task.oracle[0].get("tool_benchmark", {})
    kind = spec.get("kind")
    inventory = _inventory(clients)

    if kind == "launch":
        expected = spec["count"]
        paths = [path for path, _app in _owned_paths(task, directory)]
        rows = [_fixture(path, inventory, read_starttime) for path in paths]
        rows = [row for row in rows if row]
        if agent_workspaces is not None:
            owner = agent_workspaces.get(f"cua-bench-{task.id}-1")
            rows = [row for row in rows if owner is not None and row["workspace"] == owner]
        targets = [row["id"] for row in rows]
        return {"launch_targets": targets if len(targets) == expected and len(set(targets)) == expected else []}

    if kind == "parallel":
        frames = []
        for phase, app in enumerate(task.setup_apps[:spec["count"]], 1):
            path = directory / f"agent-launch-{phase}" / f"{app}.json"
            if not path.exists():
                path = directory / f"parallel-{app}" / f"{app}.json"
            row = _fixture(path, inventory, read_starttime)
            if not row:
                continue
            if agent_workspaces is not None:
                owner = agent_workspaces.get(f"cua-bench-{task.id}-{phase}")
                if owner is None or row["workspace"] != owner:
                    continue
            frames.append({"workspace": row["workspace"], "ownRows": [{"id": row["id"], "workspace": row["workspace"], "mine": True}]})
        return {"parallel_frames": frames}

    return {}
