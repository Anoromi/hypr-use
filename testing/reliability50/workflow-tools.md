# Common MCP tools: agent adoption

Added `fill_form`, `replace_text`, `navigate`, and `wait_for`, plus equivalent JS app methods. No table-writing tool. Existing low-level calls, permissions, identity rematching and background protection remain active. Helpers stop on error and report completed steps; they do not roll back or retry.

Seven fresh GPT-6 Astra xhigh CLI runs across six task definitions passed independent grading. Zero foreground refocuses. Raw threads, tool calls, handler timings and grades remain under `runs/workflow-tools-v1` and `runs/workflow-tools-v2`. `workflow-tool-results.json` summarizes them; `analyse_workflow_tools.py` regenerates it.

| Run | Seconds | Explicit new tools used |
|---|---:|---|
| Name edit | 22.44 | None; ordinary JS setter |
| Delayed dialog v1 | 60.03 | wait_for |
| Example navigation | 31.04 | navigate |
| Two-field profile and save | 37.45 | fill_form |
| Delayed dialog v2 | 69.38 | wait_for |
| Google in a new tab | 28.09 | navigate |
| Note edit and save | 48.26 | replace_text twice |

All seven new-tool calls succeeded. The note agent also tried the existing JS `selectText`, which failed because Chromium did not retain the requested selection. It recovered using `replace_text` and saved the independently verified result. Google grading showed both Google and the original Start tab remained open.

V2 removes a redundant address-bar click and emits the exact matched wait snapshot instead of rescanning after a match. A final validation-only correction rejects inherited object property names; its regression test passed after the live runs. `npm test --prefix mcp/unified` passes 15 tests covering validation, partial failures, selector ambiguity, bounded waits, snapshot consistency, protocol persistence and routing.

These are exploratory adoption tests, with a prompt that permits either MCP tools or JS and API instructions recommending common helpers. They are not paired speed measurements. Extra internal AX checks can cost time; the intended saving is fewer agent/tool round trips. A simple field task still chose its ordinary setter.
