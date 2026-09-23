from __future__ import annotations

from .catalog import Task


def _goal(task: Task) -> str:
    if task.tier != "T6": return task.prompt
    spec = task.oracle[0]["tool_benchmark"]; kind = spec["kind"]
    if kind == "rapid": return f"Click Complete exactly {spec['count']} times and verify the displayed count."
    if kind == "latency": return "Extract all 1,000 rows and their descendants with app.getAXState({maxRecords:8000,timeBudgetMs:30000,disableDiffing:true}); verify Item 1000 is present. This is a completeness task, not a speed score."
    if kind == "launch": return f"Launch {spec['count']} forms-app instances with cua.launch and verify each returned a distinct address."
    if kind == "restart": return "Observe forms-app, recover its binding after the connection restart, and verify it remains readable."
    if kind == "parallel": return f"In your assigned workspace, launch one fixture and report its owned window and workspace ID; the harness runs {spec['count']} agents concurrently."
    if kind == "text" and "\n" in spec["value"]: return f"Use app.typeText to replace editor-app Document with this exact multiline value and verify it round trips unchanged: {spec['value']!r}."
    if kind == "text": return f"Replace forms-app Name with this exact value using plain-text paste and verify it round trips unchanged: {spec['value']!r}."
    if kind == "click": return f"Activate Complete using the {spec['mode']} click method and verify its status changed."
    if kind == "tracking": return f"Track the moving Complete target across at least {spec['count']} observations and report the distinct frames."
    return task.prompt


def agent_prompt(task: Task) -> str:
    apps = ", ".join(task.setup_apps or (task.app,))
    return f"""Complete this desktop task using only cua_repl: {_goal(task)}

Target application(s): {apps}. Scenario: {task.seed}.

Choose the primary fixture whose title ends with [{task.seed}]. Related dialogs or same-process secondary windows may have fixed titles without that suffix; bind those through the seeded app relationship or matching process, never through an older primary fixture. Start with cua.listApps() when the target is ambiguous, then use cua.getApp() with its inventory id or address. After a window restarts or closes, list and bind it again; stale indices and bindings are invalid.

Use the supported cua API: getApp/listApps/getState, app AX or screenshot observations, click/drag/scroll/pressKey/typeText/paste/setValue/selectText, and workflow methods. Large AX trees can use getAXState({{maxRecords:8000,timeBudgetMs:30000,disableDiffing:true}}). For known forms use app.fillForm({{fields:[{{name,value,role?,method?}}],submit?}}); string values edit fields and booleans set checkboxes. For combo boxes use app.selectOptions({{choices:[{{name,option,role?}}],submit?}}). app.waitFor() accepts exactly one of target, text, or dialog_title plus optional value and timeout_ms. Use app.getDialog({{title,timeout_ms}}) after opening a related dialog; it waits for an exact title for up to 30000 ms and does not click it. setTimeout/clearTimeout support bounded delays from 0 through 30000 ms, though waitFor/getDialog should handle UI waits. Shell, filesystem, network, browser automation, and hyprctl are unavailable.

Work until the requested state is complete. Re-observe after changes and do not treat an action acknowledgement as proof. Do not move global focus. Emit a concise final result."""
