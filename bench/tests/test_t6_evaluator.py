import json
import tempfile
import unittest
from pathlib import Path

from cua_bench.catalog import load_tasks
from cua_bench.t6_evaluator import evaluate


TASKS = {task.id: task for task in load_tasks()}


def wire(path: Path, code: str, content: str, operations: list[str], total_ms: float = 10) -> None:
    row = {
        "request": {"params": {"name": "js", "arguments": {"code": code}}},
        "response": {"result": {"content": [{"type": "text", "text": content}], "isError": False,
                                "_meta": {"hypr-use/timing": {"total_ms": total_ms,
                                                               "operations": [{"name": name} for name in operations]}}}},
    }
    with path.open("a") as target:
        target.write(json.dumps(row) + "\n")


class T6EvaluatorTests(unittest.TestCase):
    def test_ax1000_requires_every_row_in_one_observation(self):
        task = TASKS["t6-02-ax-1000"]; state = {"apps": {"list-app": {"rows": 1000}}}
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "wire.jsonl"
            wire(path, "await app.getAXState();", "Item 1000", ["get_ax_state"])
            self.assertFalse(evaluate(task, state, [path], [])[0])
            path.unlink()
            wire(path, "await app.getAXState();", "\n".join(f"Item {i}" for i in range(1, 1001)), ["get_ax_state"])
            passed, evidence = evaluate(task, state, [path], [])
            self.assertTrue(passed); self.assertEqual(evidence["observed_rows"], 1000)

    def test_rapid_requires_exact_state_and_operations(self):
        task = TASKS["t6-01-rapid-200"]
        events = [{"tool_benchmark": {"tool_passed": True, "completed": 200}}]
        passed, _ = evaluate(task, {"apps": {"forms-app": {"click_count": 199}}}, [], events)
        self.assertFalse(passed)
        passed, _ = evaluate(task, {"apps": {"forms-app": {"click_count": 200}}}, [], events)
        self.assertTrue(passed)

    def test_text_ignores_tool_passed_and_checks_primitive(self):
        task = TASKS["t6-06-unicode"]
        state = {"apps": {"forms-app": {"name": "東京 café 👋"}}}
        self.assertFalse(evaluate(task, state, [], [{"tool_benchmark": {"tool_passed": True}}])[0])
        events = [{"tool_benchmark": {"tool_passed": False, "operations": ["paste_text"]}}]
        self.assertTrue(evaluate(task, state, [], events)[0])

    def test_index_click_requires_index_shape_and_final_state(self):
        task = TASKS["t6-08-click-index"]
        state = {"apps": {"forms-app": {"completed": True, "click_count": 1}}}
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "wire.jsonl"
            wire(path, "await app.click([90,540]);", "", ["click"])
            self.assertFalse(evaluate(task, state, [path], [])[0])
            path.unlink()
            wire(path, "await app.click(88);", "", ["click"])
            self.assertTrue(evaluate(task, state, [path], [])[0])

    def test_restart_requires_two_connections_with_same_target(self):
        task = TASKS["t6-04-restart"]
        with tempfile.TemporaryDirectory() as raw:
            first, second = Path(raw) / "first.jsonl", Path(raw) / "second.jsonl"
            text = "App: forms; Target: address:0xabc@pid=1@start=2"
            wire(first, "await app.getAXState();", text, ["get_ax_state"])
            self.assertFalse(evaluate(task, {}, [first], [])[0])
            wire(second, "await app.getAXState();", text, ["get_ax_state"])
            self.assertTrue(evaluate(task, {}, [first, second], [])[0])

    def test_restart_rejects_scripted_rebound_without_two_wires(self):
        task = TASKS["t6-04-restart"]
        event = {"tool_benchmark": {"tool_passed": True, "rebound": True}}
        self.assertFalse(evaluate(task, {}, [], [event])[0])

    def test_launch_counts_runtime_outputs_and_matches_trusted_snapshot(self):
        task = TASKS["t6-03-launch-10"]
        targets = [f"address:0x{i}" for i in range(10)]
        content = "\n".join(f"Launched python3 on workspace 1 as {target} (app: title)" for target in targets)
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "wire.jsonl"
            wire(path, "for(let i=0;i<10;i++)await cua.launch(argv);", content, ["get_ax_state"] * 10)
            event = {"t6_verification": {"launch_targets": targets}}
            self.assertTrue(evaluate(task, {}, [path], [event])[0])
            self.assertFalse(evaluate(task, {}, [path], [])[0])

    def test_parallel_requires_disjoint_owned_frames(self):
        task = TASKS["t6-05-parallel-2"]
        rows = [
            {"workspace": 1, "ownRows": [{"id": "a", "workspace": 1, "mine": True}]},
            {"workspace": 2, "ownRows": [{"id": "b", "workspace": 2, "mine": True}]},
        ]
        event = {"t6_verification": {"parallel_frames": rows}}
        with tempfile.TemporaryDirectory() as raw:
            paths = []
            for index, row in enumerate(rows):
                path = Path(raw) / f"wire-{index}.jsonl"; wire(path, "nodeRepl.write(...)" , json.dumps(row), []) ; paths.append(path)
            self.assertTrue(evaluate(task, {}, paths, [event])[0])
            self.assertFalse(evaluate(task, {}, [], [event])[0])
        rows[1]["ownRows"][0]["id"] = "a"
        self.assertFalse(evaluate(task, {}, paths, [event])[0])


if __name__ == "__main__":
    unittest.main()
