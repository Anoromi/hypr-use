# Continuous improvement iterations

## Selection readback

Controlled fresh Chromium probes passed 0/2 before the fix and passed 2/2 after it. AT-SPI accepted the selection but the immediate readback preceded the asynchronous update. Readback now waits at most 150 ms, stops immediately on a match, and never repeats the selection mutation. Both saved notes contained exactly `alpha DELTA gamma`.

Fresh Astra xhigh runs `loop-selection-astra` passed native and browser replacement tasks. Both agents successfully used `selectText`; no foreground refocus occurred. Native run: 39.31 s, browser run: 44.19 s. A separate native `fill_form` attempt rejected the matching label plus field as ambiguous; that is the next issue to fix. These are reliability checks, not paired speed measurements.

Evidence: `diagnostics/loop-selection-before`, `diagnostics/loop-selection-readback`, and `runs/loop-selection-astra`. Four deterministic readback tests pass. The run manifest now also hashes all vendor MCP Python modules so selection/security changes cannot be omitted from runtime provenance.

## Field selectors

Field operations now match editable/value controls, excluding same-name labels. Explicit label selectors fail before keyboard input. Multiple editable fields with the same name still fail as ambiguous. The previously failed native `fill_form` call succeeded in a fresh Astra run (`loop-field-selector/06-replace-word`), followed by successful substring selection. Whole task passed in 36.02 s with no tool errors or refocuses. Sixteen JS/protocol tests pass, including label collisions and duplicate editable fields.

## Chromium field capabilities

The next browser probe exposed a regression in the editability filter: Chromium's AT-SPI `entry` nodes can omit both EDITABLE and EditableText while native input still works. Field matching now also recognizes entry/password/spin-button roles. Default form input uses a supported setter when available, otherwise native keys. An explicitly requested unsupported setter is rejected before input rather than silently falling back.

The failed probe is retained in `diagnostics/loop-workflow-cost-before`. Two fresh browser probes passed after correction (`loop-field-browser-fix`), followed by a fresh Astra profile task using the default form method: 36.36 s, pass, zero tool errors and zero refocuses. Seventeen unit/protocol tests pass.

## Blocking application-name enumeration

Several following probes timed out at six seconds, including initial AX reads. An opt-in child stack dump showed the scanner blocked in `atspi_name` inside `atspi_iter_apps`, before target PID matching. Removing eager app-name requests from enumeration made both failed form probes pass again. PID matching and mutation identity checks remain unchanged. Empty names are explicitly excluded from the later name fallback.

Debug support uses `HYPR_USE_AX_DEBUG_STACK=1`; binary stderr from timed-out children is now retained so stack traces are not discarded. Evidence: `diagnostics/loop-ax-timeout-stack`, `diagnostics/loop-ax-enumeration-fix`. Two fresh Astra tasks passed (`loop-enumeration-astra`): navigation 22.6 s and form fill 37.6 s, with no timeouts or refocuses. Four enumeration/diagnostic tests and existing AX semantics checks passed. The scan-reuse candidate was set aside during this investigation.

## Reuse observations between actions

Form helpers reuse the preflight snapshot for the first field and each verified snapshot for the next field or submit lookup. Native/indexed actions still perform their own fresh identity rematch. Navigation reuses its initial lookup when no tab-opening action intervenes. A form without submission emits its already verified final snapshot.

On the stable enumeration build, two matched fresh key-input form probes changed from 8.347/8.681 s to 6.557/6.865 s: median 8.514 → 6.711 s, 21.2% lower helper time. Both methods, the auto-route form, and navigation/wait probes passed (`diagnostics/loop-scan-reuse`). Two fresh Astra tasks passed: native replacement 35.16 s and form fill 31.25 s, no errors/refocuses (`loop-scan-reuse-astra`). Eighteen unit/protocol tests pass. The earlier timeout attempts remain recorded separately and are not substituted into the stable timing comparison.

Probe cleanup now verifies process start time before terminating its owned app, and probe summaries explicitly mark incomplete/aborted runs.

## Fused replacement input

`typeText(text,{replaceAll:true,submit:true})` can send Ctrl+A, validated text, and optional Enter in one existing native keyboard transaction. Empty replacement sends Ctrl+A then Backspace. Full validation occurs before dispatch; the 4096-key limit includes prefix/suffix events. Workflows use this path for supported-sized key input and retain explicit paste/setter behavior.

Five controlled cases passed, plus a separate nonempty-to-empty replacement check. Two form input segments fell from 1.922/1.879 s over four backend calls to 0.866/1.390 s over two calls. Whole-form timings were noisier: 6.557/6.865 → 5.765/6.788 s. Navigation plus wait was 3.493 → 2.838 s in one probe each; these small samples are not universal latency estimates.

Fresh Astra runs `loop-fused-astra` all passed: new Google tab 30.61 s, form fill 32.81 s, note edit 43.32 s. No refocuses. Evidence: `diagnostics/loop-fused-input`, `diagnostics/loop-fused-clear`. Nineteen JS/protocol tests, four fused-input tests and ten general-fix tests passed. No native plugin rebuild was needed; the existing sequence dispatcher handles these keys.
