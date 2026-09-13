# Hypr-use Computer Use MCP

**September 12 correction:** This implementation targets the older ten-tool API. Reports from September 5–10 show a newer `unified-computer-use` plugin exposing a JavaScript `cua` interface through `cua_repl/js` and `cua_repl/js_reset`. It is not yet compatible with that newer model-facing surface. See [the collected current API](../research/2026-09-12/unified-api.md), now verified against bundled declarations and MCP discovery.

A stdio MCP server using the macOS Computer Use vocabulary with the existing Hypr-Agent-Portal backend. It calls no model API and needs no API key.

Ten tools: `list_apps`, `get_app_state`, `click`, `perform_secondary_action`, `set_value`, `select_text`, `scroll`, `drag`, `press_key`, `type_text`.

## Run

From the current Hyprland desktop session:

```sh
python3 /home/anoromi/code/experiments/hypr-use/mcp/run-local.py
```

This machine's launcher uses the existing Nix runtime. A portable installation can run `server.py` using Python with the portal's dependencies. The native Hyprland plugin must already be loaded for desktop operations. The launcher does not load plugins, launch applications, change focus, or enable accessibility. AT-SPI must be enabled for accessibility operations; see `../testing/ACCESSIBILITY.md`.

`codex-config.toml` contains a ready-to-merge configuration under the server name `computer-use`, including the user-requested full-permission mode. It has **not** been installed into your global configuration. Full mode is owner configuration: tool calls cannot escalate permission. Existing explicit app restrictions, identity validation and compositor guards still apply. With no environment override, the backend retains its standard permission mode. Set `HYPR_AGENT_PORTAL_PERMISSION_MODE=read-only` for observation only. The adapter retains backend discovery filtering and routes every action through backend `handle()` and its policy/audit/lease checks.

`HYPR_USE_APP_ALIASES` is a JSON string mapping names to Linux app selectors. Otherwise `app` is passed through unchanged. `HYPR_USE_COMMAND_MODIFIER=ctrl` (default) translates Mac `super`, `cmd`, and `command` chord modifiers to Linux Control; `super` preserves the Linux Super key instead. This is a configurable shortcut approximation, not a guarantee that every Mac shortcut has a Linux equivalent.

## Contract evidence, checked September 12, 2026

[OpenAI's current docs](https://learn.chatgpt.com/docs/computer-use) mention GPT-6 Astra and say its plugin setup, OS permissions and app controls are the same. They do **not** publish a versioned tool manifest. A model release alone does not establish a tool-schema change.

The strongest tool inventory found is [macuse's direct native-client investigation](https://github.com/fitchmultz/macuse/blob/447df5214c143c7e88e644295451fc81fee71d70/docs/reference/codex-computer-use-external-harness.md). It reports an August 17 spot-check of ChatGPT build 6662, Computer Use plugin 1.0.1000717, client 26.727.1000550: ten computer-use tools. Its [upstream argument whitelist](https://github.com/fitchmultz/macuse/blob/447df5214c143c7e88e644295451fc81fee71d70/extensions/codex-computer-use-modules/upstream-tool-args.mjs) separates native keys from wrapper-only approval, safety-note and target-alias arguments.

The [open-codex-computer-use clone](https://github.com/iFurySt/open-codex-computer-use/blob/386a260d1ab8b690adbbb27f7471595cf0c2b752/packages/OpenComputerUseKit/Sources/OpenComputerUseKit/ToolDefinitions.swift), updated September 10, still exposes nine tools, omitting `select_text` and adding its own `click_method` and snapshot limits. We do not copy those extensions into the compatibility contract.

`tools.json` is a **reconstructed compatible schema**, not a captured September native manifest: names and argument keys follow the native-client bridge; types/required fields combine its wrapper and the clone's declarations. Descriptions and annotations accurately describe Linux behavior. Exact newest native schema, error text, result text formatting and Astra-specific changes remain unverified. Sources are cloned under `../research/2026-09-12/`.

## Behavior and limits

- `get_app_state` returns the portal's screenshot and AT-SPI tree. Images, structured content, errors and metadata pass through unchanged. Accessibility coverage varies by app. Tree IDs and screenshot coordinates are not macOS AX IDs or global desktop coordinates.
- `list_apps` lists running Linux windows/apps, without Mac usage history. `get_app_state` does not automatically launch a missing app. App launch is not one of the ten native tools.
- `select_text` uses AT-SPI Text selection/caret APIs, refreshes and rebinds explicit element IDs, validates window/process identity, and arms the related-window guard before mutation. With no element ID it uses the focused editable text node inside the bound app window. Prefix/suffix match immediately adjacent context; ambiguous/missing text fails. It verifies resulting selection/caret offsets. Unsupported apps return an error. No pointer or focus-request fallback is used.
- Existing click, key, typing, scroll and drag behavior remains the portal implementation. This adapter does not prove that every app/dialog can operate without refocus. The previous GTK background fixture passed; LibreOffice launch and keyboard-triggered dialog paths still need further same-desktop tests. New selection logic has unit and routing tests, not a live desktop test.
- Recording (`event-stream`, three tools) and computer history (`computer-history`, five tools) are separate native servers; this implementation does not provide them.
- Requests execute serially. Cancellation notifications reach the backend between operations; they do not interrupt an in-flight primitive. No model-turn session reset is imposed by this adapter.

## Verify without touching desktop windows

```sh
python3 -m unittest discover -s hypr-use/tests -p test_macos_compat.py
```

`regression-results.json` records the existing backend regression run. `stdio-smoke.json` records startup, tool discovery and malformed-request checks. No GUI actions are performed by these checks.
