# 50-task background reliability suite

Ten tasks each for a native GTK fixture, Chromium navigation, local web workflows, LibreOffice Calc and Writer. Five tasks visit public sites. This measures this task set, not general desktop reliability or Zen support.

Each task starts a fresh owned app profile and a fresh GPT-6 Astra xhigh CLI thread using the unified JS MCP. The initial evaluator must fail. Final files, browser state or fixture events determine success. Agents cannot access the evaluators. Task and provider failures, setup errors and foreground changes remain recorded.

```bash
python3 testing/reliability50/run_suite.py phase-name
python3 testing/reliability50/run_suite.py phase-name 25-web-date
python3 testing/reliability50/analyse_runs.py phase-name
python3 testing/reliability50/report.py
```

The runner refuses to adopt existing target apps. It launches owned processes on workspace 902 with an explicit silent-workspace rule and stops if an owned window becomes foreground. Do not run two GUI phases concurrently. Runtime and task source hashes must remain unchanged during a phase. Record the loaded native plugin before and after with `record_plugin.py OUTPUT.json`.

The completed comparison is `baseline-v2`, 43 passes and 7 failures, versus `improved-v1`, 50 passes and zero failed tasks. Both full phases recorded zero refocuses. The earlier `baseline` stopped after a setup refocus and remains in safety reporting. `pilot*` phases are development checks, excluded from full-suite rates. All results and raw private recordings remain under `runs/`; deterministic input probes are under `diagnostics/`.

One attempt per task does not prove that a passing task is reliable on repetition. The final full rerun must use the same task definitions, starting conditions, model, effort and limits, and must report regressions as well as fixes. Do not combine successful retries into a replacement baseline.

The report includes handler time separately from total agent-run time. Remaining time includes model inference, provider/CLI waiting and orchestration; it is not a direct measurement of pure inference. Failed actions can return successful acknowledgements, so error flags alone are insufficient for classifying recovery time.

Phase names must be new by default. Existing phases are rejected before desktop access. Use `run_suite.py phase-name --resume` only to explicitly reuse completed results and continue missing tasks; matching source hashes and variant are still required. Each invocation is recorded in `invocations.jsonl`.
