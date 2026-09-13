# Investigation notes

These are evidence and hypotheses, not completed fixes or final reliability claims.

## Launch failure before the first agent action

The aborted `baseline` phase passed tasks 1–2. Task 3 mapped `hypr-use-bench` onto workspace 2 and gained focus. The monitor terminated it; focus returned to T3 Code about 25 ms later. The exact reason the temporary class rule stopped applying was not captured. Do not claim garbage collection or a config reload as established causes.

The harness now reinstalls its temporary rule on each launch, attaches an independent `[workspace 902 silent]` exec rule, tracks the owned process identity, and asserts workspace placement before starting the agent. Ten consecutive launch checks passed without focus changes. The full restarted phase is `baseline-v2`. The aborted phase remains visible and is excluded from paired task-performance comparisons, not erased from background-safety reporting.

## Browser pilot: mixed coordinate scales

In pilot task 21, root AX bounds were 1757×1119, while the web-document bounds were x=0,y=139,width=2812,height=1652. That is approximately 1.6× the root coordinate scale. Full name AX entry bounds were x=848,y=353,width=402,height=59. AX-index clicks did not visibly edit fields; the agent recovered with screenshot coordinates around x=641,y=238 and ultimately passed.

The entry exposed `editable=false` and `supportsEditableText=false`. setValue returned a clear unsupported-element error, but these capability flags were not visible in the compact tree. This suggests two shared improvement candidates: normalize mixed coordinate spaces before index-based input and display actual text-edit capabilities. Both are implemented in pilot-general, pending evaluation.

Primary source reference for coordinate semantics: https://chromium.googlesource.com/chromium/src/+/refs/heads/main/ui/accessibility/platform/ax_platform_node_auralinux.cc . Chromium's GetExtentsRelativeToAtkCoordinateType requests kScreenDIPs. Installed-version behavior still requires direct measurement; this source alone does not explain the observed mismatch.

## Office pilot

Calc passed in 160.6 seconds despite a first-launch welcome dialog and repeated six-second AX timeouts. The fresh-profile harness attempts to suppress FirstRun and ShowTipOfTheDay, but the welcome dialog still appears. Writer ended with provider error "Selected model is at capacity"; this is not evidence that Writer GUI automation failed. Accessibility timeout causes remain unproven.

## Measurement discipline

Do not modify MCP/runtime sources during baseline-v2. Preserve every original result. Use exact final document/fixture state for grading. Independently classify provider failures, setup errors, timeouts, task failures and refocuses. Choose shared fixes from repeated failures, then run a complete new phase and report regressions as well as improvements. Source edits to the report/analysis scripts do not change the frozen runtime.

## Keyboard routing candidate

semantic_press_key chooses best_scroll_element and passes its screenshot-relative center as x/y to keyboard(). The native dispatcher interprets these as global coordinates and resolves a hit-tested surface. type_with_keys instead uses the explicitly targeted main surface without coordinates. This is an inconsistent path for modifiers/shortcuts versus typed characters. Test main-surface routing for pressKey after the frozen baseline completes; do not claim causality before a controlled probe.

Examples 12 and 13 failed navigation. IANA task 14 recovered after a screenshot-coordinate click in the address bar. Date-entry task 25 also failed while the web-modal task 26 passed. These results do not establish that every failure shares one cause.

## Additional shared candidates

- `pressKey` facade splits on spaces to normalize modifiers but forwards the entire string to a backend that accepts only one combination. Task 25's `pressKey('1 0')` failed. Implement ordered native key combinations within the same JS call, with validation and no hidden retry.
- Calc's initial AX output is about 40,699 characters and hits the 500-record limit on mostly empty grid cells. Preserve real zero values and unknown reads, selected/focused cells and a bounded sample of confirmed empty text cells. Do not infer emptiness from a numeric zero alone. Ensure later controls become reachable without skipping nonempty cells.
- Task 35 has a confirmed SIGABRT core dump. Stack includes QuickSelectionEngine::HandleKeyEvent and GtkInstanceComboBox::signalKeyPress after dialog OK and Ctrl+S. Task 38 became unresponsive after a semantic menu action. Test native pointer dispatch for AX-index clicks as an alternative to implicit AT-SPI activation. Explicit secondary actions should remain explicit; do not silently retry an action that may already have executed.
- The attempted LibreOffice FirstRun/ShowTipOfTheDay flags did not suppress its welcome dialog. Keep the same setup for the paired comparison; do not count a changed startup profile as a tool improvement.

## Completed baseline and targeted improvement checks

Baseline-v2 completed all 50 tasks: 43 pass, 7 fail, zero provider errors, zero refocuses. Failures: 12, 13, 25, 27, 35, 38, 47. Agent time totals 3490.82 seconds; measured server handlers total 826.71 seconds. The remainder includes inference, provider/CLI waiting and orchestration, not pure inference.

