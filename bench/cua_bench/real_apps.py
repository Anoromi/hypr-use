from __future__ import annotations

import json
import base64
import os
import signal
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import time
from pathlib import Path

from .catalog import ROOT
from .mcp_bridge import Client, js, text_content


def _require(group: str) -> str:
    found = next((shutil.which(name) for name in group.split("|") if shutil.which(name)), None)
    if not found: raise RuntimeError(f"prerequisite_unavailable: {group}")
    return found


def _keys(client: Client, bind: str, keys: list[str]) -> None:
    for key in keys: js(client, bind + f"await app.pressKey({json.dumps(key)});", "Real-app keyboard action")


def _isolated_launcher(sandbox: Path, binary: str, name: str) -> Path:
    launcher = sandbox / name
    home = sandbox / "home"; config = sandbox / "config"; cache = sandbox / "cache"; state = sandbox / "state"
    for path in (home, config, cache, state): path.mkdir(exist_ok=True)
    launcher.write_text("#!/bin/sh\n" + "\n".join([
        f"export HOME={str(home)!r}", f"export XDG_CONFIG_HOME={str(config)!r}",
        f"export XDG_CACHE_HOME={str(cache)!r}", f"export XDG_STATE_HOME={str(state)!r}",
        f"exec {binary!r} \"$@\"",
    ]) + "\n"); launcher.chmod(0o700); return launcher


def _owned_processes(sandbox: Path) -> dict[int, str]:
    wanted = str(sandbox / "home").encode()
    found = {}
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            if b"HOME=" + wanted + b"\0" in (proc / "environ").read_bytes():
                found[int(proc.name)] = (proc / "stat").read_text().rsplit(")", 1)[1].split()[19]
        except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError): pass
    return found


def _cleanup_owned(owned: dict[int, str]) -> None:
    for pid, starttime in owned.items():
        try:
            if Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19] == starttime: os.kill(pid, signal.SIGTERM)
        except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError): pass


