# Local Portal test

Built Portal 0.4.0 from bc0b100719dafb8bdf893ace4d3be1d78b1a0876 against the installed Hyprland 0.55.4 Nix packages. The native compatibility changes are on vendor branch `local/hyprland-0.55.4`, also saved in `hyprland-0.55.4.patch`. They restore 0.55 window/workspace and animation APIs while retaining the latest keyboard resource routing and target identity checks.

## Run

From `hypr-use`:

```sh
nix build --file testing/plugin.nix --impure --out-link testing/plugin-result -L
nix build --file testing/runtime.nix --impure --out-link testing/runtime-result
python3 testing/start-test.py
python3 testing/run-codex-test.py
python3 testing/stop-test.py
```

The Nix expressions intentionally use the same local nixpkgs store path as the installed Hyprnav build wrapper. They are machine-specific. On a fresh vendor clone, apply `testing/hyprland-0.55.4.patch` once before building. Do not apply it again to the already modified checkout.

The plugin is `testing/plugin-result/lib/libhypr-agent-portal.so`. This procedure loads it only into the disposable compositor, never the user's desktop. Nothing is added to Hyprland's persistent config or global Codex config.

## Test environment

Cage runs with a headless backend and provides a render allocator for a separate Hyprland 0.55.4 process. Cage's xdg-shell version is raised from 5 to 6, supported by its wlroots 0.20 dependency and required by Aquamarine 0.12.1. Hyprland uses an explicit headless TEST output. Its libseat backend is deliberately invalid, preventing it from acquiring the real display/input seat. XWayland is disabled.

The test has a private runtime directory and session D-Bus. A small Wayland client creates a virtual pointer and a keyboard with the standard US keymap. It sends no input events. GTK runs two separate native Wayland processes: a target entry/button app and a foreground focus sentinel. Portal performs the actual clicks and typing through MCP. This isolates the test desktop, but is not a filesystem or network sandbox.

The MCP wrapper checks the test socket exists, confines actions to `fixture.py`, grants only that app full input permission, and disables clipboard access. Codex uses five allowed tools, with shell tools disabled and user-configured MCP servers disabled for this invocation. The test server's tools are preapproved for this authorized disposable test. Existing user configuration is not edited. See [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

## Evidence

- `build.log`: native Nix build.
- `offline-tests.log`: all 17 upstream Python test scripts passed with inaccessible desktop endpoints.
- `codex-test.jsonl`: actual Codex MCP calls and responses, including images.
- `session/fixture-state.json`: independent app-side text/button result.
- `focus-observations.jsonl`: sampled active window, workspace, and cursor.
- `session/`: process IDs, logs, and private connection environment.

Generated logs and session data are ignored by git. `stop-test.py` signals only recorded process groups whose command lines match the test. Cage has a one-hour lifetime; use the stop script to release all test processes.

An isolated test does not establish safety for existing applications on the real desktop, concurrent physical input, popup routing, or every 0.55 API adaptation. Those need separate testing before loading this plugin into the user's compositor.

## Observed result

The native plugin loaded successfully. Codex read screenshots and typed `portal test` into the unfocused native GTK app using `method=keys`. Its first button click used the wrong Y coordinate. A follow-up Codex run with verified screenshot coordinates clicked the button successfully; the app independently wrote `{"text":"portal test","confirmed":true}`. The focus sentinel remained foreground, the cursor stayed at 640,400, and workspace 1 stayed active. See `test-results.json`.

AT-SPI discovery did not find the GTK app in this private D-Bus setup, so this validates screenshot-based interaction. It does not validate accessibility-based targeting. The test desktop was stopped after collecting evidence.

## Real Zen test, 2026-09-07

**Passed after local fixes on Hyprland 0.56.2.** Codex opened Google in a new tab of the existing native Wayland Zen instance through MCP. All 100 final-test focus samples remained on T3 Code, workspace 1; Zen stayed on workspace 3. Clipboard was disabled.

The initial failure combined swallowed Lua errors, shortcut parsing, QWERTY assumptions, and stale off-workspace screenshots. See [the investigation](ZEN-DEBUG.md). The complete patch is `portal-background-fixes.patch`; the current loaded build is `plugin-fixed-result/lib/libhypr-agent-portal.so`. No persistent compositor or global Codex configuration was added.

Build with `nix-build testing/plugin-live.nix -o testing/plugin-fixed-result`. This expression pins the current local Nix package source and compiles the modified 0.56.2 vendor worktree. Rebuild against the running compositor after upgrades. The Python CLI preparation change and native plugin must be deployed together.

Additional checks: `python3 testing/test-portal-shortcuts.py`, `python3 testing/test-background-capture.py`, and `nix-build testing/test-keymap.nix -o testing/keymap-test-result`.

## Configurable permissions and recorded Calc test

[Permission configuration](PERMISSIONS.md) documents the startup profiles and
independent confirmation setting. `portal-permission-modes.patch` contains the
policy, docs and regression tests. It applies separately from the native/input patch.

The ongoing Calc test is stored in ignored `calc-session/`. `run-calc-test.py`
starts a persistent Codex thread; `resume-calc-test.py` continues it and records
operator interventions. `publish-calc-replay.py` extracts its returned images
and publishes a step-by-step replay. `verify-calc-workbook.py` independently
checks the GUI-saved ODS against the source CSV without modifying the workbook.
