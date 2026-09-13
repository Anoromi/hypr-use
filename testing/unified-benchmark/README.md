# Unified computer-use benchmark

Every official task uses a fresh `codex exec` process with `gpt-6-astra`, high reasoning, only the unified MCP server, a 180-second task limit and a 30-second default JS limit. The task prompts are in `tasks.json`.

The valid comparison is `astra-baseline` tasks01–17 plus `astra-baseline-calc` tasks18–24, against all24 `astra-optimized` tasks. Earlier Sol and Calc-scope setup attempts are excluded. `astra-recovery` and `astra-save-recovery` are separate follow-ups after additional fixes. Do not merge their passes into the original20/24 outcome.

Each task directory contains its prompt, execution configuration, timestamped Codex events, MCP wire calls, portal timings, final answer and result. A `review.json` records independent evidence review. Process exit zero does not prove success. Calc tasks depend on earlier task state. Source snapshots and hashes identify each implementation.

`setup.py <profile-suffix>` launches a GTK fixture and private Calc on workspace902 without initial focus. It refuses to launch while another LibreOffice process has a window. Zen uses the existing background browser. `run.py <new-phase> [task-ids...]` runs selected tasks sequentially. Use a new phase name: the runner does not resume or append its results safely.

The monitor combines compositor events with100ms polling and stops the runner if an agent target becomes foreground or the observer fails. This tests refocus under the recorded rules, not every kind of user interference. A user switching to a target also stops the run. Do not run desktop mutations or latency probes concurrently with a model phase.

`analyse.py <phase>` builds metrics. `report.py <phases...>` creates the private HTML artifact with exact calls, images and timings. `verify-ods.py <path>` checks saved spreadsheet XML. `probes.py` runs five direct fixture operations per category after model phases; blocked calls are failures, not latency successes.

For cleanup, preserve the workbook first and terminate only processes whose command lines contain this fixture path or the private Calc profile. Disable the temporary rule with:

```sh
hyprctl eval 'hl.window_rule({name="hypr-use-benchmark",match={class="^(hypr-use-bench|libreoffice.*|soffice)$"}}):set_enabled(false)'
```

Hyprland merges named rule redeclarations. Globals created by one `hyprctl eval` are not available in the next call. Keep user windows and tabs intact. Recordings contain desktop text and screenshots; the report belongs on the private artifact server.
