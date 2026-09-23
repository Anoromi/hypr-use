#!/usr/bin/env python3
"""GTK 4 benchmark fixtures. Each interaction writes a machine-readable state file."""
from __future__ import annotations

import json
import os
import signal
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk
from fixture_state import complete_target_window, initialize_target_pair, submit_quick_entry

APP = sys.argv[1] if len(sys.argv) > 1 else "forms-app"
SEED = os.environ.get("HYPR_LAB_SEED", os.environ.get("CUA_BENCH_SEED", "manual"))
STATE_DIR = Path(os.environ.get("BENCH_STATE_DIR", "/tmp/cua-bench-state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_PATH = STATE_DIR / f"{APP}.json"
def process_starttime() -> int:
    return int(Path(f"/proc/{os.getpid()}/stat").read_text().split()[21])


state: dict = {"app": APP, "seed": SEED, "launched": True, "observed": True, "events": [], "pid": os.getpid(), "starttime": process_starttime()}


def save(event: str | None = None) -> None:
    if event:
        state["events"].append(event)
    temp = STATE_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(state, sort_keys=True) + "\n")
    temp.replace(STATE_PATH)


def named(widget: Gtk.Widget, name: str, tooltip: str | None = None) -> Gtk.Widget:
    widget.update_property([Gtk.AccessibleProperty.LABEL], [name])
    if tooltip:
        widget.set_tooltip_text(tooltip)
    return widget


def button(label: str, callback, tooltip: str | None = None) -> Gtk.Button:
    widget = Gtk.Button(label=label)
    named(widget, label, tooltip)
    widget.connect("clicked", callback)
    return widget


def entry(label: str, key: str, parent: Gtk.Box) -> Gtk.Entry:
    parent.append(Gtk.Label(label=label, xalign=0))
    widget = Gtk.Entry()
    named(widget, label)
    widget.connect("changed", lambda w: (state.setdefault("fields", {}).__setitem__(key, w.get_text()), state.__setitem__(key, w.get_text()), save(f"set:{key}")))
    parent.append(widget)
    return widget


def dialog(parent: Gtk.Window, title: str, actions: list[tuple[str, callable]]) -> None:
    win = Gtk.Window(title=title, transient_for=parent, modal=True, default_width=380, default_height=170)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
    box.append(Gtk.Label(label=title))
    row = Gtk.Box(spacing=8, halign=Gtk.Align.END)
    for label, callback in actions:
        row.append(button(label, lambda _w, cb=callback, target=win: (cb(), target.close())))
    box.append(row); win.set_child(box); win.present()


def forms(win: Gtk.Window) -> None:
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=24, margin_bottom=24, margin_start=30, margin_end=30)
    initial_country = "Germany" if SEED.startswith("t1-12-") else "Japan"
    root.append(Gtk.Label(label="Application form", xalign=0)); root.append(Gtk.Label(label="Reference value: REF-731", xalign=0)); state["fields"] = {"country": initial_country, "newsletter": False, "archive": False}
    quick_status = named(Gtk.Label(label="Quick entry not submitted", xalign=0), "Quick entry status")
    for label, key in (("Name", "name"), ("Email", "email"), ("Quick entry", "quick_entry"), ("Reference", "reference"), ("Due date", "due_date")):
        w = entry(label, key, root)
        if key == "name" and SEED.startswith("t6-"): GLib.idle_add(lambda target=w: (target.grab_focus(), False)[1])
        if key == "quick_entry": w.connect("activate", lambda x: (quick_status.set_label(submit_quick_entry(state, x.get_text())), save("quick-submit")))
    root.append(quick_status)
    calendar = Gtk.Calendar(); named(calendar, "Due date picker")
    calendar.connect("day-selected", lambda w: (state["fields"].__setitem__("calendar_date", w.get_date().format("%Y-%m-%d")), save("calendar"))); root.append(calendar)
    country = Gtk.DropDown.new_from_strings(["Japan", "Germany", "United States"]); named(country, "Country")
    country.set_selected(1 if initial_country == "Germany" else 0)
    country.connect("notify::selected", lambda w, _p: (state["fields"].__setitem__("country", ["Japan", "Germany", "United States"][w.get_selected()]), save("country"))); root.append(country)
    for label, key in (("Newsletter", "newsletter"), ("Archive", "archive")):
        check = Gtk.ToggleButton(label=label); named(check, label); check.connect("toggled", lambda w, k=key: (state["fields"].__setitem__(k, w.get_active()), save(k))); root.append(check)
    visual = Gtk.Entry(); visual.connect("changed", lambda w: (state.__setitem__("visual_value", w.get_text()), save("visual"))); root.append(visual)
    actions = Gtk.Box(spacing=8)
    status = named(Gtk.Label(label="Pending"), "Status")
    action_status = named(Gtk.Label(label="No form action completed", xalign=0), "Form action status")
    complete = button("Complete", lambda _w: (state.__setitem__("completed", True), state.__setitem__("click_count", state.get("click_count", 0) + 1), status.set_label(f"Completed {state['click_count']}"), save("complete")))
    actions.append(complete)
    if "tracking" in SEED:
        def move_target():
            state["motion_ticks"] = state.get("motion_ticks", 0) + 1; complete.set_margin_start((state["motion_ticks"] % 8) * 12); save("move"); return True
        GLib.timeout_add(120, move_target)
    actions.append(button("Next", lambda _w: (state.__setitem__("page", 2), action_status.set_label("Page 2"), save("next"))))
    actions.append(button("Save draft", lambda _w: (state.__setitem__("draft_saved", True), action_status.set_label("Draft saved"), save("draft"))))
    def submit(_w):
        state["submitted"] = True; state["submission"] = dict(state["fields"]); action_status.set_label("Submitted; confirmation required"); save("submit")
        dialog(win, "Confirm submission", [("Cancel", lambda: (action_status.set_label("Submission confirmation cancelled"), save("cancel"))), ("Confirm", lambda: (state.__setitem__("confirmed", True), action_status.set_label("Submission confirmed"), save("confirm")))])
    actions.append(button("Submit", submit))
    actions.append(button("Export", lambda _w: (state.__setitem__("exported", True), submit(_w)), "Export archive"))
    root.append(actions); root.append(status); root.append(action_status); win.set_child(root)


