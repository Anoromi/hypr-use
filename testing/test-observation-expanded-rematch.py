"""Expanded AX limits survive observation caching and indexed-action rematching."""
import importlib.util
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "mcp/unified"))
from observations import Observations

spec = importlib.util.spec_from_file_location(
    "portal_expanded_rematch",
    root / "vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py",
)
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

seen = []
backend.snapshot_after_action = lambda *args: None
backend.SEMANTIC_TOOLS = {
    name: (lambda args, name=name: seen.append((name, args)) or args)
    for name in ("click", "scroll", "set_value", "select_text", "perform_secondary_action")
}
old = {"index": 7000, "source": "atspi", "controlType": "button", "name": "Item 1000", "runtimeId": [0, 1000]}
fresh = {"elements": [{**old, "index": 7100}]}

def build(query, **options):
    seen.append((query, options))
    return fresh

backend.build_app_snapshot = build
backend.snapshot_window_query = lambda snapshot, app: snapshot["target"]
observations = Observations(backend)
observations.publish("bound", {"target": "bound", "elements": [old], "axScan": {"maxRecords": 8000, "timeBudgetMs": 30000}})
backend.SEMANTIC_TOOLS["click"]({"app": "bound", "element_index": "7000", "element_click_mode": "auto"})

assert seen[0] == ("bound", {"ax_max_records": 8000, "ax_time_budget_ms": 30000})
assert seen[1][1]["element_index"] == "7100"
print("Expanded AX rematch preserves scan limits")
