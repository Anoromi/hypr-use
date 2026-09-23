from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from .catalog import Task
from .mcp_bridge import Client, bind_code, index_for, js, perform, point_for, text_content
from .mcp_bridge import LAB_ENV
from .t6_verification import cleanup as cleanup_t6_host, verify as verify_t6_host


def client_overrides(kind: str, identity: str = "main") -> dict[str, str]:
    """Enable workspace registration only for benchmarks that exercise it."""
    if kind not in {"launch", "parallel"}:
        return {}
    return {
        "HYPR_USE_NO_HYPRNAV": "0",
        "HYPR_USE_AGENT_ID": f"cua-bench-{kind}-{identity}",
        "HYPR_USE_AGENT_LABEL": f"CUA bench {kind} {identity}",
    }


def parallel_isolated(outcomes: list[dict[str, Any]], expected: int) -> bool:
    if len(outcomes) != expected or any(row.get("error") for row in outcomes):
        return False
    workspaces = [row.get("workspace") for row in outcomes]
    own_rows = [row.get("ownRows") for row in outcomes]
    if any(not isinstance(ws, int) for ws in workspaces) or len(set(workspaces)) != expected:
        return False
    if any(not isinstance(rows, list) or not rows for rows in own_rows):
        return False
    if any(any(row.get("mine") is not True or row.get("workspace") != ws or not row.get("id") for row in rows) for ws, rows in zip(workspaces, own_rows)):
        return False
    own_ids = [{row["id"] for row in rows} for rows in own_rows]
    return all(own_ids[i].isdisjoint(own_ids[j]) for i in range(expected) for j in range(i + 1, expected))


def host_clients() -> list[dict[str, Any]]:
    env = os.environ.copy()
    if LAB_ENV.exists(): env.update(json.loads(LAB_ENV.read_text()))
    try: value = json.loads(subprocess.run(["hyprctl", "clients", "-j"], env=env, capture_output=True, text=True, check=True).stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError): return []
    return value if isinstance(value, list) else []


