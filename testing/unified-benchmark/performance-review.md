# Baseline performance review

The first fixes should remove redundant observation work and repair click semantics. The 24 valid Astra tasks took 32m11s. Outer tools occupied 17m48s, 55% of task time. Nine tasks have supporting completion evidence: seven automatic fixture assertions and two parent-reviewed results. Twelve JavaScript calls timed out; agents often stopped because the timeout was reported as cancellation.

This is a read-only audit of recorded runs and source. I did not operate the desktop. Source paths below are relative to hypr-use. Machine-readable totals are in performance-review-metrics.json.

## What counts

Use tasks 01–17 from astra-baseline and 18–24 from astra-baseline-calc. Exclude the original Calc scope-misconfiguration attempts and all Sol setup runs. Every valid task uses a fresh Codex process with gpt-6-astra and high reasoning. Calc tasks form a dependent sequence; failed formulas invalidate downstream totals/chart prerequisites.

Seven fixture tasks pass independent requested-state checks. Text selection and requested-path save fail automatic assertions. Amazon comparison and Calc table pass existing parent review of screenshots and AX respectively. Wikipedia and back/forward have model-reported completion but no independent review record. The remaining tasks are incomplete or unverified. Exit code zero is not task success. Fixture checks do not check every possible collateral change.

Both phase focus records contain zero detected target-window refocuses. Temporary no_initial_focus and activation-suppression rules cover fixture/Calc windows. This establishes behavior under those rules and the monitored session, not a universal no-focus guarantee.

## Where time went

| Measurement | Baseline |
|---|---:|
| Task wall time | 1,931.1s |
| Outer tool time | 1,067.7s |
| Residual outside outer tools | 863.4s |
| Completed JS cells / portal calls | 90 / 143 |
| Completed screenshot captures / emitted images | 156 / 23 |
| call_ctl invocations | 2,208 |
| Screenshot call_ctl time | 473.3s |
| AT-SPI isolation self time | 98.0s |
| Global-menu self time | 60.8s |
| Explicit sleep self time | 47.7s |

Residual time includes model generation, scheduling, CLI startup, transport and teardown. It is not a direct model-latency measurement. Interrupted portal operations have no completed response record, so nested stage totals undercount their work. Self times avoid nested double-counting; screenshot call_ctl is a subset of all call_ctl time. The difference between captures and emitted images shows unused image work, not an exact recoverable-time prediction.

| Completed portal operation | Count | Median | Maximum |
|---|---:|---:|---:|
| get_app_state | 73 | 5.20s | 8.30s |
| click | 22 | 8.94s | 15.85s |
| press_key | 22 | 8.51s | 9.60s |
| type_text | 11 | 15.84s | 19.73s |
| set_value | 7 | 7.63s | 10.74s |
| select_text | 2 | 11.02s | 11.30s |

## Recommended implementation order

1. Separate AX, screenshot and combined observation in mcp/unified/facade.mjs and backend build_app_snapshot. AX calls currently capture pixels. Mutation responses build snapshots that act() immediately discards, followed by another explicit observation. There were 80 completed captures inside mutations, plus 76 during get_app_state. Introduce an internal acknowledgement-only mutation mode and invalidate observation caches on mutation. Preserve window identity, geometry checks needed for input, popup tracking and action warnings. Lazy AX refresh must occur before indexed targeting; never reuse numeric IDs after a layout change without validation. Test that AX-only performs zero captures, screenshot-only avoids AX when it needs no indexed resolution, and a mutation followed by observation builds exactly one needed observation.

2. Repair observation and click correctness before measuring speed claims. Parent is investigating transparent off-workspace images in src/plugin/screenshot_capture.cpp. Existing image-analysis records show RGB and alpha zero, so these are transparent captures displayed black. In facade click(), forced element_click_mode=atspi rejects non-actionable Calc cells in tasks18–22. Entries expose activate, which submits rather than focuses. Task24 proves this: clicking Save dialog Name entry6 closes the dialog and changes the title to Untitled 1.ods; subsequent pinned-target access correctly fails. Use guarded widget-focus semantics for edit controls and guarded pointer fallback for non-actionable cells only with validated geometry. Never bypass identity rejection. Emit targetClosed/continuedWithTarget warnings currently discarded by act(). Test entry clicks do not submit, Calc cell clicks select a cell, and closed-dialog handles stay rejected.

3. Fix selectText followed by typeText. Task06 puts DELTA into Name instead of Note. The recorded Note still contains alpha beta gamma. AT-SPI selection alone does not direct subsequent window keyboard input to that widget. Establish focus within the target's protected background session, verify focused state/selection, then type. Keep the user's foreground unchanged. Add a two-entry live regression asserting both intended replacement and unchanged other entry. Include timeouts and dialog creation in focus monitoring.

4. Fix AX state extraction and traversal. Newsletter checked state and Country selected value are absent from structured elements, not just rendered text. Expose checked/selected/expanded and selection-derived combo text. Zen task09 reaches the 500-record cap with offscreen page tabs at y≈19,000 before reaching document content. Prioritize the selected document and useful chrome; prune inactive tab descendants and viewport-ineligible leaves while preserving structural ancestors and selected content. A blanket offscreen-node removal can drop needed descendants and is unsuitable. Test that fixture selection changes appear in AX diffs and a browser with many tabs still exposes active-page content within the record budget.

5. Distinguish timeout from user cancellation in mcp/unified/server.mjs. Twelve calls hit the default 30s timeout, commonly in three- or four-operation navigation batches. Report the elapsed limit and that partial actions may have completed. Preserve completed-operation timings using incremental worker messages. clearTimeout in every stop path and bind cancellation to the active request ID. Do not turn a larger default timeout into the main performance fix; keep 30s for the matched run and use explicit longer timeouts only for separate recovery runs. Test timeout vs notification vs reset, an unrelated cancellation ID, and cancel/reset followed by a new call.

