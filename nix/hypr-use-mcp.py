#!@PYTHON@
"""Launch the packaged unified MCP in this session or a saved headless session."""
import json
import os
from pathlib import Path
import socket
import sys


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
