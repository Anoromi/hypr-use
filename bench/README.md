# cua benchmark

This suite runs the same 90 desktop tasks in two distinct modes. It contains
90 seeded tasks: 15 T1, 20 T2, 20 T3, 15 T4, 10 T5, and 10 T6 tool-stress tasks. GTK 4 fixtures
write atomic JSON state after every interaction. Graders read that state and the transcript;
they never trust a model's success claim.

## Commands

```sh
./bench list --tier T1
./bench run --tier T1 # both modes by default
./bench run --mode scripted --tier T1 --task t1-01-button
./bench run --mode agentic --tier T1 --model gpt-5.6-sol --runs 3
./bench run --mode both --tier T6
./bench tools --tier T1 # compatibility alias for scripted mode
./bench real-list
./bench real-apps --task real-nautilus-folder
./bench report results/<run>
```

Scripted mode starts the lab, seeds each scenario, and runs its fixed command sequence through a
persistent unified MCP process. It is a deterministic tool baseline, not model performance.
Agentic mode launches a fresh Codex CLI process using the existing login token. It uses no paid
Claude invocation or API key. Both modes use the same task catalog, state grader, and recording
contract. T6 covers rapid actions, 1,000-row AX latency, repeated launch,
MCP restart, parallel sessions, text fidelity, index and pixel clicks, and target tracking.

Agentic runs give Codex only the CUA MCP tools. Each run uses an ephemeral session, read-only sandbox,
no shell tool, only the benchmark MCP, and an operational timeout. There is no step limit penalty.
The task instructions identify the seeded primary-window suffix, explain how to bind related fixed-title
windows, list the supported CUA methods, and direct the agent to use bounded `waitFor`/`getDialog` waits
instead of unavailable JavaScript timers.
Artifacts use `results/<run>/<mode>/run-N/<task>/`; every task directory contains `desktop.mp4` alongside
its result and evidence files. `summary.json` declares the mode, driver, and model (or `null`).

Set `HYPR_LAB` if `hypr-lab` is not on `PATH`. The lab seed contract must expose
`BENCH_STATE_DIR`; `hypr-testbed/scenarios/common.py` resolves every catalog seed and launches the
needed fixtures. `bench real-apps` executes the opt-in Nautilus, Zen, terminal, and calculator
workflows from `real-tasks.json` through MCP, with isolated profiles or paths and state graders.
`bench real-list` reports missing executable prerequisites. These tasks remain outside the
comparable 90-task fixture score. The final pinned run in `results/real-final2` passed Calculator;
Nautilus and terminal reported `wrong_action`, while Zen failed app binding with `appNotFound`.
These are recorded failures, not skipped or substituted results.

Reports default to `~/Artifacts/cua-bench/<run>/`. Paired task rows show scripted and agentic
completion, steps taken, and video evidence side by side. Completion rates and mean steps remain
separate by mode. Step count means MCP tool calls for agentic runs and predefined actions for scripted
runs. Other efficiency and cost fields may remain in raw evidence but are not benchmark metrics.
The older oracle baseline files predate the shared evaluator and remain historical evidence.
