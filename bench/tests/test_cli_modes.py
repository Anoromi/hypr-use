import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from cua_bench.catalog import load_tasks
from cua_bench.cli import agent_executor, agent_prompt


TASKS = {task.id: task for task in load_tasks()}


class CliModeTests(unittest.TestCase):
    def test_every_task_builds_an_agent_prompt(self):
        for task in TASKS.values():
            prompt = agent_prompt(task)
            self.assertIn(task.seed, prompt, task.id)
            self.assertNotIn("Target application: stress-app", prompt, task.id)

    def test_parallel_agent_phases_overlap_and_use_unique_identities(self):
        barrier = threading.Barrier(2); environments = []
        def fake_codex(**kwargs):
            environments.append(kwargs["mcp_env"]); barrier.wait(timeout=2)
            return 0, [], ""
        class Done:
            stdout = json.dumps({"CODEX_HOME": "/token-home"})
        with tempfile.TemporaryDirectory() as raw, patch("cua_bench.cli.lab", return_value=Done()), patch("cua_bench.cli.run_codex", side_effect=fake_codex):
            agent_executor("gpt-5.6-sol", 10)(TASKS["t6-05-parallel-2"], Path(raw), {}, Path(raw))
        self.assertEqual(len(environments), 2)
        self.assertEqual({env["HYPR_USE_NO_HYPRNAV"] for env in environments}, {"0"})
        self.assertEqual(len({env["HYPR_USE_AGENT_ID"] for env in environments}), 2)
        self.assertEqual(len({env["HYPR_USE_WIRE_LOG"] for env in environments}), 2)

    def test_restart_uses_two_fresh_phase_logs(self):
        environments = []
        def fake_codex(**kwargs): environments.append(kwargs["mcp_env"]); return 0, [], ""
        class Done:
            stdout = json.dumps({"CODEX_HOME": "/token-home"})
        with tempfile.TemporaryDirectory() as raw, patch("cua_bench.cli.lab", return_value=Done()), patch("cua_bench.cli.run_codex", side_effect=fake_codex):
            agent_executor("gpt-5.6-sol", 10)(TASKS["t6-04-restart"], Path(raw), {}, Path(raw))
        self.assertEqual([Path(env["HYPR_USE_WIRE_LOG"]).name for env in environments], ["wire-1.jsonl", "wire-2.jsonl"])


if __name__ == "__main__": unittest.main()
