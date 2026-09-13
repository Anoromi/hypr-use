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

## Checkbox form fields

`fill_form` now accepts boolean checkbox values alongside string text fields. It skips already-correct states, verifies changed states, and rejects mixed/unknown states before mutation. `wait_for` can match boolean checked state. AT-SPI indeterminate checkboxes are reported as mixed rather than unchecked.

Two repeated-call browser probes passed; their second calls issued only AX reads, no input (`diagnostics/loop-checkbox-probe`). Fresh Astra before/after pairs passed with no errors/refocuses: mixed native form 34.1 → 32.6 s and browser checkboxes 33.7 → 32.1 s. Native task calls fell from three to two; browser calls stayed at two. These single-run task timings do not establish a general speedup. Both updated agents chose the combined `fill_form`. Twenty-one JS/protocol tests and the mixed-state Python regression passed.

## Verify the whole form before submission

A reactive Email input reset the previously verified Full name. The old helper still submitted the wrong name and returned completed (`loop-final-form-before`). The helper now rechecks all requested fields against its final verification snapshot before submission, without another scan. A mismatch emits that snapshot and stops. This catches changes visible in that snapshot; it is not an atomic guarantee against later application changes.

Two negative probes now correctly rejected the invalid form without saving; an ordinary form passed (`loop-final-form-after`). A fresh Astra reactive-form variant recovered from the error, restored only the name, and saved correct data in 43.16 s. Its entire submission history contained no incorrect save. No refocuses. The variant is explicitly recorded separately from standard suite results. All 22 JS/protocol tests pass.

## Skip already-matching text

Default `fill_form` skips visible string values already equal to the request, just as it already skipped matching checkboxes. An explicit method forces re-entry; missing values and password fields are never assumed to match. The final whole-form verification remains active.

Two repeated-fill probes changed from 3.593/3.633 s to 0.360/0.350 s (median 3.613 → 0.355 s, 90.2% less helper time). Fresh first fills and the reactive negative test still passed. Fresh Astra selected combined fill_form on a separately labeled prefilled-form variant, skipped the correct name, and saved the correct email. Independent input-event grading confirmed zero unnecessary name input. Agent run 59.57 s: helper savings did not translate into a demonstrated end-to-end gain in this single run. No refocuses. All 24 JS/protocol tests pass. Evidence: loop-unchanged-before/after diagnostics and loop-unchanged-astra.

## Lossless compact AX geometry

AX text now prints frame coordinates as `[x,y,width,height]` with one legend, retaining all nodes, indices, actions, states and geometry. `compactGeometry:false` retains the verbose labels. Raw structured snapshots are unchanged. The sampled native tree shrank 1341 → 1058 characters (21.1%); browser tree 18228 → 14801 (18.8%). These are character counts, not measured token or inference savings.

Fresh Astra dropdown-selection and product-comparison tasks both passed (35.35 s, 23.94 s), with no tool errors or refocuses (`loop-compact-ax-astra`). All 25 JS/protocol tests pass. End-to-end speed improvement is not established by these adoption runs.
