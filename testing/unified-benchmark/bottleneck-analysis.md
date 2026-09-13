# Optimized-run bottlenecks

The fixed 24-task Astra run took 2245.7s. Tools occupied 1213.0s and everything outside tools 1032.7s. The latter includes model generation, scheduling, CLI startup, transport and teardown; the recordings cannot isolate pure inference latency.

| Measured tool component | Seconds | Share of outer tool time |
|---|---:|---:|
| Control-program calls | 671.4 | 55.3% |
| Isolated AT-SPI scans | 273.2 | 22.5% |
| Global-menu discovery | 128.2 | 10.6% |
| Explicit sleeps | 107.1 | 8.8% |

These are exclusive stage self-times. Remaining outer time includes transport, uninstrumented work and incomplete timeout traces. Control-program time includes process launches, nested hyprctl calls, native execution and waiting; it cannot all be attributed to Python.

## What creates the overhead

There were 3881 completed call_ctl calls, 211 completed AX scans and 211 global-menu queries. call_ctl starts a new Python control program. Plugin dispatch then queries hyprctl systeminfo to identify the config provider before another hyprctl invocation performs the operation.

The control-call parent buckets are 318.4s for mixed handler/session/policy work, 118.8s inside keyboard dispatch, 77.9s inside screenshots, 67.4s inside related-window discovery, 66.3s inside target resolution and 22.1s inside the visual action indicator. These subdivide 671.4s, rather than adding to it. Existing spans do not identify individual control command verbs in the mixed bucket.

finish_related_action_session polls up to six times. Each iteration sends session sync and separately queries related windows, with five 80ms sleeps when no dialog appears. Thus a normal action without a popup can pay 12 control-program calls plus 400ms of sleep just to finish its guard session. Begin/end and earlier guard checks add more calls.

snapshot_after_action waits 350ms, then rebuilds AX and global-menu state. Recorded post-action snapshot attempts consumed 291.4s, with another 49.0s in that fixed wait. The 291.4s overlaps the stage table and is not all removable: some observations are necessary. There were 146 attempts, including failed snapshots. The facade only reuses a post-action observation for an immediate AX read within 100ms. Consecutive deterministic actions still generate intermediate observations that the agent never reads.

type_with_keys launches keyboard dispatch separately for every character and sleeps 15ms between characters. All keyboard operations together accounted for 636 completed dispatches and 118.8s of control time. Per-character sleeps contributed only 8.6s. The process/IPC work matters much more than that 15ms setting. Typing operations totalled 279.0s across 29 recorded responses; this includes guards and observations, not just key emission.

Global-menu discovery repeats service/PID discovery and menu inspection on every snapshot, even without a usable provider. Ordinary screenshot requests also gather AX/menu state. Geometry resolution involves 913 completed target resolutions and 244 geometry refreshes, but their Python arithmetic is negligible; the control calls beneath target resolution cost 66.3s.

## Recommended optimization order

1. Keep a control worker alive and use direct Hyprland IPC instead of spawning Python and hyprctl for each command. Cache config-provider detection per compositor instance. Add control verb/phase timings first so native waiting can be distinguished from launch and query overhead. Preserve policy and exact target validation.
2. Batch key/text events into one native request, with per-event cancellation and lock/grab checks. This removes one process/IPC transaction per character. Explicit setValue is already useful for editable fields; clipboard paste needs its generic-table/Escape heuristic fixed before broader use.
3. Make intermediate mutations return acknowledgements and window/dialog-change metadata. Collect AX once at a decision boundary or before resolving a new numeric element target. Screenshot-only requests should capture pixels without scanning AX/menu state. Replace the unconditional 350ms wait with bounded readiness checks. Never reuse stale element indices after UI changes.
4. Keep the background guard active across a JS batch and track new dialogs from compositor events. Replace repeated sync/window polling with an event-driven or combined native operation. Preserve delayed-dialog protection, lease ownership, cancellation, EOF/crash cleanup and no-refocus tests. Simply removing the polls would weaken the behavior being tested.
5. Cache menu-provider capability by PID/starttime and D-Bus owner, including negative results. Refresh actual menus when requested or invalidated. Consider a restartable persistent AT-SPI worker to amortize initialization, with bounded requests so an unresponsive application cannot hang the server.
6. Correct Calc cell bounds from measured table/header geometry. The observed 9–10px error causes retries and screenshot recovery; do not hard-code that offset across scales. Formatting and chart failures consumed 180s each. Better dialog tracking and bounds should reduce both tool work and agent deliberation.

Reducing round trips may also reduce the 1032.7s outside tools, because the agent needs fewer recovery turns. Increasing timeout_ms for long batches prevents avoidable resets but does not make operations faster. Lower reasoning or another model would change the requested Astra-high comparison and is not the first intervention.

A Go rewrite alone would retain the same repeated IPC, scans and waits. The architectural changes above should come first. The measured 671.4s control bucket and 340.4s post-action snapshot/wait bucket overlap; they are affected-cost bounds, not additive savings forecasts.

## Validation

Use the existing five-repeat direct probes, then the same 24 tasks with fresh Astra-high processes. Keep outcome checks and focus-event monitoring. Add delayed-dialog, cancellation, reused-window-identity and active-input-grab cases before accepting session batching. Report successful-task time and all-attempt time separately; a failed task can appear fast.

This investigation used recorded runs and source inspection only. It did not operate the desktop or change runtime behavior. Machine-readable totals are in bottleneck-analysis.json.