6. After those changes, optimize guarded-session command overhead if still material. finish_related_action_session performs up to six sync attempts and five 80ms waits, while call_ctl's handler/session/policy category totals 162.1s. That category is mixed and cannot be assigned wholly to sessions. Add command verb, phase and target tags before selecting a narrower optimization. A persistent guarded session with event-driven popup tracking may amortize setup, but must survive delayed dialogs and clean up on timeout, EOF and process death. Do not remove guards or arbitrarily shorten the protection window. Global-menu discovery accounts for another 60.8s; a per-process capability cache with invalidation is a secondary candidate, not the first change.

Geometry needs an explicit correctness test before pointer fallback. Fixture AX frame x≈840 while the window origin is -840 and AX root is local zero. atspi_bounds_are_global currently accepts overlapping bounds as sufficient evidence. Test local/global coordinate roots on negative-origin windows, viewport offsets, scaling and resize. Overlap alone does not establish a global coordinate space.

## Matched rebenchmark

Keep Astra high, the 24 task prompts, 30s default JS timeout, 180s task cap, tool access, owner policy and focus rules fixed. Record backend/plugin revisions and loaded ABI. Reset fixture state and private Calc profile before each full phase; preserve the original initial table and dependency order. Remove only benchmark-owned browser tabs or use a documented repeatable tab inventory. Do not compare a sparse clean browser with the baseline's many-tab Zen state without marking the change.

First run deterministic regressions for text selection, editable clicks, pointer geometry, checkbox/combo AX, active browser document, popup save and transparent-image detection. Run direct repeatable operation probes with at least five repetitions for AX, screenshot, a harmless text change and guarded key input. Report medians and tails separately from whole-agent time.

Then repeat all 24 tasks with fresh Astra processes. Add independent ODS inspection for cells, formulas, totals, sort, styles and chart; requested file existence alone is insufficient. Preserve task-level success and failure results even when later tasks have missing prerequisites. Report all-attempt wall time and success-matched task speed separately so early failure cannot look like improvement. Any observed target refocus is a regression and should stop the phase. Include monitor start/end, socket errors, sample counts and target discovery coverage.

## Task timings and outcome evidence

| Task | Wall s | Tool s | Evidence |
|---|---:|---:|---|
| 01-form-name | 47.4 | 19.8 | Automatic pass |
| 02-form-email | 71.1 | 34.3 | Automatic pass |
| 03-form-country | 71.8 | 42.6 | Automatic pass |
| 04-note-save | 56.9 | 26.3 | Automatic pass |
| 05-note-reopen | 63.0 | 32.9 | Automatic pass |
| 06-text-selection | 104.2 | 68.4 | Automatic failure |
| 07-create-folder | 44.1 | 25.7 | Automatic pass |
| 08-dialog-confirm | 62.2 | 28.1 | Automatic pass |
| 09-google | 59.4 | 35.3 | Incomplete or unverified |
| 10-wikipedia | 81.6 | 51.0 | Reported completion, unreviewed |
| 11-browser-find | 62.2 | 35.8 | Incomplete or unverified |
| 12-browser-navigation | 169.7 | 113.0 | Reported completion, unreviewed |
| 13-browser-tabs | 68.6 | 35.3 | Incomplete or unverified |
| 14-web-extract | 67.1 | 35.4 | Incomplete or unverified |
| 15-web-scroll | 65.4 | 37.0 | Incomplete or unverified |
| 16-amazon-compare | 153.2 | 86.7 | Parent-reviewed pass |
| 17-manufacturer-compare | 180.0 | 115.0 | Incomplete or unverified |
| 18-calc-table | 178.1 | 99.8 | Parent-reviewed pass |
| 19-calc-formulas | 45.8 | 17.3 | Incomplete or unverified |
| 20-calc-sum | 44.5 | 17.1 | Incomplete or unverified |
| 21-calc-sort | 80.5 | 42.2 | Incomplete or unverified |
| 22-calc-format | 48.8 | 19.0 | Incomplete or unverified |
| 23-calc-chart | 36.4 | 12.6 | Incomplete or unverified |
| 24-calc-save | 69.2 | 36.9 | Automatic failure |


## Follow-up visual review

Baseline tasks10 and12 now pass recorded-screenshot review. Their per-task review.json files identify exact wire lines and extracted images. Task10 visibly shows Ada Lovelace's birth date, 10 December 1815, on Wikipedia. Task12 screenshots after Back and Forward show Example Domain and IANA Example Domains at the requested URLs. These are separate review judgments based on the agent's captured observations, not fresh browser-state checks. The original totals above predate this follow-up; supported completion count is now eleven, comprising seven automatic fixture assertions and four reviewed passes.

Source follow-up confirms the main implemented changes: image-free AX/mutation observations, short-lived reuse of post-action AX, editable pointer focus/auto click fallback, closed-target warnings, state extraction and timeout/cancellation handling. Remaining recommendation gaps are bounded: mutations still rebuild AX after every action, so deterministic batches do not yet use acknowledgement-only actions with one final observation; screenshot-only still gathers AX by the stated design; session-command and global-menu caching remain deferred pending measurements. The short 100ms reuse avoids some duplicate reads but cannot eliminate intermediate snapshots between consecutive actions. Describe this as removing image capture from mutation snapshots, not removing all post-action snapshot work. No live behavior or performance improvement is established by this source-only follow-up.
