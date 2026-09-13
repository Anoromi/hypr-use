# Focused API performance experiments

Checkpoint: `9ef2795` on `main`. Native portal checkpoint: `bcab301`, also preserved as `vendor/portal-checkpoint.patch`. Experiments are on `experiment/api-performance`. Raw runs and owned profiles remain local.

## Changes kept

The unified adapter skips separate D-Bus global-menu discovery. Its JS facade never exposed those results or their activation method. Visible AT-SPI menus remain available. Set `HYPR_USE_GLOBAL_MENU=1` to restore discovery for diagnostics. Native code, identity rematching, frame preparation and background popup guards are unchanged.

API instructions now describe the existing single-transaction keyboard sequences: newlines and tabs in `typeText`, and space-separated chords in `pressKey`. This lets agents avoid separate text/Enter calls and clipboard import dialogs where deterministic keyboard input is appropriate. Calls are not automatically merged.

## Fresh Astra tasks

Same three tasks, fresh profiles and GPT-6 Astra xhigh CLI threads, same catalog, prompt, limits and graders. Only `observations.py` changed between these two phases. No whole-suite rerun.

| Task | Agent seconds before → after | Handler seconds before → after | Result |
|---|---:|---:|---|
| Calc formulas | 140.46 → 72.51 | 28.89 → 11.20 | Both passed |
| Calc chart | 123.82 → 94.81 | 30.45 → 10.94 | Both passed |
| Writer replacement | 77.28 → 75.42 | 15.88 → 8.86 | Both passed |

Three passes per phase; zero refocuses. The baseline formula agent recovered from one tool error; none appeared in the three menu-optimized runs. Stronger independent file audits agreed with all six grades. Total agent duration fell 29%; handler duration fell 59%. Agents chose different workflows, so total changes are not isolated causal estimates. Other elapsed time includes inference, provider waiting and CLI orchestration.

Reproduce analysis with `python3 testing/reliability50/compare_api_costs.py`. Raw phases are `runs/api-cost-before` and `runs/api-cost-after`; summary is `api-performance.json`.

## Controlled action costs

Same untouched Calc window, four fresh MCP sessions in menu-on/off/off/on order. Excluding each process's initial observation, six samples per mode gave median AX-call times of **1.646 → 0.717 seconds**, 56% less. All twelve steady outputs were identical. The first startup observation preceded the Welcome popup and omitted its attention line; startup was excluded from the comparison.

Four fresh seeded Calc files used split/combined/combined/split input order. Entering the same header and three formulas took **3.429 → 0.424 seconds** median, 88% less, with all four saved files passing and no refocuses. Eight text/Enter calls become one existing `typeText` call. The native input transaction and its popup guard still run; no guard interval was shortened.

Reproduce with `python3 testing/reliability50/probe_table_input.py UNIQUE-NAME`. Evidence is in `diagnostics/api-cost-controlled` and `api-controlled-results.json`. These are action probes, not model benchmarks.

Regression checks: `test_api_costs.py` passed 2 checks, `testing/test-ax-frame-preparation.py` passed 3, and `mcp/unified/test.mjs` passed 6.

Remaining costs include accessibility scanning, per-call popup protection, and model/CLI gaps. These results cover selected Calc/Writer cases and do not establish universal reliability or Zen performance.

A separate fresh Astra run after the API instruction update used the combined newline call, passed in 71.07 seconds with 8 JS calls, and recorded zero refocuses. Handler time was 12.14 seconds. One run does not establish an additional total-task speedup. Its recording is `runs/api-batching-hints`; summary is `api-batching-hints.json`.

That instruction-validation run recorded one rejected `ArrowDown` during verification. The facade now accepts `ArrowUp`, `ArrowDown`, `ArrowLeft` and `ArrowRight`, including modifier chords, by mapping them to the portal's existing key names. This is a later correction, excluded from the menu-only comparison. Its direct Calc regression is `diagnostics/api-arrow-alias`.

The arrow regression passed: clicking D2 then `ArrowDown` selected D3, with the saved formulas intact and no refocus. Summary: `api-arrow-alias.json`.
