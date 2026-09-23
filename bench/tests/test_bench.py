import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cua_bench.catalog import load_tasks, select
from cua_bench.grading import grade
from cua_bench.report import render
from cua_bench.instructions import agent_prompt
from apps.fixture_state import complete_target_window, initialize_target_pair, submit_quick_entry
from cua_bench.codex_driver import token_auth
from cua_bench.toolbench import client_overrides, parallel_isolated


class CatalogTests(unittest.TestCase):
    def test_tier_counts_and_unique_ids(self):
        tasks = load_tasks(); counts = {tier: sum(t.tier == tier for t in tasks) for tier in {t.tier for t in tasks}}
        self.assertEqual(counts, {"T1": 15, "T2": 20, "T3": 20, "T4": 15, "T5": 10, "T6": 10})
        self.assertEqual(len({t.id for t in tasks}), 90)

    def test_every_task_is_bounded_and_gradable(self):
        for task in load_tasks():
            self.assertGreater(task.max_steps, 0, task.id); self.assertTrue(task.prompt, task.id); self.assertTrue(task.grader["checks"], task.id); self.assertTrue(task.oracle, task.id)
            if task.tier != "T6": self.assertGreater(task.budget_usd, 0, task.id)

    def test_every_grader_rejects_a_mutated_outcome(self):
        for task in load_tasks():
            state = {}; transcript = []
            for check in task.grader["checks"]:
                if check["path"] in {"$transcript", "$oracle_transcript"}:
                    transcript = [{"type": "result", "result": check["value"]}]; continue
                target = state
                parts = check["path"].split(".")
                for part in parts[:-1]: target = target.setdefault(part, {})
                target[parts[-1]] = check.get("value", True)
            self.assertTrue(grade(task.grader, state, transcript).passed, task.id)
            first = task.grader["checks"][0]
            if first["path"] in {"$transcript", "$oracle_transcript"}: transcript = [{"type": "result", "result": "wrong"}]
            else:
                target = state; parts = first["path"].split(".")
                for part in parts[:-1]: target = target[part]
                target[parts[-1]] = object()
            self.assertFalse(grade(task.grader, state, transcript).passed, task.id)

    def test_select(self):
        self.assertEqual(len(select(load_tasks(), {"T5"}, None)), 10)

    def test_long_horizon_cross_app_tasks_have_25_steps(self):
        tasks = [task for task in load_tasks() if task.tier == "T5" and "cross-app expedition" in task.prompt]
        self.assertTrue(tasks); self.assertTrue(all(task.oracle_steps >= 25 for task in tasks))


class GradingTests(unittest.TestCase):
    def test_partial_credit_and_failure(self):
        result = grade({"checks": [{"path": "a", "value": 1}, {"path": "nested.b", "value": 2}]}, {"a": 1, "nested": {"b": 0}}, [{}])
        self.assertFalse(result.passed); self.assertEqual(result.score, .5); self.assertEqual(result.failure_class, "wrong_action")

    def test_guardrail_failure_wins(self):
        result = grade({"checks": [{"path": "done", "value": True}]}, {}, [{"guardrail_violation": "hyprctl"}])
        self.assertEqual(result.failure_class, "violated_guardrail")

    def test_guardrail_overrides_complete_state(self):
        result = grade({"checks": [{"path": "done", "value": True}]}, {"done": True}, [{"guardrail_violation": "hyprctl"}])
        self.assertFalse(result.passed); self.assertEqual(result.failure_class, "violated_guardrail")

    def test_prompt_or_tool_text_cannot_satisfy_report(self):
        spec = {"checks": [{"path": "$transcript", "op": "contains", "value": "REF-731"}]}
        self.assertFalse(grade(spec, {}, [{"type": "tool_result", "text": "REF-731"}]).passed)

    def test_oracle_observation_is_explicit(self):
        spec = {"checks": [{"path": "$oracle_transcript", "op": "contains", "value": "REF-731"}]}
        event = {"request": {"tool": "get_app_state"}, "result": "REF-731"}
        self.assertTrue(grade(spec, {}, [event]).passed)


