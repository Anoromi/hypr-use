#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SERVER = Path(__file__).resolve().parents[2] / "mcp" / "unified" / "server.mjs"
LAB_ENV = Path(__file__).resolve().parents[3] / "hypr-testbed" / "lab" / "env.json"
LAB_MCP = LAB_ENV.with_name("cua-mcp")
ALIASES = {name: "dev.hypruse.bench." + name.replace("-", "") for name in ("forms-app", "list-app", "editor-app", "dialog-storm", "multi-window-app", "stress-app")}


class Client:
    def __init__(self, overrides: dict[str, str] | None = None) -> None:
        env = os.environ.copy()
        if LAB_ENV.exists(): env.update(json.loads(LAB_ENV.read_text()))
        env.setdefault("HYPR_AGENT_PORTAL_PERMISSION_MODE", "full")
        env.setdefault("HYPR_AGENT_PORTAL_APPROVAL_POLICY", "never")
        env.setdefault("HYPR_USE_APP_ALIASES", json.dumps(ALIASES))
        env.setdefault("HYPR_USE_FAST_CONTROL", "0")
        env.setdefault("HYPR_USE_NO_HYPRNAV", "1")
        env.update(overrides or {})
        packaged_mcp = os.environ.get("HYPR_USE_PACKAGED_MCP")
        command = [packaged_mcp] if packaged_mcp else ["node", str(SERVER)]
        self.proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        self.sequence = 0; self.tool_calls = 0
        self.call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "cua-bench", "version": "0.1"}})

    def call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.sequence += 1
        assert self.proc.stdin and self.proc.stdout
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.sequence, "method": method, "params": params}) + "\n"); self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP server closed: " + (self.proc.stderr.read() if self.proc.stderr else ""))
        data = json.loads(line)
        if "error" in data: raise RuntimeError(data["error"]["message"])
        return data["result"]

    def tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.tool_calls += 1
        result = self.call("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            text = "; ".join(b.get("text", "") for b in result.get("content", []) if b.get("type") == "text")
            raise RuntimeError(text or f"{name} failed")
        return result

    def close(self) -> None:
        if self.proc.stdin: self.proc.stdin.close()
        try: self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired: self.proc.terminate()


def js(client: Client, code: str, title: str, timeout_ms: int = 45000) -> dict[str, Any]:
    return client.tool("js", {"code": code, "title": title, "timeout_ms": timeout_ms})


def bind_code(app: str, window: str | None = None) -> str:
    selector = ALIASES.get(app, app)
    # Let the runtime resolve a class/title to its newest matching process.
    # Passing an address selected from listApps bypasses that freshness policy.
    return f"var app=await cua.getApp({json.dumps(window or selector)});"


def text_content(result: dict[str, Any]) -> str:
    return "\n".join(block.get("text", "") for block in result.get("content", []) if block.get("type") == "text")


def index_for(client: Client, app: str, target: dict[str, Any], window: str | None = None) -> int:
    result = js(client, bind_code(app, window), "Observe target")
    name = target["name"]
    candidates = []; matching_lines = []
    for line in text_content(result).splitlines():
        match = re.match(r"\s*(\d+)\b.*", line)
        exact = re.match(rf"\s*\d+\s+(?:[a-z]+(?: [a-z]+)?)\s+{re.escape(name)}(?= (?:Secondary Actions:|Checked:|Value:|SetValue:|Frame:))", line)
        if match and exact: candidates.append(int(match.group(1))); matching_lines.append(line)
    preferred = [int(re.match(r"\s*(\d+)", line).group(1)) for line in matching_lines if " label " not in line]
    clickable = [int(re.match(r"\s*(\d+)", line).group(1)) for line in matching_lines if "Secondary Actions: click" in line]
    candidates = list(dict.fromkeys(clickable or preferred or candidates))
    if len(candidates) != 1: raise RuntimeError(f"expected one AX target named {name!r}, found {candidates}: {matching_lines}")
    return candidates[0]


def dialog_index_for(client: Client, target: dict[str, Any]) -> int:
    result = js(client, "await dialog.getAXState({disableDiffing:true});", "Observe dialog target")
    name = target["name"]; candidates = []
    for line in text_content(result).splitlines():
        match = re.match(r"\s*(\d+)\b.*", line)
        exact = re.search(rf"\b{re.escape(name)}\b(?= (?:Secondary Actions:|Checked:|Value:|SetValue:|Frame:))", line)
        if match and exact and " label " not in line: candidates.append(int(match.group(1)))
    candidates = list(dict.fromkeys(candidates))
    if len(candidates) != 1: raise RuntimeError(f"expected one dialog AX target named {name!r}, found {candidates}")
    return candidates[0]


def point_for(client: Client, app: str, target: dict[str, Any]) -> tuple[int, int]:
    result = js(client, bind_code(app), "Observe drag geometry")
    name = target["name"]; matches = []
    for line in text_content(result).splitlines():
        if f'"{name}"' not in line and name not in line: continue
        frame = re.search(r"(?:frame|bounds)[=: ]+\[\s*(-?\d+),\s*(-?\d+),\s*(\d+),\s*(\d+)\s*\]", line, re.I)
        if frame: matches.append(tuple(map(int, frame.groups())))
    if len(matches) != 1: raise RuntimeError(f"expected one visible drag target named {name!r}, found {len(matches)}")
    x, y, width, height = matches[0]; return x + width // 2, y + height // 2


def perform(client: Client, action: dict[str, Any]) -> dict[str, Any]:
    tool, app = action["tool"], action.get("app")
    if tool == "copy_value":
        observed = perform(client, {"tool": "get_app_state", "app": action["from_app"], "window": action.get("from_window")})
        match = re.search(action["pattern"], text_content(observed))
        if not match: raise RuntimeError(f"copy source pattern did not match: {action['pattern']}")
        value_match = re.search(action.get("value_pattern", action["pattern"]), match.group(0))
        value = value_match.group(1) if value_match and value_match.groups() else match.group(1)
        return perform(client, {"tool": "set_value", "app": action["to_app"], "target": action["target"], "value": value})
    if tool == "launch":
        command = ["python3", str(Path(__file__).resolve().parents[1] / "apps" / "bench_app.py"), app]
        return js(client, f"var app=await cua.launch({json.dumps(command)});", "Launch benchmark app")
    if tool == "get_app_state": return js(client, bind_code(app, action.get("window")) + "await app.getAXState({disableDiffing:true});", "Observe benchmark app")
    if tool == "get_dialog": return js(client, bind_code(app) + f"var dialog=await app.getDialog({json.dumps({'title': action.get('title', 'Delayed approval'), 'timeout_ms': action.get('wait_ms', 10000)})});", "Bind related dialog")
    if tool == "select_options": return js(client, bind_code(app) + f"await app.selectOptions({json.dumps({'choices': action['choices']})});", "Oracle select options")
    if tool == "dialog_click":
        idx = dialog_index_for(client, action["target"])
        return js(client, f"await dialog.performSecondaryAction({idx},'click');", "Oracle dialog click")
    if "target" in action: idx = index_for(client, app, action["target"], action.get("window"))
    if tool == "click" and "x" in action: code = bind_code(app) + f"await app.click({json.dumps([action['x'], action['y']])});"
    elif tool == "click": code = f"await app.click({idx});"
    elif tool == "set_value": code = f"await app.setValue({idx},{json.dumps(action['value'])});"
    elif tool == "press_key": code = bind_code(app) + f"await app.pressKey({json.dumps(action['key'])});"
    elif tool == "type_text": code = bind_code(app) + f"await app.typeText({json.dumps(action['text'])});"
    elif tool == "scroll": code = f"await app.scroll({idx},{json.dumps(action['direction'])},{action.get('pages',1)});"
    elif tool == "drag":
        start = point_for(client, app, action["from"]); end = point_for(client, app, action["to"])
        code = f"await app.drag({json.dumps(start)},{json.dumps(end)});"
    else: raise RuntimeError(f"unsupported oracle tool {tool}")
    return js(client, code, f"Oracle {tool}")


def main() -> int:
    request = json.loads(sys.stdin.readline()); client = Client()
    try:
        result = perform(client, request)
        print(json.dumps({"ok": True, "meta": result.get("_meta", {})}))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)})); return 1
    finally: client.close()


if __name__ == "__main__": raise SystemExit(main())
