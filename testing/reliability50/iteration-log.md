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
