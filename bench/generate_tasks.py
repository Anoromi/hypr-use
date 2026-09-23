#!/usr/bin/env python3
from pathlib import Path
from dataclasses import replace

from cua_bench.catalog import Task, dump_tasks


def click(app: str, label: str) -> dict:
    return {"tool": "click", "app": app, "target": {"name": label}}


def setv(app: str, label: str, value: str) -> dict:
    return {"tool": "set_value", "app": app, "target": {"name": label}, "value": value}


def key(app: str, value: str) -> dict:
    return {"tool": "press_key", "app": app, "key": value}


def dialog_click(app: str, title: str, label: str) -> list[dict]:
    return [{"tool": "get_dialog", "app": app, "title": title}, {"tool": "dialog_click", "app": app, "target": {"name": label}}]


def country(value: str) -> list[dict]:
    initial = "Germany" if value == "Japan" else "Japan"
    return [{"tool": "select_options", "app": "forms-app", "choices": [{"name": initial, "option": value}]}]


def checks(**values) -> dict:
    return {"checks": [{"path": k, "value": v, "name": k} for k, v in values.items()]}


tasks: list[Task] = []

# T1: every task is one or two visible operations.
t1 = [
    ("button", "Click Complete.", [click("forms-app", "Complete")], checks(completed=True)),
    ("type", "Enter Akira in Name.", [setv("forms-app", "Name", "Akira")], checks(**{"fields.name": "Akira"})),
    ("submit", "Enter ready in Quick entry and submit that field with Enter.", [setv("forms-app", "Quick entry", "ready"), key("forms-app", "ENTER")], {"checks": [{"path": "quick_entry", "value": "ready"}, {"path": "events", "op": "contains", "value": "quick-submit"}]}),
    ("read", "Report the reference value shown in the window.", [{"tool": "get_app_state", "app": "forms-app"}], {"checks": [{"path": "$oracle_transcript", "op": "contains", "value": "REF-731", "name": "observed reference"}]}),
    ("dialog-close", "Close the open notice dialog.", [{"tool": "get_dialog", "app": "dialog-storm", "title": "Notice"}, {"tool": "dialog_click", "app": "dialog-storm", "target": {"name": "Close notice"}}], checks(notice_closed=True)),
    ("dialog-confirm", "Confirm the open approval dialog.", [click("dialog-storm", "Approve")], checks(approved=True)),
    ("editor-type", "Type lunar into the editor.", [setv("editor-app", "Document", "lunar")], checks(content="lunar")),
    ("editor-save", "Save the open document.", [click("editor-app", "Save")], checks(saved=True)),
    ("list-select", "Select Item 7.", [click("list-app", "Item 7")], checks(selected="Item 7")),
    ("list-filter", "Enter north in Filter.", [setv("list-app", "Filter", "north")], checks(filter="north")),
    ("check", "Enable Newsletter.", [click("forms-app", "Newsletter")], checks(**{"fields.newsletter": True})),
    ("dropdown", "Choose Japan in Country.", country("Japan"), checks(**{"fields.country": "Japan"})),
    ("next", "Go to the next form page.", [click("forms-app", "Next")], checks(page=2)),
    ("window", "Click Mark done in the Notes window.", [click("multi-window-app", "Mark done")], checks(notes_done=True)),
    ("launch", "Launch the forms benchmark app.", [{"tool": "get_app_state", "app": "forms-app"}], checks(launched=True)),
]
for i, (name, prompt, oracle, grader) in enumerate(t1, 1):
    tasks.append(Task(f"t1-{i:02d}-{name}", "T1", oracle[0].get("app", "forms-app"), f"t1-{i:02d}-{name}", prompt, 3, .03, grader, oracle, tags=("ax",)))