def editor(win: Gtk.Window) -> None:
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=20, margin_bottom=20, margin_start=24, margin_end=24)
    tools = Gtk.Box(spacing=8); find = entry("Find", "find", root); replace = entry("Replace", "replace", root)
    saved_status = named(Gtk.Label(label="Document not saved", xalign=0), "Document save status")
    view = Gtk.TextView(); named(view, "Document"); view.set_wrap_mode(Gtk.WrapMode.WORD); state["content"] = "alpha beta alpha"; view.get_buffer().set_text(state["content"])
    view.get_buffer().connect("changed", lambda b: (state.__setitem__("content", b.get_text(b.get_start_iter(), b.get_end_iter(), True)), save("content")))
    scroll = Gtk.ScrolledWindow(min_content_height=260); scroll.set_child(view); root.append(scroll)
    tools.append(button("Replace all", lambda _w: (view.get_buffer().set_text(state.get("content", "").replace(find.get_text(), replace.get_text())), state.__setitem__("replaced", True), save("replace-all"))))
    tools.append(button("Undo", lambda _w: save("undo")))
    tools.append(button("Save", lambda _w: (state.__setitem__("saved", True), state.__setitem__("saved_content", state.get("content", "")), (STATE_DIR / "document.txt").write_text(state.get("content", "")), saved_status.set_label("Document saved"), save("save"))))
    root.append(tools); root.append(saved_status); win.set_child(root)


def list_app(win: Gtk.Window) -> None:
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=18, margin_bottom=18, margin_start=22, margin_end=22)
    filter_entry = entry("Filter", "filter", root); state["rows"] = 1000
    root.append(button("Amount", lambda _w: (state.__setitem__("sort", "amount-desc" if state.get("sort") == "amount-asc" else "amount-asc"), save("sort"))))
    top_status = named(Gtk.Label(label="Top three not recorded", xalign=0), "Top three status")
    root.append(button("Record top three", lambda _w: (state.__setitem__("top_recorded", True), state.__setitem__("top_three", [999, 998, 997]), top_status.set_label("Top three recorded: 999, 998, 997"), save("top"))))
    root.append(top_status)
    rows = Gtk.ListBox(); named(rows, "Rows"); rows.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
    for i in range(1, 1001):
        row = Gtk.ListBoxRow(); line = Gtk.Box(spacing=16); label = button(f"Item {i}", lambda _w, item=i: (state.__setitem__("selected", f"Item {item}"), save("select"))); named(label, f"Item {i}"); line.append(label); line.append(Gtk.Label(label=f"Amount {i * 17}", xalign=0)); row.set_child(line); rows.append(row)
        source = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
        source.connect("prepare", lambda _source, _x, _y, value=i: Gdk.ContentProvider.new_for_value(str(value))); row.add_controller(source)
        target = Gtk.DropTarget.new(str, Gdk.DragAction.MOVE)
        target.connect("drop", lambda _target, value, _x, _y, before=i: (state.__setitem__("reordered", True), state.__setitem__("reorder", [int(value), before]), save("reorder"), True)[-1]); row.add_controller(target)
        menu_click = Gtk.GestureClick(button=3)
        def context(_gesture, _count, _x, _y, item=i, anchor=row):
            pop = Gtk.Popover(parent=anchor); pop.set_child(button("Pin row", lambda _w: (state.__setitem__("pinned", f"Item {item}"), save("pin"), pop.popdown()))); pop.popup()
        menu_click.connect("pressed", context); row.add_controller(menu_click)
    rows.connect("row-selected", lambda _box, row: (state.__setitem__("selected", f"Item {row.get_index()+1}" if row else None), save("select")))
    scroll = Gtk.ScrolledWindow(min_content_height=420); scroll.set_child(rows); root.append(scroll); win.set_child(root)


