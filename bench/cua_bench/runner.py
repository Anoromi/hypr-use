from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from .catalog import Task
from .grading import grade
from .t6_evaluator import evaluate as evaluate_t6


class Mode(str, Enum):
    AGENTIC = "agentic"
    SCRIPTED = "scripted"


@dataclass
class Execution:
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    fields: dict[str, Any] = field(default_factory=dict)



def result_for(task: Task, mode: Mode, execution: Execution, state: dict[str, Any],
               recording: Path, started: float) -> dict[str, Any]:
    lifecycle = any(event.get("lifecycle_error") for event in execution.events)
    grading_events = execution.events + ([{"tool_error": execution.error}] if execution.error and not lifecycle else [])
    outcome = grade(task.grader, state, grading_events)
    metrics = {key: value for key, value in execution.fields.items() if key in {"tool_calls", "input_tokens", "output_tokens", "cost_usd", "exit_code", "t6_evidence", "steps"}}
    infrastructure_errors = [
        event.get("tool_error") or event.get("lifecycle_error") or ("timeout" if event.get("timeout") else None)
        for event in execution.events
        if event.get("tool_error") or event.get("lifecycle_error") or event.get("timeout")
    ]
    if execution.error and execution.error not in infrastructure_errors: infrastructure_errors.append(execution.error)
    return {
        **metrics,
        "id": task.id,
        "tier": task.tier,
        "mode": mode.value,
        "baseline_kind": "model_score" if mode is Mode.AGENTIC else "scripted_baseline",
        "steps": int(metrics.pop("steps", metrics.get("tool_calls", 0)) or 0),
        "infrastructure_errors": infrastructure_errors,
        **asdict(outcome),
        "wall_s": time.monotonic() - started,
        "oracle_steps": task.oracle_steps,
        "error": execution.error,
        "recording": str(recording),
        "state": state,
    }


def execute(task: Task, mode: Mode, directory: Path, *,
            setup: Callable[[Task], tuple[dict[str, Any], Path]],
            record_start: Callable[[Path], None], record_stop: Callable[[], None],
            executor: Callable[[Task, Path, dict[str, Any], Path], Execution],
            state_reader: Callable[[Path, str], dict[str, Any]],
            recording_validator: Callable[[Path], bool] | None = None) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    recording = directory / "desktop.mp4"
    started = time.monotonic()
    seeded: dict[str, Any] = {}; state_directory: Path | None = None; recording_started = False
    try:
        seeded, state_directory = setup(task)
        record_start(recording); recording_started = True
        execution = executor(task, directory, seeded, state_directory)
    except Exception as exc:
        execution = Execution(error=str(exc), events=[{"lifecycle_error": str(exc)}])
    finally:
        if recording_started:
            try: record_stop()
            except Exception as exc:
                execution.events.append({"lifecycle_error": f"recording stop failed: {exc}"})
                execution.error = execution.error or str(exc)
    try: state = state_reader(state_directory, task.app) if state_directory else {}
    except Exception as exc:
        state = {}; execution.events.append({"lifecycle_error": f"state read failed: {exc}"}); execution.error = execution.error or str(exc)
    valid_recording = recording_validator(recording) if recording_validator else recording.is_file() and recording.stat().st_size > 0
    if not valid_recording:
        execution.events.append({"lifecycle_error": "task recording is missing or empty"})
        execution.error = execution.error or "task recording is missing or empty"
    if task.tier == "T6":
        try:
            verified, evidence = evaluate_t6(task, state, sorted(directory.glob("wire*.jsonl")), execution.events)
            state["tool_passed"] = verified; execution.fields["t6_evidence"] = evidence
            import json
            (directory / "t6-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        except Exception as exc:
            state["tool_passed"] = False; execution.events.append({"lifecycle_error": f"T6 evaluation failed: {exc}"}); execution.error = execution.error or str(exc)
    result = result_for(task, mode, execution, state, recording, started)
    import json
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