# T2: compact single-window workflows.
for i in range(1, 21):
    kind = (i - 1) % 5
    seed = f"t2-{i:02d}"
    if kind == 0:
        app, prompt = "forms-app", f"Set Name to User {i}, Email to user{i}@example.test, then save."
        oracle = [setv(app, "Name", f"User {i}"), setv(app, "Email", f"user{i}@example.test"), click(app, "Save draft")]
        grader = checks(**{"fields.name": f"User {i}", "fields.email": f"user{i}@example.test", "draft_saved": True})
    elif kind == 1:
        app, prompt = "forms-app", "Select Germany, enable Newsletter and Archive, then save."
        oracle = [*country("Germany"), click(app, "Newsletter"), click(app, "Archive"), click(app, "Save draft")]
        grader = checks(**{"fields.country": "Germany", "fields.newsletter": True, "fields.archive": True, "draft_saved": True})
    elif kind == 2:
        app, prompt = "list-app", f"Enter the exact filter text 'Item {i}', select Item {i}, and report its Amount as 'Amount N'."
        oracle = [setv(app, "Filter", f"Item {i}"), click(app, f"Item {i}"), {"tool": "get_app_state", "app": app}]
        grader = {"checks": [*checks(filter=f"Item {i}", selected=f"Item {i}")["checks"], {"path": "$oracle_transcript", "op": "regex", "value": rf"Amount\D+{i * 17}\b", "name": "observed amount"}]}
    elif kind == 3:
        app, prompt = "editor-app", f"Replace the document with note {i} and save it."
        oracle = [setv(app, "Document", f"note {i}"), click(app, "Save")]
        grader = checks(content=f"note {i}", saved_content=f"note {i}", saved=True)
    else:
        app, prompt = "forms-app", f"Set the due date to 2026-10-{i:02d} and save a draft."
        oracle = [setv(app, "Due date", f"2026-10-{i:02d}"), click(app, "Save draft")]
        grader = checks(**{"fields.due_date": f"2026-10-{i:02d}", "draft_saved": True})
    tasks.append(Task(seed, "T2", app, seed, prompt, 8, .08, grader, oracle, tags=("single-window",)))

# T3: validation, sort, replace, confirmation, and same-process windows.
for i in range(1, 21):
    kind = (i - 1) % 5; seed = f"t3-{i:02d}"
    if kind == 0:
        app, prompt = "forms-app", f"Submit Name Person {i}, Email person{i}@example.test, and Due date 2026-12-01. Advance the form, fix any visible validation error, and confirm submission."
        oracle = [setv(app, "Name", f"Person {i}"), setv(app, "Email", f"person{i}@example.test"), click(app, "Next"), setv(app, "Due date", "2026-12-01"), click(app, "Submit"), *dialog_click(app, "Confirm submission", "Confirm")]
        grader = checks(submitted=True, confirmed=True, **{"submission.name": f"Person {i}", "submission.email": f"person{i}@example.test", "submission.due_date": "2026-12-01"})
    elif kind == 1:
        app, prompt = "list-app", "Sort Amount descending and record the top three rows."
        oracle = [click(app, "Amount"), click(app, "Amount"), click(app, "Record top three")]
        grader = checks(sort="amount-desc", top_recorded=True, top_three=[999, 998, 997])
    elif kind == 2:
        app, prompt = "editor-app", f"Replace every alpha with omega-{i}, then save."
        oracle = [setv(app, "Find", "alpha"), setv(app, "Replace", f"omega-{i}"), click(app, "Replace all"), click(app, "Save")]
        grader = checks(find="alpha", replace=f"omega-{i}", replaced=True, saved=True, saved_content=f"omega-{i} beta omega-{i}")
    elif kind == 3:
        app, prompt = "dialog-storm", "Open the destructive action, choose Continue, then confirm the nested dialog."
        oracle = [click(app, "Destructive action"), *dialog_click(app, "Continue?", "Continue"), *dialog_click(app, "Final confirmation", "Confirm")]
        grader = checks(nested_confirmed=True)
    else:
        app, prompt = "multi-window-app", "Copy the code shown in the Reference window into the Notes window and save."
        oracle = [{"tool": "copy_value", "from_app": app, "from_window": "Reference", "to_app": app, "pattern": rf"Reference code: (CODE-{i:02d})", "target": {"name": "Notes"}}, click(app, "Save notes")]
        grader = checks(notes=f"CODE-{i:02d}", notes_saved=True)
    tasks.append(Task(seed, "T3", app, seed, prompt, 14, .15, grader, oracle, tags=("state", "verification")))

