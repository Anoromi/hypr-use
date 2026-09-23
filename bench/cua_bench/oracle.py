from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .mcp_bridge import Client, perform


class OracleError(RuntimeError):
    def __init__(self, message: str, events: list[dict[str, Any]], tool_calls: int):
        super().__init__(message); self.events = events; self.tool_calls = tool_calls


def run_oracle(actions: list[dict[str, Any]], transcript_path: Path) -> list[dict[str, Any]]:
    events = []
    client = Client()
    try:
        for sequence, action in enumerate(actions, 1):
            started = time.monotonic()
            calls_before = client.tool_calls
            result = perform(client, action)
            events.append({"sequence": sequence, "request": action, "result": result, "mcp_calls": client.tool_calls - calls_before, "duration_ms": round((time.monotonic() - started) * 1000, 3)})
            transcript_path.write_text("".join(json.dumps(event) + "\n" for event in events))
        return events
    except Exception as exc:
        raise OracleError(str(exc), events, client.tool_calls) from exc
    finally:
        client.close()