The first shared patch includes document-only coordinate normalization, explicit setValue capability text, supported-interface guards, blank-text grid summaries that preserve reported numeric values, native pointer clicks, main-surface keyboard routing, and ordered key sequences. No task-specific identifiers or answers were added to runtime code.

The user requested failed cases first. Pilot-general is a targeted development phase, excluded from the final full-suite failure rate. Example navigation passed with recovery: the first indexed address-bar input and Ctrl+L attempt had no effect; a later coordinate click worked. Date entry and Calc sort passed. This does not yet establish that the underlying navigation problem is fixed.

Writer's original table failure: element 5 was the correct row spin control. setValue changed its AX text from 2 to 3, then AT-SPI activation of Insert produced a saved 2×2 table. The generic setter prefers EditableText over Value; an uncommitted spin control text edit is a plausible cause. Test the actual numeric Value interface rather than declaring a wrong model target.

## Confirmed native F11/F12 mapping defect

The production parser returned KEY_F1 + n - 1 for F1-F12. Compiling the production function in isolation reproduced F11=69 instead of 87 and F12=70 instead of 88. Those wrong codes are Num Lock and Scroll Lock. An explicit table of Linux KEY_F constants corrects the parser. The regression test passes after the change. The rebuilt plugin is recorded in plugin-builds.json; it must be loaded only between runs.

Pilot-general Writer table still failed before this plugin was loaded, while Example, date, Calc sort and rename passed. Native click mode alone does not resolve every failure.

## Browser input ordering probe

On fresh owned browsers, click+type failed with indexed and coordinate clicks, batching and separated calls, additional waits, screenshots before input and AX/screenshots after click. These are controller-driven diagnostic probes, not extra agent task results. The input-v2 probe had a controller setup error and is retained separately.

The native experiment wraps pointer activation in a target-client KeyboardResourceTransaction. It sends keyboard enter before the pointer click and restores the target client's previous resource afterward. It does not assign global seat keyboard focus. Index-batch, point-batch and index-split then all navigated successfully, without screenshots or refocus. Shortcut-only Ctrl+L still failed; this limitation is not solved by the click change.

Writer passed in pilot-numeric-fkeys after correcting F12 and preferring numeric Value over EditableText for controls exposing both interfaces. Its saved 3×2 table was independently verified. Pilot-failed-final reruns all seven original failures on the combined version before any full-suite rerun.

## Segmented typing and false setter acknowledgements

Pilot-failed-final passed six of seven cases, but date entry failed again. Typing 2026 produced year 6; month and day also retained only final digit values. Each character previously created its own target-client keyboard enter/leave pair, resetting the segmented field's edit state.

The native keyboard dispatcher now accepts a validated sequence of up to 4096 key events in one transaction. typeText and multi-key pressKey use it. Keys are validated and resolved before emitting input; repeated keymap resolutions are cached within the sequence. No text, field names, date values or task identifiers are embedded in the implementation. Long text can use paste.

Numeric setValue now reads back the actual value with a bounded 150 ms confirmation interval. A provider's acknowledgement without a matching value produces a tool error. A setter error does not trigger hidden retries or another mutation.

Direct fresh-browser probes passed date entry through both typeText and multi-key pressKey, producing saved date 2026-10-21. Click-based navigation still passed. Shortcut-only navigation remains unresolved. No refocus occurred. Pilot-failed-sequences starts with the failed date case before the other six and before the full suite.

## Completed full comparison

Both full phases completed all 50 tasks with the same catalog, benchmark harness, Astra xhigh settings, fresh profiles and initial-failure assertions. Baseline-v2: 43 passes, 7 failures. Improved-v1: 50 passes, zero failed tasks, zero regressions. Both completed phases recorded zero refocuses; the earlier aborted setup refocus remains in the report. The loaded plugin's declared path, file hash, compositor identity and plugin handle matched before and after improved-v1. Process maps were not readable, so the binary provenance record explicitly uses the successful load command plus file hash.

Total agent-run time changed from 3490.82 to 2719.58 seconds, a 22.1% reduction. The 43 tasks that passed in both phases also became faster in aggregate: 2765.62 to 2194.67 seconds. Individual tasks did not all improve. JS calls changed from 319 to 258, images delivered from 104 to 34, explicit tool errors from 16 to 7, and AX timeouts from 33 to zero.

All 100 task timelines aligned with their wire recordings. Separate failure-associated agent-gap accounting is a reviewed lower bound, not direct inference telemetry. Stronger offline checks in 15 office cases per phase found no disagreement with scored passes. Public page reviews confirmed actual page content and Google tab preservation.

Limits remain: one fresh attempt per task in each full phase; development retries excluded from scoring; shortcut-only Ctrl+L still fails a separate fresh-Chromium probe; individual pressKey calls still use separate transactions; date setters can expose a Value interface without applying changes; some successful tasks needed recovery. The suite covers GTK, Chromium, Calc and Writer, not general Zen/XWayland reliability.
