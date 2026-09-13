# Zen background input investigation

2026-09-07. Hyprland 0.56.2, Portal 0.4.0 at bc0b100. The real session uses Lua configuration and a keyd keyboard with `us,us,ua,ru`, variants `dvorak,,,`, active English Dvorak.

## Confirmed defects

1. **Lua failures were reported as success.** Portal's native callbacks return `{ok=false,error=...}`. Hyprland's `hl.dispatch` returns that table, but the IPC evaluator discards returned values. `hyprctl dispatch` therefore printed `ok` and exited zero even for an invalid guard action. The Python CLI trusted that exit code. This affected input errors and guard reporting. Reproduced without injecting input using an invalid guard probe. The local fix invokes `hyprctl eval` with an outer assertion on the dispatch result. The same invalid request now exits nonzero with its actual error. No native plugin change is needed.

2. **The documented `key` shortcut syntax was not parsed.** `press_key` advertises `key="ctrl+t"`, which Codex used. `key_from_args` split shortcuts only when supplied in `keys`. It passed the literal string `ctrl+t` as one native key name. After fixing error propagation, the identical MCP request exposed `unknown keyboard key`. The local parser now accepts shortcuts through either field and retains explicit modifiers.

3. **Symbolic input assumed QWERTY.** The native plugin now resolves the requested US symbol through the active xkb keymap and sends the matching keycode/layout group only to the target client. On this desktop, Ctrl+T maps to physical KEY_K in Dvorak. Numeric evdev codes retain their existing semantics. The user's layout is unchanged.

4. **Background screenshots were stale.** Hyprland sends normal frame callbacks to visible workspaces. Portal rendered the last submitted buffer of the off-workspace Zen window without keeping that client producing frames. Supplying frame callbacks revealed both earlier URL typing attempts concatenated in the new-tab prompt: input had reached the browser while screenshots concealed the changes. The local plugin now supplies callbacks to the selected surface tree for two seconds after input/capture. Target screenshot capture first requests preparation, waits 120 ms outside the compositor, then reads back. Preparation repeats normal screenshot privacy checks; its denial aborts capture. Timers stop on expiry, panic, lock, cancellation, or plugin unload.

## Verified result

An actual `codex exec` run used the confined MCP server to select the duplicated URL, type `https://google.com` with `method=keys`, press Return, and verify **Google — Zen Browser** at `www.google.com` in a new tab. This used the existing native Wayland Zen instance on workspace 3. All 100 focus samples during the final test remained `t3-code-alpha`, workspace 1. Clipboard access stayed disabled. No compositor focus/workspace dispatch or browser launch was used.

The earlier claim that the sidebar pointer path failed is withdrawn: stale screenshots made it look ineffective. Zen's new-tab prompt also retains the old page title until navigation, so title alone is insufficient verification.

A temporary delayed keyboard lease did not resolve the stale view and was removed. The final plugin retains upstream immediate target keyboard restoration. Target protocol tracing was removed; it is not present in the loaded build.

## Changes and checks

The complete patch is `testing/portal-background-fixes.patch`, including the new keymap resolver header. Apply it to upstream bc0b100. `plugin-live.nix` builds against the installed Hyprland 0.56.2 dependencies; the current build is `testing/plugin-fixed-result/lib/libhypr-agent-portal.so`. It is loaded for this compositor session only. No persistent Hyprland or global Codex configuration was added.

Validation: all 17 upstream Python scripts passed (the smoke script requires the MCP script argument); seven shortcut regression cases passed; native keymap tests cover Dvorak, QWERTY, punctuation, Return and Cyrillic fallback; screenshot preparation and denied-preparation regression tests passed. The final build also returned a fresh Google state through MCP after loading. Raw Codex output and focus observations remain in ignored `testing/live-session/`.

Limits: this validates one native Zen window and one desktop configuration. The 120 ms preparation delay is a best-effort redraw interval, not a guarantee that a slow application or page has finished rendering. The background frame pump currently serves one target at a time. Unicode typing, popup routing, overlapping agents and sustained concurrent physical input need further work. AT-SPI did not find Zen; this test used screenshots.

## Source references

- Portal: `scripts/hypr-agent-portalctl`, `dispatch`; `mcp/hypr-agent-portal-mcp.py`, `key_from_args`; `src/plugin/main.cpp`, `keyboardKey`, `KeyboardResourceTransaction`, `dispatchKeyboard`.
- [Hyprland IPC dispatch](https://github.com/hyprwm/Hyprland/blob/efb50993780079460b0cbed1363e2166a2de1d9f/src/debug/HyprCtl.cpp#L1126).
- [Hyprland Lua dispatch result handling](https://github.com/hyprwm/Hyprland/blob/efb50993780079460b0cbed1363e2166a2de1d9f/src/config/lua/bindings/LuaBindingsToplevel.cpp#L352).

- [Hyprland frame event routing](https://github.com/hyprwm/Hyprland/blob/efb50993780079460b0cbed1363e2166a2de1d9f/src/render/Renderer.cpp#L2207).
