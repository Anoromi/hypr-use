#!@PYTHON@
"""Launch the packaged unified MCP in this session or a saved headless session."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

DEFAULT_MEMORY_MAX = "8G"
HOST_BIN = "/run/current-system/sw/bin"


def systemd_tool(name):
    return shutil.which(name) or (f"{HOST_BIN}/{name}" if os.access(f"{HOST_BIN}/{name}", os.X_OK) else None)


def user_manager_reachable(systemctl):
    """False in non-systemd sessions and on the lab's private D-Bus."""
    try:
        probe = subprocess.run([systemctl, "--user", "show", "-p", "Version", "--value"],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0 and bool(probe.stdout.strip())


def enter_scope(args):
    """Re-exec this launcher inside a capped transient scope.

    Node, the Python portal backend, and every worker they start inherit the
    scope, so a leak is OOM-killed inside it instead of failing the caller's
    scope (T3 Code's, when an agent starts the server). OOMPolicy=continue
    keeps the scope running after a kill. Returns only when no user manager
    is reachable or scoping is disabled; the server then runs unscoped.
    """
    if os.environ.get("HYPR_USE_MCP_SCOPE") or os.environ.get("HYPR_USE_NO_SCOPE") == "1":
        return
    systemd_run, systemctl = systemd_tool("systemd-run"), systemd_tool("systemctl")
    if not systemd_run or not systemctl or not user_manager_reachable(systemctl):
        return
    memory_max = os.environ.get("HYPR_USE_MEMORY_MAX") or DEFAULT_MEMORY_MAX
    unit = f"hypr-use-mcp-{os.getpid()}.scope"
    argv = [systemd_run, "--user", "--scope", "--quiet", "--collect", "--unit", unit,
            "--description", "hypr-use MCP server",
            "-p", f"MemoryMax={memory_max}", "-p", "MemorySwapMax=0", "-p", "OOMPolicy=continue",
            sys.executable, os.path.abspath(__file__), *args]
    os.execve(systemd_run, argv, dict(os.environ, HYPR_USE_MCP_SCOPE=unit))


def usage():
    print("Usage: hypr-use-mcp [--headless] [--help]", file=sys.stderr)


def main():
    args = sys.argv[1:]
    if args == ["--help"]:
        usage()
        return 0
    if args not in ([], ["--headless"]):
        usage()
        return 2
    enter_scope(args)
    env = os.environ.copy()
    if args == ["--headless"]:
        config = Path(os.environ.get("HYPR_USE_HEADLESS_ENV", str(Path.home() / ".local/share/hypr-use/headless-env.json")))
        try:
            saved = json.loads(config.read_text())
        except (OSError, ValueError) as exc:
            sys.exit(f"hypr-use-mcp: cannot read headless session {config}: {exc}")
        if not isinstance(saved, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in saved.items()):
            sys.exit(f"hypr-use-mcp: invalid headless session {config}")
        env.update(saved)
    missing = [key for key in ("XDG_RUNTIME_DIR", "WAYLAND_DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE") if not env.get(key)]
    if missing:
        sys.exit("hypr-use-mcp: missing session variables: " + ", ".join(missing))
    runtime = Path(env["XDG_RUNTIME_DIR"])
    endpoints = (runtime / env["WAYLAND_DISPLAY"], runtime / "hypr" / env["HYPRLAND_INSTANCE_SIGNATURE"] / ".socket.sock")
    for endpoint in endpoints:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                probe.settimeout(2)
                probe.connect(str(endpoint))
        except OSError as exc:
            sys.exit(f"hypr-use-mcp: session socket unavailable: {endpoint}: {exc}")
    for key in ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_ENTRYPOINT"):
        env.pop(key, None)
    env.setdefault("HYPR_AGENT_PORTAL_PERMISSION_MODE", "full")
    env.setdefault("HYPR_AGENT_PORTAL_APPROVAL_POLICY", "never")
    env["HYPR_USE_PYTHON"] = "@PYTHON@"
    env["PATH"] = "@PATH@" + os.pathsep + env.get("PATH", "")
    env["GI_TYPELIB_PATH"] = "@TYPELIB_PATH@" + os.pathsep + env.get("GI_TYPELIB_PATH", "")
    os.execve("@NODE@", ["@NODE@", "@SERVER@"], env)


if __name__ == "__main__":
    raise SystemExit(main())