# T4: cross-app work, delayed dialogs, distractors, rebinding, scrolling and drag.
for i in range(1, 16):
    kind = (i - 1) % 5; seed = f"t4-{i:02d}"
    if kind == 0:
        prompt = f"Read Item {i}'s Amount in list-app, enter it as the form Reference, and submit."
        oracle = [{"tool": "copy_value", "from_app": "list-app", "to_app": "forms-app", "pattern": f"Amount {i * 17}\\b", "value_pattern": f"({i * 17})", "target": {"name": "Reference"}}, click("forms-app", "Submit"), *dialog_click("forms-app", "Confirm submission", "Confirm")]
        grader = checks(reference=str(i * 17), **{"submission.reference": str(i * 17)}, submitted=True); app = "forms-app"
    elif kind == 1:
        prompt = f"Set the editor document to delay {i}. Handle the delayed approval dialog through the related-dialog API, then save."
        oracle = [setv("editor-app", "Document", f"delay {i}"), {"tool": "get_dialog", "app": "dialog-storm", "title": "Delayed approval", "wait_ms": 6000}, {"tool": "dialog_click", "app": "dialog-storm", "target": {"name": "Approve"}}, click("editor-app", "Save")]
        grader = checks(**{"apps.dialog-storm.delay_approved": True, "saved_content": f"delay {i}"}); app = "editor-app"
    elif kind == 2:
        prompt = "Use the window titled Target, ignore the identical distractor, and mark the target complete."
        oracle = [{"tool": "get_app_state", "app": "multi-window-app", "window": "Target"}, {**click("multi-window-app", "Mark target complete"), "window": "Target"}]
        grader = checks(target_complete=True, distractor_untouched=True); app = "multi-window-app"
    elif kind == 3:
        prompt = "After the target window restarts, re-observe it and enter rebound in its field."
        oracle = [click("multi-window-app", "Restart target"), {"tool": "get_app_state", "app": "multi-window-app"}, setv("multi-window-app", "Rebound value", "rebound")]
        grader = {"checks": [*checks(rebound="rebound")["checks"], {"path": "events", "op": "contains", "value": "restart", "name": "target restarted"}]}; app = "multi-window-app"
    else:
        prompt = f"Scroll to Item {900+i}, select it, and drag it before Item {899+i}."
        oracle = [{"tool": "scroll", "app": "list-app", "target": {"name": "Rows"}, "direction": "down", "pages": 20}, click("list-app", f"Item {900+i}"), {"tool": "drag", "app": "list-app", "from": {"name": f"Item {900+i}"}, "to": {"name": f"Item {899+i}"}}]
        grader = checks(selected=f"Item {900+i}", reordered=True); app = "list-app"
    tasks.append(Task(seed, "T4", app, seed, prompt, 24, .28, grader, oracle, distractors=("sentinel",), tags=("recovery",)))

# T5: long, ambiguous and adversarial scenarios. Checkpoints produce partial credit.
for i in range(1, 11):
    kind = (i - 1) % 5; seed = f"t5-{i:02d}"
    common = [setv("forms-app", "Name", f"Expedition {i}"), setv("forms-app", "Email", f"expedition{i}@example.test"), click("forms-app", "Next")]
    if kind == 0:
        note = f"checkpoint {i} verified"
        prompt = f"Complete the cross-app expedition {i}: inspect Item {i}, then select Item 2 and use its displayed Amount as the form Reference. Set Name to Expedition {i}, Email to expedition{i}@example.test, Quick entry to verified, enable Newsletter and Archive, and choose Germany. Save the editor note '{note}'. Save the form draft, submit, and confirm."
        oracle = [setv("list-app", "Filter", f"Item {i}"), click("list-app", f"Item {i}"), {"tool": "get_app_state", "app": "list-app"}, setv("list-app", "Filter", "Item 2"), click("list-app", "Item 2"), {"tool": "get_app_state", "app": "list-app"}, *common, setv("forms-app", "Quick entry", "verified"), key("forms-app", "ENTER"), click("forms-app", "Newsletter"), click("forms-app", "Archive"), *country("Germany"), setv("editor-app", "Document", f"draft {i}"), setv("editor-app", "Find", "draft"), setv("editor-app", "Replace", "checkpoint"), click("editor-app", "Replace all"), setv("editor-app", "Document", note), click("editor-app", "Save"), {"tool": "get_app_state", "app": "editor-app"}, {"tool": "copy_value", "from_app": "list-app", "to_app": "forms-app", "pattern": "Amount 34\\b", "value_pattern": "(34)", "target": {"name": "Reference"}}, click("forms-app", "Save draft"), {"tool": "get_app_state", "app": "forms-app"}, click("forms-app", "Submit"), *dialog_click("forms-app", "Confirm submission", "Confirm")]
        grader = checks(**{"apps.editor-app.saved_content": note, "apps.list-app.selected": "Item 2", "submission.reference": "34", "submission.name": f"Expedition {i}", "submission.email": f"expedition{i}@example.test", "submission.quick_entry": "verified", "submission.newsletter": True, "submission.archive": True, "submission.country": "Germany", "draft_saved": True, "submitted": True, "confirmed": True}); app = "forms-app"
    elif kind == 1:
        prompt = f"Use a screenshot to find the unlabeled visual field, enter visual-{i}, then submit and confirm."
        oracle = [{"tool": "get_app_state", "app": "forms-app"}, {"tool": "click", "app": "forms-app", "x": 310, "y": 180}, {"tool": "type_text", "app": "forms-app", "text": f"visual-{i}"}, click("forms-app", "Submit"), *dialog_click("forms-app", "Confirm submission", "Confirm")]
        grader = checks(visual_value=f"visual-{i}", submitted=True, confirmed=True); app = "forms-app"
    elif kind == 2:
        prompt = "Use tooltips to choose the export action for the archive, then confirm."
        oracle = [{"tool": "get_app_state", "app": "forms-app"}, {"tool": "click", "app": "forms-app", "x": 460, "y": 420}, *dialog_click("forms-app", "Confirm submission", "Confirm")]
        grader = checks(exported=True, confirmed=True); app = "forms-app"
    elif kind == 3:
        prompt = "Recover from the pre-opened wrong dialog, then open and confirm the correct dialog."
        oracle = [*dialog_click("dialog-storm", "Wrong dialog", "Cancel"), click("dialog-storm", "Correct action"), *dialog_click("dialog-storm", "Correct dialog", "Confirm")]
        grader = checks(wrong_cancelled=True, correct_confirmed=True); app = "dialog-storm"
    else:
        prompt = "The accessibility snapshot is stale. Use a current screenshot and approve before the dialog closes."
        oracle = [{"tool": "get_app_state", "app": "dialog-storm", "fresh": True}, {"tool": "click", "app": "dialog-storm", "x": 380, "y": 260}]
        grader = checks(timed_approved=True); app = "dialog-storm"
    tasks.append(Task(seed, "T5", app, seed, prompt, 40, .50, grader, oracle, distractors=("sentinel",), tags=("long-horizon", "partial-credit")))