def storm(win: Gtk.Window) -> None:
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=30, margin_bottom=30, margin_start=30, margin_end=30)
    def nested(_w): dialog(win, "Continue?", [("Cancel", lambda: save("cancel")), ("Continue", lambda: dialog(win, "Final confirmation", [("Confirm", lambda: (state.__setitem__("nested_confirmed", True), save("nested")))]) )])
    root.append(button("Destructive action", nested)); root.append(button("Correct action", lambda _w: dialog(win, "Correct dialog", [("Confirm", lambda: (state.__setitem__("correct_confirmed", True), save("correct")))]) ))
    root.append(button("Open notice", lambda _w: dialog(win, "Notice", [("Close notice", lambda: (state.__setitem__("notice_closed", True), save("notice")))]) ))
    root.append(button("Approve", lambda _w: (state.__setitem__("approved", True), save("approve"))))
    root.append(button("Choose file", lambda _w: Gtk.FileChooserNative.new("Choose benchmark file", win, Gtk.FileChooserAction.OPEN, "Open", "Cancel").show()))
    number = int(SEED.split("-")[1]) if SEED.startswith(("t4-", "t5-")) else 0
    if SEED.startswith("t5-") and number % 5 == 4: GLib.idle_add(lambda: (dialog(win, "Wrong dialog", [("Cancel", lambda: (state.__setitem__("wrong_cancelled", True), save("wrong-cancel")))]), False)[1])
    if SEED.startswith("t1-05-"): GLib.idle_add(lambda: (dialog(win, "Notice", [("Close notice", lambda: (state.__setitem__("notice_closed", True), save("notice")))]), False)[1])
    if SEED.startswith("t4-"): GLib.timeout_add_seconds(4, lambda: (dialog(win, "Delayed approval", [("Approve", lambda: (state.__setitem__("delay_approved", True), save("delay")))]), False)[1])
    if SEED.startswith("t5-") and number % 5 == 0:
        def timed():
            approval = Gtk.Window(title="Timed approval", transient_for=win, modal=True, default_width=360, default_height=160)
            approval.set_child(button("Approve", lambda _w: (state.__setitem__("timed_approved", True), save("timed"), approval.close()))); approval.present()
            GLib.timeout_add_seconds(20, lambda: (approval.close(), False)[1]); return False
        GLib.idle_add(timed)
    win.set_child(root)


def multi(win: Gtk.Window, application: Gtk.Application, include_reference: bool = True) -> None:
    number = int(SEED.split("-")[1]) if SEED.startswith("t4-") else 0
    if SEED.startswith("t4-") and number % 5 == 3:
        initialize_target_pair(state)
        def panel(role: str) -> Gtk.Box:
            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
            root.append(Gtk.Label(label="Review candidate", xalign=0))
            root.append(button("Mark target complete", lambda _w: (complete_target_window(state, role), save(f"complete:{role}"))))
            return root
        win.set_title(f"Target [{SEED}]"); win.set_child(panel("target"))
        distractor = Gtk.ApplicationWindow(application=application, title=f"Distractor [{SEED}]", default_width=760, default_height=650)
        distractor.set_child(panel("distractor")); distractor.present()
        return
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
    notes = entry("Notes", "notes", root); rebound = entry("Rebound value", "rebound", root)
    notes_status = named(Gtk.Label(label="Notes pending", xalign=0), "Notes status")
    root.append(button("Mark done", lambda _w: (state.__setitem__("notes_done", True), notes_status.set_label("Notes marked done"), save("done"))))
    root.append(button("Save notes", lambda _w: (state.__setitem__("notes_saved", True), notes_status.set_label("Notes saved"), save("notes"))))
    root.append(notes_status)
    def restart_target(_w) -> None:
        save("restart"); win.close()
        replacement = Gtk.ApplicationWindow(application=application, title=f"{APP} [{SEED}]", default_width=760, default_height=650)
        multi(replacement, application, include_reference=False); replacement.present()
    root.append(button("Restart target", restart_target)); win.set_child(root)
    if include_reference:
        ref = Gtk.ApplicationWindow(application=application, title="Reference", default_width=360, default_height=180)
        ref.set_child(Gtk.Label(label=f"Reference code: CODE-{int(SEED.split('-')[1]) if SEED.startswith('t3-') else 1:02d}")); ref.present()


def activate(application: Gtk.Application) -> None:
    win = Gtk.ApplicationWindow(application=application, title=f"{APP} [{SEED}]", default_width=760, default_height=650)
    {"forms-app": forms, "editor-app": editor, "list-app": list_app, "dialog-storm": storm}.get(APP, lambda w: multi(w, application))(win)
    save("launch"); win.present()


application = Gtk.Application(application_id=f"dev.hypruse.bench.{APP.replace('-', '')}", flags=Gio.ApplicationFlags.NON_UNIQUE)
application.connect("activate", activate)
GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: (application.quit(), GLib.SOURCE_REMOVE)[1])
raise SystemExit(application.run(None))