class ReportTests(unittest.TestCase):
    def test_nested_results_render(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); task = root / "run-1" / "task"; task.mkdir(parents=True)
            (task / "result.json").write_text(json.dumps({"id": "task", "mode": "scripted", "baseline_kind": "scripted_baseline", "tier": "T1", "passed": True, "steps": 3}))
            page = render(root, root / "report")
            self.assertIn("1/1 completed", page.read_text())
            page = render(root, root / "report")
            self.assertEqual(len(json.loads((root / "report/results.json").read_text())), 1)

    def test_list_baseline_and_portable_recording(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); task = root / "task"; task.mkdir(); recording = root / "clip.mp4"; recording.write_bytes(b"video")
            row = {"id": "task", "mode": "scripted", "baseline_kind": "scripted_baseline", "tier": "T1", "passed": True, "steps": 2, "recording": str(recording)}
            (task / "result.json").write_text(json.dumps(row)); (root / "baseline.json").write_text(json.dumps([row]))
            page = render(root, root / "report")
            self.assertIn("media/scripted/task.mp4", page.read_text()); self.assertTrue((root / "report/media/scripted/task.mp4").exists())

    def test_paired_modes_remain_separate_with_distinct_videos(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for mode, passed, steps in (("scripted", True, 2), ("agentic", False, 7)):
                task = root / mode / "task"; task.mkdir(parents=True); (task / "desktop.mp4").write_bytes(mode.encode())
                row = {"id": "task", "mode": mode, "baseline_kind": "model_score" if mode == "agentic" else "scripted_baseline", "tier": "T1", "passed": passed, "steps": steps, "tool_calls": 99, "input_tokens": 999}
                (task / "result.json").write_text(json.dumps(row))
            page = render(root, root / "report").read_text()
            self.assertIn("Scripted baseline", page); self.assertIn("Agentic (Codex)", page)
            self.assertIn("2 steps", page); self.assertIn("7 steps", page)
            self.assertNotIn("99 calls", page); self.assertNotIn("999 tokens", page)
            self.assertIn("media/scripted/scripted-task.mp4", page); self.assertIn("media/agentic/agentic-task.mp4", page)
            self.assertNotIn("Baseline delta", page)

    def test_legacy_result_is_unclassified(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); task = root / "task"; task.mkdir()
            (task / "result.json").write_text(json.dumps({"id": "task", "score": 1}))
            page = render(root, root / "report")
            self.assertIn("Unclassified legacy", page.read_text())

    def test_same_mode_baseline_delta_does_not_mutate_group_count(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); task = root / "scripted" / "task"; task.mkdir(parents=True)
            row = {"id": "task", "mode": "scripted", "tier": "T1", "steps": 1, "passed": True}
            (task / "result.json").write_text(json.dumps(row))
            baseline = root / "old.json"; baseline.write_text(json.dumps([{**row, "passed": False}]))
            self.assertIn("Same-mode completion delta: +100.0%", render(root, root / "report", baseline).read_text())

    def test_phase_and_t6_evidence_are_portable(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); task = root / "agentic" / "run-1" / "t6-01"; task.mkdir(parents=True)
            row = {"id": "t6-01", "mode": "agentic", "tier": "T6", "steps": 4, "passed": True}
            (task / "result.json").write_text(json.dumps(row))
            for name in ("t6-evidence.json", "wire-setup.jsonl", "wire-action.jsonl", "prompt.txt", "final.txt", "final-grade.txt"):
                (task / name).write_text(name)
            report = root / "report"; page = render(root, report).read_text()
            for name in ("t6-evidence.json", "wire-setup.jsonl", "wire-action.jsonl", "prompt.txt", "final.txt", "final-grade.txt"):
                self.assertIn(name, page)
                self.assertTrue((report / "evidence" / "agentic" / "agentic-run-1-t6-01" / name).is_file())


class InstructionTests(unittest.TestCase):
    def test_long_tasks_grade_every_requested_persisted_checkpoint(self):
        tasks = load_tasks()
        for task in (task for task in tasks if task.tier == "T5" and "cross-app expedition" in task.prompt):
            paths = {check["path"] for check in task.grader["checks"]}
            self.assertTrue({"submission.quick_entry", "submission.newsletter", "submission.archive", "submission.country", "draft_saved"} <= paths)
        for task in (task for task in tasks if task.tier == "T5" and "unlabeled visual field" in task.prompt):
            self.assertIn("confirmed", {check["path"] for check in task.grader["checks"]})
        for task in (task for task in tasks if task.tier == "T4" and "restarts" in task.prompt):
            self.assertIn("events", {check["path"] for check in task.grader["checks"]})

    def test_ax1000_uses_complete_large_tree_observation_without_speed_score(self):
        task = next(task for task in load_tasks() if task.id == "t6-02-ax-1000")
        prompt = agent_prompt(task)
        self.assertIn("maxRecords:8000", prompt); self.assertIn("timeBudgetMs:30000", prompt)
        self.assertIn("completeness task", prompt); self.assertNotIn("within 2000", prompt)

    def test_agent_instructions_document_binding_waits_and_supported_surface(self):
        prompt = agent_prompt(load_tasks()[0])
        for text in ("title ends with [t1-01-button]", "same-process secondary windows", "getDialog", "30000 ms", "waitFor", "setTimeout", "choices:[{name,option", "fields:[{name,value"):
            self.assertIn(text, prompt)
        self.assertNotIn("Stop after", prompt)

    def test_t4_delayed_dialog_prompts_include_required_editor_value(self):
        tasks = [task for task in load_tasks() if task.tier == "T4" and "delayed approval" in task.prompt]
        self.assertEqual(len(tasks), 3)
        for task in tasks:
            expected = next(check["value"] for check in task.grader["checks"] if check["path"] == "saved_content")
            self.assertIn(expected, task.prompt)

    def test_observation_answers_are_not_leaked_by_prompts(self):
        for task in load_tasks():
            if task.tier == "T3" and task.app == "multi-window-app":
                expected = next(check["value"] for check in task.grader["checks"] if check["path"] == "notes")
                self.assertNotIn(expected, task.prompt)


class FixtureStateTests(unittest.TestCase):
    def test_sensitive_fixture_outcomes_require_their_real_actions(self):
        source = (Path(__file__).parents[1] / "apps" / "bench_app.py").read_text()
        approve_line = next(line for line in source.splitlines() if 'button("Approve"' in line)
        self.assertIn('__setitem__("approved", True)', approve_line)
        self.assertNotIn("delay_approved", approve_line); self.assertNotIn("timed_approved", approve_line)
        self.assertIn("win.close()", source); self.assertIn("multi(replacement, application, include_reference=False)", source)
        self.assertIn('initial_country = "Germany" if SEED.startswith("t1-12-")', source)

    def test_success_callbacks_publish_visible_status(self):
        source = (Path(__file__).parents[1] / "apps" / "bench_app.py").read_text()
        for text in (
            'action_status.set_label("Page 2")', 'action_status.set_label("Draft saved")',
            'action_status.set_label("Submission confirmed")', 'saved_status.set_label("Document saved")',
            'top_status.set_label("Top three recorded: 999, 998, 997")',
            'notes_status.set_label("Notes marked done")', 'notes_status.set_label("Notes saved")',
        ):
            self.assertIn(text, source)

    def test_quick_entry_submission_has_state_and_visible_confirmation(self):
        state = {}
        self.assertEqual(submit_quick_entry(state, "ready"), "Quick entry submitted: ready")
        self.assertEqual(state, {"quick_entry": "ready", "quick_entry_submitted": True})
        source = (Path(__file__).parents[1] / "apps" / "bench_app.py").read_text()
        self.assertIn('quick_status.set_label(submit_quick_entry', source)
        self.assertIn('save("quick-submit")', source)

    def test_target_and_distractor_have_independent_state(self):
        state = {}; initialize_target_pair(state)
        self.assertEqual(state, {"target_complete": False, "distractor_complete": False, "distractor_untouched": True})
        complete_target_window(state, "target")
        self.assertTrue(state["target_complete"]); self.assertTrue(state["distractor_untouched"]); self.assertFalse(state["distractor_complete"])
        complete_target_window(state, "distractor")
        self.assertTrue(state["distractor_complete"]); self.assertFalse(state["distractor_untouched"])

    def test_target_pair_fixture_is_used_only_by_intended_t4_seeds(self):
        source = (Path(__file__).parents[1] / "apps" / "bench_app.py").read_text()
        self.assertIn('number % 5 == 3', source)
        self.assertIn('win.set_title(f"Target [{SEED}]")', source)
        self.assertIn('title=f"Distractor [{SEED}]"', source)

    def test_standalone_fixture_resolves_sibling_helper_from_arbitrary_cwd(self):
        apps = Path(__file__).parents[1] / "apps"
        with tempfile.NamedTemporaryFile("w", suffix=".py", dir=apps, delete=False) as handle:
            handle.write("from fixture_state import initialize_target_pair\ns = {}\ninitialize_target_pair(s)\nassert s['distractor_untouched'] is True\n")
            probe = Path(handle.name)
        try:
            with tempfile.TemporaryDirectory() as cwd:
                result = subprocess.run([sys.executable, str(probe)], cwd=cwd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            probe.unlink(missing_ok=True)


class CodexDriverTests(unittest.TestCase):
    def test_requires_token_only_auth(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); (root / "auth.json").write_text(json.dumps({"OPENAI_API_KEY": "sk-test"}))
            with self.assertRaises(RuntimeError): token_auth(str(root))
            (root / "auth.json").write_text(json.dumps({"tokens": {"access_token": "opaque"}}))
            self.assertEqual(token_auth(str(root)), root / "auth.json")


class ToolbenchTests(unittest.TestCase):
    def test_workspace_benchmarks_enable_registry_with_unique_agents(self):
        self.assertEqual(client_overrides("rapid"), {})
        launch = client_overrides("launch")
        first = client_overrides("parallel", "forms-app")
        second = client_overrides("parallel", "editor-app")
        self.assertEqual(launch["HYPR_USE_NO_HYPRNAV"], "0")
        self.assertEqual(first["HYPR_USE_NO_HYPRNAV"], "0")
        self.assertNotEqual(first["HYPR_USE_AGENT_ID"], second["HYPR_USE_AGENT_ID"])

    def test_parallel_requires_owned_rows_in_distinct_workspaces(self):
        missing = [{"workspace": 1, "ids": ["a", "b"]}, {"workspace": 2, "ids": ["a", "b"]}]
        self.assertFalse(parallel_isolated(missing, 2))
        valid = [
            {"workspace": 1, "ownRows": [{"id": "a", "workspace": 1, "mine": True}]},
            {"workspace": 2, "ownRows": [{"id": "b", "workspace": 2, "mine": True}]},
        ]
        self.assertTrue(parallel_isolated(valid, 2))


if __name__ == "__main__": unittest.main()
