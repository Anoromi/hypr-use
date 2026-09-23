# Native interface evidence from September 5–12, 2026

Checked September 12. GitHub creation/update timestamps were verified through its API; raw responses are in `recent-native-reports.json`.

- [September 10: Paseo issue 4656](https://github.com/getpaseo/paseo/issues/4656), created 12:48 UTC: ChatGPT 26.903.61454/build 8378; unified-computer-use plugin; actual MCP errors identify `cua_repl/js`, argument `code`, and `cua_repl/js_reset`. Calls include `cua.getState()` and `cua.createBrowserTab("chrome", url, {sessionName})`. This is an operator's first-hand reproduction, not an OpenAI specification.
- [September 5, updated September 6: Codex issue 43047](https://github.com/openai/codex/issues/43047): native macOS `cua.getApp(bundleId)` followed by `app.drag([x,y], [x,y])`. Client/service 26.831.1000926; desktop 26.901.41600/build 7982. Describes native app input, distinct from browser APIs.
- [September 8 follow-up: Intel Mac report](https://community.openai.com/t/intel-mac-computer-history-and-appshots-fail-because-the-managed-computer-use-service-is-missing/1390702): native API calls `cua.getState()` and `cua.getApp(...)` are present but the service fails to start. Explicit runtime surface flag `CUA_REPL_ENABLED_SURFACES=computer`.
- [September 5: Windows Codex issue 42941](https://github.com/openai/codex/issues/42941): unified plugin 26.901.41600, Sky 0.6.26. Lists browser facade methods and a missing Windows native service. Its snake_case native methods must not be assumed to describe the Mac app-object contract.

These reports demonstrate a newer model-facing JavaScript interface than the August ten-tool MCP inventory. They do not provide the complete September MCP manifest or all Mac app method signatures. They also do not establish that Astra caused the change, or that the older MCP interface has been removed.

The local MCP implementation remains an older-API adapter. Matching the newer surface requires the actual `cua_repl` schemas, runtime API/type declarations and object/session behavior before implementing a compatibility facade. No implementation changes were guessed from these partial reports.