def run(task: Task, directory: Path) -> dict[str, Any]:
    spec = task.oracle[0]["tool_benchmark"]; kind = spec["kind"]; started = time.monotonic(); evidence: dict[str, Any] = {"kind": kind}
    initial = {**client_overrides(kind), "HYPR_USE_WIRE_LOG": str(directory / "wire-1.jsonl")}
    client = Client(initial)
    try:
        if kind == "rapid":
            idx = index_for(client, "forms-app", {"name": "Complete"})
            completed = 0
            for start in range(0, spec["count"], 20):
                batch = min(20, spec["count"] - start)
                result = js(client, f"for(let i=0;i<{batch};i++)await app.click({idx});",
                            f"Rapid action batch {start // 20 + 1}", timeout_ms=120000)
                operations = result.get("_meta", {}).get("hypr-use/timing", {}).get("operations", [])
                completed += sum(operation.get("name") == "click" for operation in operations)
            observed = perform(client, {"tool": "get_app_state", "app": "forms-app"})
            state_count = f"Completed {spec['count']}" in text_content(observed)
            evidence.update(completed=completed, expected=spec["count"], state_count=state_count)
            passed = completed == spec["count"] and state_count
        elif kind == "latency":
            before = time.monotonic()
            result = js(client, bind_code("list-app") + "await app.getAXState({maxRecords:8000,timeBudgetMs:30000,disableDiffing:true});", "Extract all list rows", timeout_ms=45000)
            elapsed = (time.monotonic() - before) * 1000
            observed = {int(value) for value in re.findall(r"\bItem (\d+)\b", text_content(result))}
            complete = observed == set(range(1, 1001))
            evidence.update(elapsed_ms=elapsed, observed_rows=len(observed), all_rows_visible=complete,
                            row_1000_visible=1000 in observed, limit_ms=spec["limit_ms"])
            passed = complete
        elif kind == "launch":
            bound = []; identities = []
            for number in range(spec["count"]):
                launch_state = directory / f"launch-{number}"; launch_state.mkdir()
                command = ["env", f"BENCH_STATE_DIR={launch_state}", "python3", str(Path(__file__).resolve().parents[1] / "apps" / "bench_app.py"), "forms-app"]
                result = js(client, f"globalThis.launch{number}=await cua.launch({json.dumps(command)});", f"Launch {number+1}")
                text = text_content(result); match = __import__("re").search(r"Target: (address:[^\s]+)", text); bound.append(bool(match)); identities.append(match.group(1) if match else None)
            evidence.update(bound=bound, identities=identities); passed = all(bound) and len(set(identities)) == spec["count"]
            evidence["host_verification"] = verify_t6_host(task, directory, host_clients())
            for number in range(spec["count"]):
                try: js(client, f"await launch{number}.performSecondaryAction(0,'window.close');", f"Close launch {number+1}")
                except Exception: pass
        elif kind == "restart":
            perform(client, {"tool": "get_app_state", "app": "forms-app"}); client.close(); client = Client({"HYPR_USE_WIRE_LOG": str(directory / "wire-2.jsonl")}); result = perform(client, {"tool": "get_app_state", "app": "forms-app"})
            passed = bool(text_content(result)); evidence["rebound"] = passed
        elif kind == "parallel":
            outcomes: list[dict[str, Any]] = []
            def worker(target: str) -> None:
                other = Client({**client_overrides(kind, target), "HYPR_USE_WIRE_LOG": str(directory / f"wire-{target}.jsonl")})
                try:
                    try:
                        worker_state = directory / f"parallel-{target}"; worker_state.mkdir(exist_ok=True)
                        command = ["env", f"BENCH_STATE_DIR={worker_state}", "python3", str(Path(__file__).resolve().parents[1] / "apps" / "bench_app.py"), target]
                        code = f"var owned=await cua.launch({json.dumps(command)});var ws=await cua.myWorkspace();var apps=await cua.listWorkspaceApps({{emit:false}});nodeRepl.write(JSON.stringify({{workspace:ws.workspace,workspaceInfo:ws,ownRows:apps.filter(x=>x.mine)}}));"
                        content = text_content(js(other, code, "Parallel isolated frame")); match = __import__("re").search(r'\{"workspace".*\}', content); outcomes.append(json.loads(match.group(0)) if match else {"error": "parallel worker emitted no structured evidence"})
                    except Exception as exc: outcomes.append({"target": target, "error": str(exc)})
                finally: other.close()
            targets = ["forms-app", "editor-app"][:spec["count"]]; threads = [threading.Thread(target=worker, args=(target,)) for target in targets]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
            workspaces = [outcome.get("workspace") for outcome in outcomes]
            excluded = parallel_isolated(outcomes, spec["count"])
            evidence.update(outcomes=outcomes, distinct_workspaces=len(set(workspaces)), cross_excluded=excluded); passed = excluded
            evidence["host_verification"] = verify_t6_host(task, directory, host_clients())
            cleanup_t6_host(task, directory)
        elif kind == "text":
            target_app = "editor-app" if "\n" in spec["value"] else "forms-app"; target_name = "Document" if target_app == "editor-app" else "Name"
            idx = index_for(client, target_app, {"name": target_name}); method = "paste" if target_app == "forms-app" else "typeText"
            options = {"format": "text"} if method == "paste" else {"replaceAll": True}
            result = js(client, bind_code(target_app) + f"await app.click({idx});await app.{method}({json.dumps(spec['value'])},{json.dumps(options)});", f"{method} fidelity benchmark")
            observed = perform(client, {"tool": "get_app_state", "app": target_app}); names = [op.get("name") for op in result.get("_meta", {}).get("hypr-use/timing", {}).get("operations", [])]
            operation = "paste_text" if method == "paste" else "type_text"
            passed = spec["value"] in text_content(observed) and operation in names; evidence.update(round_trip=passed, primitive=operation, operations=names)
        elif kind == "click":
            if spec["mode"] == "index": perform(client, {"tool": "click", "app": "forms-app", "target": {"name": "Complete"}})
            else:
                point = point_for(client, "forms-app", {"name": "Complete"})
                js(client, bind_code("forms-app") + f"await app.click({json.dumps(point)});", "Pixel click benchmark")
            result = perform(client, {"tool": "get_app_state", "app": "forms-app"}); passed = "Completed" in text_content(result); evidence.update(completed=passed, target_mode=spec["mode"])
        elif kind == "tracking":
            samples = []
            for _ in range(spec["count"]):
                content = text_content(perform(client, {"tool": "get_app_state", "app": "forms-app"})); match = __import__("re").search(r"button Complete.*Frame: (\[[^]]+\])", content); samples.append(match.group(1) if match else "")
            evidence.update(tracked=sum(bool(sample) for sample in samples), distinct_frames=len(set(samples))); passed = all(samples) and len(set(samples)) > 1
        else: raise RuntimeError(f"unknown tool benchmark {kind}")
    finally:
        cleanup_t6_host(task, directory)
        client.close()
    evidence.update(tool_passed=passed, wall_s=time.monotonic() - started); (directory / "tool-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n"); return evidence
