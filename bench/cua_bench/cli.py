from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .catalog import ROOT, Task, load_tasks, select
from .grading import grade
from .oracle import OracleError, run_oracle
from .report import render
from .toolbench import run as run_tool_benchmark
from .mcp_bridge import ALIASES
from .codex_driver import run as run_codex
from .instructions import agent_prompt
from .real_apps import run as run_real_app
from .runner import Execution, Mode, execute
from .t6_verification import cleanup as cleanup_t6_host, verify as verify_t6_host

REPO = ROOT.parent
DEFAULT_LAB = REPO.parent / "hypr-testbed" / "hypr-lab"
LAB_ROOT = Path(os.environ.get("HYPR_LAB_ROOT", REPO.parent / "hypr-testbed"))
MCP_ROOT = Path(os.environ.get("HYPR_USE_MCP_ROOT", REPO))
RESULTS_ROOT = Path(os.environ.get("HYPR_BENCH_RESULTS_DIR", Path.home() / "Artifacts/cua-bench/results" if os.environ.get("HYPR_USE_PACKAGED_BENCH") else ROOT / "results"))


def write_source_manifest(output: Path) -> Path:
    sources = [
        ROOT / "tasks.json", ROOT / "generate_tasks.py", *sorted((ROOT / "apps").glob("*.py")),
        *sorted((ROOT / "cua_bench").glob("*.py")),
        MCP_ROOT / "mcp" / "unified" / "server.mjs", MCP_ROOT / "mcp" / "unified" / "worker.mjs",
        MCP_ROOT / "mcp" / "unified" / "backend.py", MCP_ROOT / "mcp" / "unified" / "observations.py",
        MCP_ROOT / "mcp" / "unified" / "facade.mjs", MCP_ROOT / "mcp" / "unified" / "workflows.mjs", MCP_ROOT / "mcp" / "unified" / "runtime_fixes.py",
        LAB_ROOT / "lab" / "cua-mcp",
    ]
    payload = {"created_at": datetime.now(timezone.utc).isoformat(), "files": {}}
    for path in sources:
        try: payload["files"][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError: payload["files"][str(path)] = None
    manifest = output / "source-manifest.json"
    if manifest.exists() and json.loads(manifest.read_text()).get("files") != payload["files"]:
        cohorts = sorted(output.glob("source-manifest-resume-*.json")); manifest = output / f"source-manifest-resume-{len(cohorts)+1}.json"
    manifest.write_text(json.dumps(payload, indent=2) + "\n")
    return manifest


def lab_command() -> list[str]:
    configured = os.environ.get("HYPR_LAB")
    if configured: return [configured]
    found = shutil.which("hypr-lab")
    return [found] if found else [sys.executable, "-m", "hyprlab"]


def lab(*args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy(); env.setdefault("HYPR_BENCH_ROOT", str(ROOT)); env.setdefault("BENCH_TASK_FILE", str(ROOT / "tasks.json"))
    return subprocess.run([*lab_command(), *args], check=check, text=True, capture_output=capture, cwd=LAB_ROOT, env=env)


def require_lab(profile: str) -> None:
    if len(lab_command()) == 1 and not Path(lab_command()[0]).exists() and not shutil.which(lab_command()[0]):
        raise SystemExit(f"hypr-lab unavailable at {lab_command()[0]}; set HYPR_LAB")
    status = lab("status", "--json", check=False)
    ready = False
    try:
        payload = json.loads(status.stdout); ready = payload.get("running") is True and payload.get("healthy") is True
    except json.JSONDecodeError: pass
    if not ready:
        if 'payload' in locals() and payload.get("running") is True:
            raise SystemExit("hypr-lab core is running but unhealthy; refusing to replace the live compositor")
        lab("up", "--profile", profile, capture=False)
        payload = json.loads(lab("status", "--json").stdout)
        if payload.get("running") is not True or payload.get("healthy") is not True: raise SystemExit("hypr-lab did not become healthy")


def seed(task: Task) -> dict[str, Any]:
    proc = lab("seed", task.seed, "--json")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def state_dir(seed_result: dict[str, Any]) -> Path:
    path = seed_result.get("bench_state_dir") or seed_result.get("BENCH_STATE_DIR") or os.environ.get("BENCH_STATE_DIR")
    if not path:
        env = json.loads(lab("env", "--json").stdout); path = env.get("BENCH_STATE_DIR")
    if not path: raise RuntimeError("lab seed did not expose BENCH_STATE_DIR")
    return Path(path)


def read_state(directory: Path, primary: str) -> dict[str, Any]:
    paths = list(directory.glob("*.json")); states = {}
    for path in paths:
        try: states[path.stem] = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError): continue
    merged = dict(states.get(primary, {})); merged["apps"] = states
    return merged


def transcript_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    tool_calls = 0; input_tokens = 0; output_tokens = 0; cost = 0.0; total_cost = 0.0
    tool_ids: set[str] = set()
    for event in events:
        if not isinstance(event, dict):
            continue
        body = event.get("message", event)
        item = event.get("item", {})
        if not isinstance(item, dict): item = {}
        if event.get("type") in {"item.started", "item.completed"} and item.get("type") == "mcp_tool_call":
            raw_id = str(item.get("id") or event.get("id") or "")
            identity = f"{event.get('benchmark_phase', 1)}:{raw_id}" if raw_id else ""
            if identity:
                if identity not in tool_ids: tool_ids.add(identity); tool_calls += 1
            elif event.get("type") == "item.completed": tool_calls += 1
        if event.get("type") in {"tool_use", "tool_result"} or (isinstance(body, dict) and body.get("type") == "tool_use"): tool_calls += 1
        usage = event.get("usage", {}) if event.get("type") == "turn.completed" else (body.get("usage", {}) if isinstance(body, dict) else {})
        input_tokens += int(usage.get("input_tokens", 0) or 0); output_tokens += int(usage.get("output_tokens", 0) or 0)
        total_cost = max(total_cost, float(event.get("total_cost_usd", 0) or 0)); cost += float(event.get("cost_usd", 0) or 0)
    return {"tool_calls": tool_calls, "input_tokens": input_tokens, "output_tokens": output_tokens, "cost_usd": total_cost or cost}



def setup_execution(task: Task) -> tuple[dict[str, Any], Path]:
    seeded = seed(task)
    if seeded.get("ready") is not True: raise RuntimeError(f"seed {task.seed} did not become ready")
    return seeded, state_dir(seeded)


def start_recording(path: Path) -> None:
    lab("record", "start", str(path))


def stop_recording() -> None:
    lab("record", "stop", check=False)


def valid_recording(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size == 0: return False
    checked = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    try: return checked.returncode == 0 and float(checked.stdout.strip()) > 0
    except ValueError: return False


def compositor_clients() -> list[dict[str, Any]]:
    try: value = json.loads(lab("exec", "--", "hyprctl", "clients", "-j").stdout)
    except Exception: return []
    return value if isinstance(value, list) else []


def agent_executor(model: str, timeout: int):
    def run(task: Task, directory: Path, _seeded: dict[str, Any], _states: Path) -> Execution:
        server_env = json.loads(lab("env", "--json").stdout)
        server_env.pop("OPENAI_API_KEY", None); server_env.pop("OPENAI_BASE_URL", None)
        server_env.update(HYPR_AGENT_PORTAL_PERMISSION_MODE="full", HYPR_AGENT_PORTAL_APPROVAL_POLICY="never", HYPR_USE_APP_ALIASES=json.dumps(ALIASES), HYPR_USE_FAST_CONTROL="0", HYPR_USE_NO_HYPRNAV="1")
        lab_mcp = LAB_ROOT / "lab" / "cua-mcp"
        packaged_mcp = os.environ.get("HYPR_USE_PACKAGED_MCP")
        mcp_command = packaged_mcp or (str(lab_mcp) if lab_mcp.exists() else "node")
        mcp_args = [] if packaged_mcp or lab_mcp.exists() else [str(MCP_ROOT / "mcp" / "unified" / "server.mjs")]
        prompt = agent_prompt(task); (directory / "prompt.txt").write_text(prompt + "\n")
        before_clients = compositor_clients() if task.tier == "T6" else []
        kind = task.oracle[0].get("tool_benchmark", {}).get("kind") if task.tier == "T6" else None
        phases = 2 if kind in {"parallel", "restart"} else 1
        def run_phase(phase: int) -> tuple[int, list[dict[str, Any]], str]:
            phase_env = dict(server_env); phase_env["HYPR_USE_WIRE_LOG"] = str(directory / ("wire.jsonl" if phases == 1 else f"wire-{phase+1}.jsonl"))
            if kind in {"launch", "parallel"}:
                phase_env.update(HYPR_USE_NO_HYPRNAV="0", HYPR_USE_AGENT_ID=f"cua-bench-{task.id}-{phase+1}", HYPR_USE_AGENT_LABEL=f"CUA bench {task.id} phase {phase+1}")
            phase_prompt = prompt
            if kind in {"launch", "parallel"}:
                assigned = task.setup_apps[phase] if kind == "parallel" else "forms-app"
                launch_count = task.oracle[0]["tool_benchmark"].get("count", 1) if kind == "launch" else 1
                commands = []
                for number in range(launch_count):
                    launch_state = directory / f"agent-launch-{number+1 if kind == 'launch' else phase+1}"; launch_state.mkdir(exist_ok=True)
                    commands.append(["env", f"BENCH_STATE_DIR={launch_state}", "python3", str(ROOT / "apps" / "bench_app.py"), assigned])
                phase_prompt += f"\nThe allowed cua.launch argv values for your fixture(s) are exactly: {json.dumps(commands)}."
            if kind == "parallel":
                phase_prompt += (f"\nYou own isolated phase {phase+1} of {phases}. Launch and verify only {task.setup_apps[phase]}. "
                                 "After observing cua.myWorkspace() and cua.listWorkspaceApps({emit:false}), "
                                 "emit one JSON object in a cua_repl js tool response with "
                                 "nodeRepl.write(JSON.stringify({workspace: workspace.workspace, "
                                 "ownRows: apps.filter(row => row.mine === true)})). "
                                 "Use workspace and apps variables holding those actual observations; do not invent IDs or workspace numbers.")
            elif kind == "restart": phase_prompt += f"\nThis is connection phase {phase+1} of {phases}. Observe and verify the same fixture; phase 2 uses a fresh MCP connection."
            code, phase_events, phase_stderr = run_codex(prompt=phase_prompt, model=model, cwd=ROOT / "demo-project", mcp_command=mcp_command, mcp_args=mcp_args, mcp_env=phase_env, output=directory / ("final.txt" if phases == 1 else f"final-{phase+1}.txt"), timeout=timeout, codex_home=server_env.get("CODEX_HOME"))
            return code, [{**event, "benchmark_phase": phase + 1} for event in phase_events], phase_stderr
        if kind == "parallel":
            with ThreadPoolExecutor(max_workers=phases) as pool: phase_results = list(pool.map(run_phase, range(phases)))
        else: phase_results = [run_phase(phase) for phase in range(phases)]
        events = [event for _code, phase_events, _stderr in phase_results for event in phase_events]
        stderrs = [value for _code, _events, value in phase_results]; exit_codes = [code for code, _events, _stderr in phase_results]
        trusted = verify_t6_host(task, directory, compositor_clients(), before_clients=before_clients)
        if trusted: events.append({"t6_verification": trusted})
        cleanup_t6_host(task, directory)
        exit_code = next((code for code in exit_codes if code != 0), 0); stderr = "\n".join(stderrs)
        (directory / "transcript.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events)); (directory / "stderr.txt").write_text(stderr)
        violations = [{"guardrail_violation": "command_execution"} for event in events
                      if isinstance(event.get("item"), dict) and event["item"].get("type") == "command_execution"]
        metrics = transcript_metrics(events)
        if exit_code == 124: violations.append({"timeout": True})
        elif exit_code != 0: violations.append({"lifecycle_error": f"codex exited {exit_code}"})
        violations += [{"tool_error": event["item"].get("error") or "MCP tool call failed"} for event in events
                       if event.get("type") == "item.completed" and isinstance(event.get("item"), dict)
                       and event["item"].get("type") == "mcp_tool_call" and event["item"].get("status") == "failed"]
        return Execution(events=events + violations, fields={**metrics, "steps": metrics["tool_calls"], "exit_code": exit_code})
    return run


def scripted_executor(task: Task, directory: Path, _seeded: dict[str, Any], _states: Path) -> Execution:
    try:
        if task.tier == "T6":
            evidence = run_tool_benchmark(task, directory); events = [{"tool_benchmark": evidence}]
            if evidence.get("host_verification"): events.append({"t6_verification": evidence["host_verification"]})
        else:
            events = run_oracle(task.oracle, directory / "transcript.jsonl")
        if task.tier == "T6":
            steps = 0
            for path in directory.glob("wire*.jsonl"):
                for line in path.read_text().splitlines():
                    try: row = json.loads(line)
                    except json.JSONDecodeError: continue
                    if row.get("request", {}).get("method") == "tools/call": steps += 1
        else: steps = sum(int(event.get("mcp_calls", 1)) for event in events)
        return Execution(events=events, fields={"steps": steps})
    except (OracleError, RuntimeError, subprocess.CalledProcessError) as exc:
        return Execution(events=getattr(exc, "events", []), error=str(exc), fields={"steps": getattr(exc, "tool_calls", 0)})


def execute_mode(task: Task, mode: Mode, directory: Path, model: str, timeout: int) -> dict[str, Any]:
    return execute(task, mode, directory, setup=setup_execution, record_start=start_recording,
                   record_stop=stop_recording, executor=agent_executor(model, timeout) if mode is Mode.AGENTIC else scripted_executor,
                   state_reader=read_state, recording_validator=valid_recording)


def command_run(args: argparse.Namespace) -> int:
    tasks = select(load_tasks(), set(args.tier or []), set(args.task or []))
    if not tasks: raise SystemExit("no benchmark tasks selected")
    require_lab("full"); run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = RESULTS_ROOT / run_id; output.mkdir(parents=True, exist_ok=args.resume)
    source_manifest = write_source_manifest(output)
    modes = [Mode.AGENTIC, Mode.SCRIPTED] if args.mode == "both" else [Mode(args.mode)]
    results = []
    for mode in modes:
        for run_number in range(args.runs):
            for task in tasks:
                destination = output / mode.value / f"run-{run_number+1}" / task.id
                if args.resume and (destination / "result.json").exists(): result = json.loads((destination / "result.json").read_text())
                else:
                    result = execute_mode(task, mode, destination, args.model, args.timeout)
                    result["source_manifest"] = source_manifest.name
                    (destination / "result.json").write_text(json.dumps(result, indent=2) + "\n")
                results.append(result); print(json.dumps({k: result.get(k) for k in ("id", "mode", "passed", "score", "wall_s")}))
    summary = {"run_id": run_id, "mode": args.mode, "driver": "codex exec + predefined commands" if args.mode == "both" else ("codex exec" if args.mode == "agentic" else "predefined commands"), "model": args.model if args.mode != "scripted" else None, "results": results}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n"); print(render(output, output / "report")); return int(not all(r["passed"] for r in results))


def command_oracles(args: argparse.Namespace) -> int:
    args.mode = "scripted"; args.model = "gpt-5.6-sol"; args.runs = 1; args.timeout = 240; args.resume = bool(args.run_id)
    return command_run(args)


def command_list(args: argparse.Namespace) -> int:
    tasks = select(load_tasks(), set(args.tier or []), set(args.task or []))
    for task in tasks: print(f"{task.id}\t{task.tier}\t{task.app}\t{task.prompt}")
    return 0


def command_report(args: argparse.Namespace) -> int:
    source = Path(args.run); target = Path(args.output) if args.output else Path.home() / "Artifacts" / "cua-bench" / source.name
    print(render(source, target, Path(args.baseline) if args.baseline else None)); return 0


def command_real_list(_args: argparse.Namespace) -> int:
    for task in json.loads((ROOT / "real-tasks.json").read_text()):
        groups = task["requires"]
        available = all(any(shutil.which(name) for name in group.split("|")) for group in groups)
        print(json.dumps({"id": task["id"], "available": available, "requires": groups}))
    return 0


def command_real(args: argparse.Namespace) -> int:
    require_lab("full"); output = RESULTS_ROOT / (args.run_id or datetime.now(timezone.utc).strftime("real-%Y%m%dT%H%M%SZ")); output.mkdir(parents=True, exist_ok=False)
    ids = args.task or [row["id"] for row in json.loads((ROOT / "real-tasks.json").read_text())]
    results = [run_real_app(task_id, output / task_id) for task_id in ids]
    for result in results: print(json.dumps(result))
    render(output, output / "report"); return int(not all(result["passed"] for result in results))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bench"); sub = p.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False); common.add_argument("--tier", action="append", choices=[f"T{i}" for i in range(1, 7)]); common.add_argument("--task", action="append")
    listing = sub.add_parser("list", parents=[common]); listing.set_defaults(func=command_list)
    oracle = sub.add_parser("tools", parents=[common]); oracle.add_argument("--run-id"); oracle.set_defaults(func=command_oracles)
    run = sub.add_parser("run", parents=[common]); run.add_argument("--mode", choices=("agentic", "scripted", "both"), default="both"); run.add_argument("--model", default="gpt-5.6-sol"); run.add_argument("--runs", type=int, default=1); run.add_argument("--timeout", type=int, default=240); run.add_argument("--run-id"); run.add_argument("--resume", action="store_true"); run.set_defaults(func=command_run)
    report = sub.add_parser("report"); report.add_argument("run"); report.add_argument("--output"); report.add_argument("--baseline"); report.set_defaults(func=command_report)
    real = sub.add_parser("real-list"); real.set_defaults(func=command_real_list)
    real_run = sub.add_parser("real-apps"); real_run.add_argument("--task", action="append"); real_run.add_argument("--run-id"); real_run.set_defaults(func=command_real)
    return p


def main() -> int:
    args = parser().parse_args(); return args.func(args)