# T6 is tool-only. The runner expands repeat counts and enforces thresholds.
t6_specs = [
    ("rapid-200", "200 rapid actions without loss", {"kind": "rapid", "count": 200}),
    ("ax-1000", "Extract all 1,000 AX rows and confirm Item 1000", {"kind": "latency", "tool": "get_app_state", "limit_ms": 2000}),
    ("launch-10", "Ten launches bind to the right frames", {"kind": "launch", "count": 10}),
    ("restart", "Resume after an MCP restart", {"kind": "restart"}),
    ("parallel-2", "Two frame sets do not interfere", {"kind": "parallel", "count": 2}),
    ("unicode", "Unicode text entry round trips", {"kind": "text", "value": "東京 café 👋"}),
    ("newlines", "Multiline entry preserves newlines", {"kind": "text", "value": "one\ntwo\nthree"}),
    ("click-index", "Index clicks hit the intended element", {"kind": "click", "mode": "index"}),
    ("click-pixel", "Pixel clicks hit the intended element", {"kind": "click", "mode": "pixel"}),
    ("tracking", "A moving target remains bound", {"kind": "tracking", "count": 25}),
]
for i, (name, prompt, spec) in enumerate(t6_specs, 1):
    tasks.append(Task(f"t6-{i:02d}-{name}", "T6", "stress-app", f"t6-{i:02d}-{name}", prompt, spec.get("count", 20) + 5, 0, {"checks": [{"path": "tool_passed", "value": True}]}, [{"tool_benchmark": spec}], tags=("tool-only",)))

configured = []
for task in tasks:
    apps = tuple(dict.fromkeys(value for action in task.oracle for value in ([action["app"]] if "app" in action else [action[k] for k in ("from_app", "to_app") if k in action])))
    if task.tier == "T6": apps = ("list-app",) if task.oracle[0]["tool_benchmark"]["kind"] == "latency" else (("editor-app",) if "Multiline" in task.prompt else (("forms-app", "editor-app") if "frame sets" in task.prompt else ("forms-app",)))
    configured.append(replace(task, setup_apps=apps or (task.app,)))
tasks = configured
assert {tier: sum(t.tier == tier for t in tasks) for tier in {t.tier for t in tasks}} == {"T1": 15, "T2": 20, "T3": 20, "T4": 15, "T5": 10, "T6": 10}
dump_tasks(tasks, Path(__file__).with_name("tasks.json"))
