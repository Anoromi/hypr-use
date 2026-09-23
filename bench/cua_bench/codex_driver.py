from __future__ import annotations

import json
import os
import signal
import subprocess
from pathlib import Path
from typing import Any


def token_auth(codex_home: str | None) -> Path:
    if not codex_home: raise RuntimeError("Codex benchmark requires an isolated token-only CODEX_HOME")
    auth = Path(codex_home) / "auth.json"
    try: payload = json.loads(auth.read_text())
    except (OSError, json.JSONDecodeError) as exc: raise RuntimeError("Codex token auth is unavailable") from exc
    lowered = json.dumps(payload).lower()
    if not payload.get("tokens") or "api_key" in lowered or "sk-" in lowered: raise RuntimeError("Codex benchmark refuses missing or API-key auth")
    return auth


def command(*, model: str, cwd: Path, mcp_command: str, mcp_args: list[str], mcp_env: dict[str, str], output: Path) -> list[str]:
    env_toml = "{" + ",".join(key + "=" + json.dumps(value) for key, value in mcp_env.items()) + "}"
    return [
        "codex", "exec", "--ignore-user-config", "--skip-git-repo-check", "--json", "--ephemeral",
        "-C", str(cwd), "-m", model, "-s", "read-only", "-c", 'approval_policy="never"',
        "-c", 'model_reasoning_effort="low"',
        "-c", "features.shell_tool=false", "-c", "features.plugins=false", "-c", "features.multi_agent=false",
        "-c", f"mcp_servers.cua_repl.command={json.dumps(mcp_command)}",
        "-c", "mcp_servers.cua_repl.args=" + json.dumps(mcp_args),
        "-c", "mcp_servers.cua_repl.env=" + env_toml,
        "-c", 'mcp_servers.cua_repl.default_tools_approval_mode="approve"',
        "-c", "mcp_servers.cua_repl.required=true", "-o", str(output), "-",
    ]


def run(*, prompt: str, model: str, cwd: Path, mcp_command: str, mcp_args: list[str], mcp_env: dict[str, str], output: Path, timeout: int, codex_home: str | None = None) -> tuple[int, list[dict[str, Any]], str]:
    token_auth(codex_home)
    try:
        driver_env = os.environ.copy()
        if codex_home: driver_env["CODEX_HOME"] = codex_home
        driver_env.pop("OPENAI_API_KEY", None); driver_env.pop("OPENAI_BASE_URL", None)
        proc = subprocess.Popen(command(model=model, cwd=cwd, mcp_command=mcp_command, mcp_args=mcp_args, mcp_env=mcp_env, output=output), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=driver_env, start_new_session=True)
        try: stdout, stderr = proc.communicate(prompt, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            os.killpg(proc.pid, signal.SIGTERM)
            try: stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL); stdout, stderr = proc.communicate()
            events = []
            for line in (stdout or "").splitlines():
                try:
                    decoded = json.loads(line)
                    events.append(decoded if isinstance(decoded, dict) else {"type": "raw", "value": decoded})
                except json.JSONDecodeError: events.append({"type": "raw", "text": line})
            events.append({"type": "error", "timeout": True, "message": str(exc)})
            return 124, events, stderr or str(exc)
    except OSError as exc:
        return 127, [{"type": "error", "message": str(exc)}], str(exc)
    events = []
    for line in stdout.splitlines():
        try:
            decoded = json.loads(line)
            events.append(decoded if isinstance(decoded, dict) else {"type": "raw", "value": decoded})
        except json.JSONDecodeError: events.append({"type": "raw", "text": line})
    return proc.returncode, events, stderr