def run(task_id: str, output: Path) -> dict:
    specs = {row["id"]: row for row in json.loads((ROOT / "real-tasks.json").read_text())}
    spec = specs[task_id]; output.mkdir(parents=True, exist_ok=True)
    try:
        binaries = [_require(group) for group in spec["requires"]]
    except RuntimeError as exc:
        result = {"id": task_id, "passed": False, "failure_class": "prerequisite_unavailable", "detail": str(exc)}
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n"); return result
    sandbox = Path(tempfile.mkdtemp(prefix=f"cua-{task_id}-", dir=output)); client = Client({
        "HYPR_USE_NO_HYPRNAV": "0", "T3CODE_THREAD_ID": "real-" + task_id,
        "T3CODE_ENVIRONMENT_ID": str(sandbox), "HYPR_USE_ENV_ID": str(sandbox)})
    evidence = ""
    server = None; launched = False; owned = {}
    try:
        launchers = [_isolated_launcher(sandbox, binary, f"launch-{i}") for i, binary in enumerate(binaries)]
        if task_id == "real-nautilus-folder":
            workspace = sandbox / "workspace"; workspace.mkdir(); (workspace / "note.txt").write_text("bench\n"); uri = workspace.as_uri()
            js(client, f"var app=await cua.launch({json.dumps([str(launchers[0]), '--new-window', uri])});", "Launch isolated Nautilus"); launched=True
            owned = _owned_processes(sandbox); bind = ""; evidence += text_content(js(client, "await app.getAXState({disableDiffing:true});", "Wait for Nautilus")); _keys(client, bind, ["Ctrl+Shift+n"]); js(client, bind + "await app.typeText('Archive');await app.pressKey('Enter');", "Create folder")
            _keys(client, bind, ["a", "F2"]); js(client, bind + "await app.typeText('Filed',{replaceAll:true});await app.pressKey('Enter');", "Rename folder")
            _keys(client, bind, ["n", "Ctrl+x", "f", "Enter", "Ctrl+v"]); time.sleep(1)
            time.sleep(1); passed = (workspace / "Filed" / "note.txt").is_file() and not (workspace / "Archive").exists()
        elif task_id == "real-zen-local-form":
            submitted = sandbox / "submitted.txt"
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    body=b'''<label>Name <input id=n autofocus></label><button onclick="fetch('/submit',{method:'POST',body:n.value}).then(()=>document.body.innerHTML='<h1>Receipt ZEN-284</h1><p>'+n.value+'</p>')">Submit</button>'''
                    self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(body)
                def do_POST(self):
                    submitted.write_bytes(self.rfile.read(int(self.headers.get("Content-Length", "0")))); self.send_response(204); self.end_headers()
                def log_message(self, *_): pass
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler); threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{server.server_port}/"
            js(client, f"var app=await cua.launch({json.dumps([str(launchers[0]), '--new-instance', '--no-remote', '--profile', str(sandbox / 'profile'), url])});", "Launch isolated Zen"); launched=True
            owned = _owned_processes(sandbox); bind = ""; evidence += text_content(js(client, "await app.getAXState({disableDiffing:true});", "Wait for Zen")); js(client, bind + "await app.typeText('Aster');await app.pressKey('Tab');await app.pressKey('Enter');", "Complete local form"); time.sleep(1); evidence += "\n" + text_content(js(client, bind + "await app.getAXState({disableDiffing:true});", "Read receipt")); passed = "ZEN-284" in evidence and "Aster" in evidence
            passed = passed and submitted.read_text() == "Aster" if submitted.exists() else False
        elif task_id == "real-terminal-output":
            terminal = str(launchers[0]); command = [terminal, "--class", "cua-real-terminal", "bash", "--noprofile", "--norc"] if binaries[0].endswith("kitty") else [terminal, "-e", "sh"]
            js(client, f"var app=await cua.launch({json.dumps(command)});", "Launch isolated terminal"); launched=True; owned = _owned_processes(sandbox); bind = ""
            evidence += text_content(js(client, "await app.getAXState({disableDiffing:true});", "Wait for terminal")); transcript=sandbox/'transcript.txt'; js(client, bind + f"await app.typeText({json.dumps('printf BENCH-417\\\\n | tee '+str(transcript))});await app.pressKey('Enter');", "Run terminal command"); time.sleep(1); evidence += "\n" + text_content(js(client, bind + "await app.getAXState({disableDiffing:true});", "Read terminal output")); passed = "BENCH-417" in evidence and transcript.exists() and "BENCH-417" in transcript.read_text()
        else:
            js(client, f"var app=await cua.launch({json.dumps([str(launchers[0])])});", "Launch isolated calculator"); launched=True; owned = _owned_processes(sandbox); bind = ""
            evidence += text_content(js(client, "await app.getAXState({disableDiffing:true});", "Wait for calculator")); js(client, bind + "await app.typeText('(73*19)+8');await app.pressKey('Enter');", "Calculate expression"); time.sleep(1); evidence += "\n" + text_content(js(client, bind + "await app.getAXState({disableDiffing:true});", "Read calculator result")); passed = "1395" in evidence
        try:
            shot = js(client, "await app.getScreenshot({emit:true});", "Capture real-app evidence")
            image = next((b for b in shot.get("content", []) if b.get("type") == "image"), None)
            if image: (output / "screenshot.png").write_bytes(base64.b64decode(image["data"]))
        except Exception as exc: evidence += "\nscreenshot_error: " + str(exc)
        result = {"id": task_id, "passed": passed, "failure_class": None if passed else "wrong_action", "detail": "state grader passed" if passed else "expected real application state absent", "sandbox": str(sandbox)}
    except Exception as exc: result = {"id": task_id, "passed": False, "failure_class": "tool_error", "detail": str(exc), "sandbox": str(sandbox)}
    finally:
        if server: server.shutdown(); server.server_close()
        if launched:
            try: js(client, "await app.close();", "Close isolated real application")
            except Exception: pass
        _cleanup_owned(owned)
        client.close()
    (output / "evidence.txt").write_text(evidence); (output / "result.json").write_text(json.dumps(result, indent=2) + "\n"); return result
