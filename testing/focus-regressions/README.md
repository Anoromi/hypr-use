# Same-desktop focus regression

Run from the project root with `python testing/focus-regression.py`.

This uses the user's running Hyprland desktop, a disposable native GTK application, and an unused workspace starting at 901. It does not substitute a nested compositor. The current foreground window belongs to the user, not a test sentinel.

The monitor connects to Hyprland socket2 before launch and also samples activewindow every 100ms. It records stage boundaries, new-window mapping, active-window changes, workspace events, and tool responses. A transfer to an agent-owned window fails the test; a switch between unrelated user windows does not. On detection it stops further tool calls and terminates only its disposable fixture. A currently running observation can still take time to return. The detector tests cover active-before-map event ordering and duplicate observations.

## Observed failure and fix

Run 20260909-224733 reproduced a refocus. The background parent mapped on workspace 901. Typing and selection replacement succeeded while T3 stayed active on workspace 2. During an explicit AT-SPI click on Open test dialog, the new modal mapped on workspace 2 and immediately became active. Its openwindow event and activewindowv2 event were 0.15ms apart. Cleanup closed only fixture windows and T3 became active again.

The new semantic_atspi_click implementation introduced in the previous accessibility experiments skipped begin_related_action_session. The native plugin's early mapping hook protects same-client dialogs only while a workspace session is registered. Without that registration, normal compositor mapping assigned focus to the new modal. This was a regression introduced by our accessibility change, not proof the plugin cannot preserve focus.

The explicit AT-SPI path now starts that guard before dispatch, refuses dispatch if the guard cannot start, and finishes/synchronizes it afterward even when dispatch raises. Screenshot visibility is still not required for semantic activation, and identity checks still apply.

Run 20260909-224944 passed seven tool calls and all four application-state checks: typed text, selection replacement, popup open, popup close. No refocus events were observed across 392 active-window samples plus socket2 events. Baseline and final foreground were T3 on workspace 2. The dialogs and fixture were cleaned up.

## Limits

This is a controlled native GTK fixture, not a guarantee for every application. It does not retest LibreOffice's splash-to-main-window launch behavior, every keyboard shortcut that creates a dialog, or applications that request activation later. Before-fix logs contain repeated poll observations of one sustained refocus; these are not separate focus transfers. The updated detector deduplicates a continuous episode. A dropped socket/event stream or transient shorter than the polling interval could limit observation; socket2 covers transitions that sampling alone can miss.

Files in each timestamped folder: summary.json, focus-events.jsonl, tools.json, fixture-state.json, fixture.log. The first attempt 20260909-224638 never mapped a fixture because its launch environment lacked the GTK typelib path; it is a setup failure, not a background-operation pass.
