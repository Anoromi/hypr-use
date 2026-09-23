import tempfile
import unittest
from pathlib import Path

from cua_bench.catalog import Task
from cua_bench.runner import Execution, Mode, execute, result_for


def task():
    return Task("x", "T1", "forms-app", "x", "do it", 3, 0, {"checks": [{"path": "done", "value": True}]}, [])


class RunnerTests(unittest.TestCase):
    def test_authoritative_fields_cannot_be_overwritten(self):
        row = result_for(task(), Mode.AGENTIC, Execution(fields={"passed": True, "mode": "wrong", "tool_calls": 2}), {}, Path("x"), 0)
        self.assertFalse(row["passed"]); self.assertEqual(row["mode"], "agentic"); self.assertEqual(row["tool_calls"], 2)

    def test_recovered_infrastructure_error_does_not_erase_completion(self):
        row = result_for(task(), Mode.AGENTIC, Execution(events=[{"tool_error": "first attempt failed"}], fields={"steps": 3}),
                         {"done": True}, Path("x"), 0)
        self.assertTrue(row["passed"]); self.assertEqual(row["steps"], 3)
        self.assertEqual(row["infrastructure_errors"], ["first attempt failed"])

    def test_both_modes_share_setup_grader_and_recording(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); calls = []
            def setup(_task): calls.append("setup"); return {}, root
            def start(path): calls.append("start"); path.write_bytes(b"video")
            def stop(): calls.append("stop")
            for mode in (Mode.AGENTIC, Mode.SCRIPTED):
                row = execute(task(), mode, root / mode.value, setup=setup, record_start=start, record_stop=stop,
                              executor=lambda *_: Execution(), state_reader=lambda *_: {"done": True})
                self.assertTrue(row["passed"]); self.assertTrue(Path(row["recording"]).is_file())
            self.assertEqual(calls, ["setup", "start", "stop"] * 2)

    def test_setup_failure_persists_failed_result_and_continues(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            row = execute(task(), Mode.SCRIPTED, root, setup=lambda _task: (_ for _ in ()).throw(RuntimeError("seed failed")),
                          record_start=lambda _path: None, record_stop=lambda: None,
                          executor=lambda *_: Execution(), state_reader=lambda *_: {})
            self.assertFalse(row["passed"]); self.assertEqual(row["failure_class"], "driver_error")
            self.assertTrue((root / "result.json").is_file())
