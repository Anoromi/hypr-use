import json
import tempfile
import unittest
from pathlib import Path

from cua_bench.catalog import load_tasks
from cua_bench.t6_verification import cleanup, verify


TASKS = {task.id: task for task in load_tasks()}


def fixture(root: Path, folder: str, app: str, pid: int, starttime: int = 10) -> None:
    path = root / folder
    path.mkdir()
    (path / f"{app}.json").write_text(json.dumps({"app": app, "pid": pid, "starttime": starttime}))


def client(pid: int, address: str, workspace: int) -> dict:
    return {"pid": pid, "address": address, "workspace": {"id": workspace}, "mapped": True}


class TrustedT6VerificationTests(unittest.TestCase):
    def test_launch_uses_controlled_processes_not_agent_output(self):
        task = TASKS["t6-03-launch-10"]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for number in range(10): fixture(root, f"launch-{number}", "forms-app", 100 + number)
            clients = [client(100 + number, f"0x{number}", 7) for number in range(10)]
            result = verify(task, root, clients, read_starttime=lambda _pid: 10)
            self.assertEqual(len(result["launch_targets"]), 10)

    def test_agent_launch_rejects_unregistered_before_after_diff(self):
        task = TASKS["t6-03-launch-10"]
        before = [{**client(1, "0xseed", 7), "class": "dev.hypruse.bench.formsapp"}]
        after = before + [{**client(100 + number, f"0x{number}", 9), "class": "dev.hypruse.bench.formsapp"} for number in range(10)]
        agents = {f"cua-bench-{task.id}-1": 9}
        with tempfile.TemporaryDirectory() as raw:
            result = verify(task, Path(raw), after, before_clients=before, agent_workspaces=agents)
        self.assertEqual(result["launch_targets"], [])

    def test_agent_launch_preserves_each_controlled_process_identity(self):
        task = TASKS["t6-03-launch-10"]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for number in range(10): fixture(root, f"agent-launch-{number + 1}", "forms-app", 200 + number)
            clients = [client(200 + number, f"0xa{number}", 9) for number in range(10)]
            result = verify(task, root, clients, read_starttime=lambda _pid: 10)
            self.assertEqual(len(result["launch_targets"]), 10)

    def test_stale_pid_and_unmapped_client_are_rejected(self):
        task = TASKS["t6-03-launch-10"]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for number in range(10): fixture(root, f"launch-{number}", "forms-app", 100 + number)
            clients = [client(100 + number, f"0x{number}", 7) for number in range(10)]
            result = verify(task, root, clients, read_starttime=lambda pid: 11 if pid == 105 else 10)
            self.assertEqual(result["launch_targets"], [])
            clients[0]["mapped"] = False
            result = verify(task, root, clients, read_starttime=lambda _pid: 10)
            self.assertEqual(result["launch_targets"], [])

    def test_parallel_is_derived_from_phase_fixture_pids(self):
        task = TASKS["t6-05-parallel-2"]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fixture(root, "agent-launch-1", "forms-app", 101)
            fixture(root, "agent-launch-2", "editor-app", 102)
            clients = [client(101, "0xa", 11), client(102, "0xb", 12)]
            agents = {f"cua-bench-{task.id}-1": 11, f"cua-bench-{task.id}-2": 12}
            result = verify(task, root, clients, read_starttime=lambda _pid: 10, agent_workspaces=agents)
            self.assertEqual([row["workspace"] for row in result["parallel_frames"]], [11, 12])
            agents[f"cua-bench-{task.id}-2"] = 11
            result = verify(task, root, clients, read_starttime=lambda _pid: 10, agent_workspaces=agents)
            self.assertEqual(len(result["parallel_frames"]), 1)

    def test_cleanup_terminates_every_owned_agent_launch_fixture(self):
        task = TASKS["t6-03-launch-10"]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for number in range(10): fixture(root, f"agent-launch-{number + 1}", "forms-app", 200 + number)
            terminated = []
            result = cleanup(task, root, read_starttime=lambda _pid: 10,
                             terminate=lambda pid, sig: terminated.append((pid, sig)))
            self.assertEqual(result, list(range(200, 210)))
            self.assertEqual([pid for pid, _sig in terminated], result)

    def test_cleanup_rejects_stale_or_mismatched_fixture_identity(self):
        task = TASKS["t6-05-parallel-2"]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fixture(root, "agent-launch-1", "forms-app", 101)
            fixture(root, "agent-launch-2", "editor-app", 102)
            state_path = root / "agent-launch-2" / "editor-app.json"
            state = json.loads(state_path.read_text()); state["app"] = "forms-app"
            state_path.write_text(json.dumps(state))
            terminated = []
            result = cleanup(task, root, read_starttime=lambda pid: 11 if pid == 101 else 10,
                             terminate=lambda pid, sig: terminated.append((pid, sig)))
            self.assertEqual(result, [])
            self.assertEqual(terminated, [])


if __name__ == "__main__":
    unittest.main()
