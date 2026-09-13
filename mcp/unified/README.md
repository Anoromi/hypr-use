# Unified Hypr-use MCP

`node server.mjs` retains the three tools from the inspected OpenAI unified plugin: `js`, `js_reset`, `turn_ended`. It implements the native-app `cua` surface over Hypr-Agent-Portal. No model API calls or API key are needed by the server.

```toml
[mcp_servers.cua_repl]
command = "node"
args = ["/home/anoromi/code/experiments/hypr-use/mcp/unified/server.mjs"]

[mcp_servers.cua_repl.env]
HYPR_AGENT_PORTAL_PERMISSION_MODE = "full"
HYPR_AGENT_PORTAL_APPROVAL_POLICY = "never"
```

MCP clients may filter inherited environment variables: put owner permission settings explicitly in the server's `env` table. Full mode does not disable process identity, confinement, lock or compositor workspace guards. Use `standard` or `read-only` instead when desired. Do not set clipboard permissions to `all`; individual accepted values are `read,write,paste_text,paste_file,paste_image`, and full mode already supplies its defaults.

The launcher uses this project's existing Nix runtime and installed session environment. The matching native Hyprland plugin must be loaded. AT-SPI accessibility must be enabled for semantic actions. All app operations pass through the portal's policy entry point.

```js
let app = await cua.getApp("zen-beta");
await app.pressKey("ctrl+l");
await app.typeText("https://www.google.com");
await app.pressKey("Return");
await app.getAXState();
```

App methods: `getAXState`, `getScreenshot`, `getAXStateAndScreenshot`, `click`, `drag`, `scroll`, `pressKey`, `typeText`, `paste`, `setValue`, `selectText`, `performSecondaryAction`. `cua` provides `getApp`, `listApps`, `getState` and `initialize`. Observations emit themselves by default. `emit:false` suppresses output; `disableDiffing:true` requests a complete tree. `compactGeometry:false` retains verbose frame labels; the default uses lossless `[x,y,width,height]` frame arrays. Element indices are numbers; coordinates are `[x,y]` relative to the screenshot.

Bindings persist and can be redeclared. Top-level await and ordinary JS control flow are supported. Imports and direct filesystem/network/process APIs are not exposed. This is not a security boundary against hostile JavaScript; authority is enforced by the backend and owner configuration. Timeout/reset terminates the worker process group; a dispatched OS action cannot be undone. Host `turn_ended` notifications clean up sessions and are deduplicated per session/turn.

Differences from the inspected Mac API: only running apps are supported, inventory uses qualified Linux window IDs, only plain-text paste is implemented, browser-provider methods are absent, click count is limited to 1–3, and execution timeout is capped at 300 seconds. The JS worker's synchronous-code timeout is one second to prevent a loop from blocking reset. Native Zen is controlled through its app interface. Neither API shape nor passing unit tests proves that every application can operate without refocus.

`HYPR_USE_APP_ALIASES` accepts a JSON map of app names to Linux selectors. `HYPR_USE_COMMAND_MODIFIER=ctrl` translates Mac super/cmd/command chords; set `super` to retain that modifier. `HYPR_USE_WIRE_LOG` and `HYPR_USE_PORTAL_LOG` enable recordings; these include UI text and images and should remain private.

Tests: `npm test --prefix hypr-use/mcp/unified`. Recorded real-agent suite: `testing/unified-benchmark/run.py`, with separate Codex CLI processes, GPT-6 Astra, compositor event monitoring and per-operation timings.

The adapter returns acknowledgements after mutations. Call `getAXState()` when the agent needs a new observation. AX-index actions refresh the tree and strictly rematch the selected element before dispatch, so an old index cannot silently select a different element. Screenshot-only calls capture fresh pixels without scanning AX or menus. Combined observations collect both. Input identity checks and background session guards still run. Editable-entry and cell clicks can use a guarded pointer even when addressed by an AX index. `selectText()` focuses the widget within the background window before selecting.

The current key-event `typeText` implementation uses the portal's supported key map. Use explicit plain-text `paste` for text the key map cannot represent. Hidden-browser document selection falls back to a title match when AT-SPI omits SHOWING; duplicate document titles can remain ambiguous.

Benchmark evidence and the independent review live under `testing/unified-benchmark/`. The valid baseline combines `astra-baseline` tasks01–17 and `astra-baseline-calc` tasks18–24; `astra-optimized` repeats all 24. The latest fixed phase combines `astra-fast` 01–22 and `astra-fast-completion` 23–24; supplemental Save recovery and native-resize checks remain separate. Earlier Calc scope trials and Sol setup attempts are excluded. `review.json` records reviewed outcomes separately from automatic assertions. `report.py` builds the private HTML report, including exact JS calls and nested timings.

Post-benchmark corrections are recorded separately. An automatic semantic click may recapture once on a pre-dispatch title-only mismatch, then requires a unique enabled role/name/action match and revalidates the qualified process/window. A dispatched action is never automatically repeated or converted into a pointer fallback. Click sessions clean up on rejected paths. Key-event `typeText` skips spreadsheet-paste preparation, which previously injected Escape when typing a long path into a file chooser.

Calc grid coordinates now use matching horizontal and vertical scrollbar wrappers to measure the GTK/VCL translation, including a measured zero offset. Other layouts retain the existing fallback. Long batches and complex formatting/chart editing still need benchmark evidence. Explicit paste still uses the legacy grid preparation heuristic; long text in dialog fields should use key-event `typeText` or `setValue` until that heuristic is narrowed.

Control commands now run through a resident Python interpreter and direct Hyprland IPC, avoiding per-command Python and hyprctl launches. Set `HYPR_USE_FAST_CONTROL=0` to disable this transport. Each transaction retains its own EOF-framed socket; this is not a persistent compositor connection. Configuration discovery is cached for five seconds.

Post-action dialog protection retains its 400 ms interval. A compositor event observer replaces repeated polling; observer failure restores the original polling path. Native early-map protection remains enabled. Global-menu service discovery uses a 60-second cache, and process/service and tree-path discovery use two-second caches. Menu item state is still read fresh. AT-SPI scans still use isolated child processes.

Screenshot downsampling now uses GdkPixbuf when available. The original Python implementation remains the fallback; `HYPR_USE_NATIVE_RESIZE=0` disables the native resizer. Both paths retain screenshot dimensions and coordinate mapping, but their bilinear filters can produce slightly different pixels. The final native-resize change has separate direct and Astra validation after the fixed 24-task comparison.

AX updates now choose the shorter of a full tree and a diff. Pure embedded-object placeholder values are omitted; readable text and element indices remain. EditableText interface support alone does not mark a node editable: the AT-SPI EDITABLE state must also be present. Firefox exposes that interface on tabs and buttons too. See `testing/unified-benchmark/readiness/` for controlled experiments and replay measurements.

Sampled Codex model-facing rollout outputs exclude the timing metadata that remains in wire recordings. We retain those timings and do not count metadata removal as a context-token optimization. In that earlier phase, neither 1.2-second pauses nor main-surface keyboard routing alone solved browser readiness. The later 50-task investigation below adds client input-order and sequence fixes.

Earlier automatic click routing retained the EditableText-interface check for guarded pointer input. The current facade defaults AX-index clicks to native pointer input. Correcting editability metadata must not silently enable AT-SPI activation: a live Google suggestion test showed that its semantic action can activate the root Zen window despite the related-popup guard. The test stopped and the foreground was restored. Explicit secondary/AT-SPI actions retain this known background-use limitation.

### Background AX freshness

AX-only observations wake the bound window's Wayland frame callbacks before scanning, using the native screenshot dispatcher's prepare-only branch and a 120 ms settling interval. This produces no screenshot and does not focus the target. Native lock/privacy checks still apply. Without preparation, Chromium on a hidden workspace retained a closed tab in its accessibility tree and agents misclassified successful restoration as failure. The interval matches screenshot preparation; it does not prove every application's updates have completed.

Six fresh Astra xhigh restore-tab runs and context audits are recorded under `testing/unified-benchmark/astra-restore-clean-*` and `astra-restore-ax-fix-*`. Median total time changed from 70.19 s to 25.35 s. Each fixed run used two JS calls, no screenshots and no refocus. The earlier 22.30 s preflight-warmed result is excluded. Regression checks: `python3 testing/test-ax-frame-preparation.py` and `node --test mcp/unified/test.mjs`.

### 50-task reliability investigation

The suite in `testing/reliability50/` covers native GTK, Chromium navigation and web forms, Calc and Writer. It records fresh Astra xhigh CLI threads, independent initial/final checks and foreground-window events. The completed baseline passed 43/50. Development reruns of failed cases are separate from full-suite comparisons.

Current shared changes normalize mixed web-document AX scales, summarize blank-text grid cells while retaining reported values, expose setter interfaces, check numeric setters by reading their value back, and use native pointer clicks. The native plugin delivers target-client keyboard enter before pointer activation and correctly maps F11/F12. Neither change assigns global seat keyboard focus.

`typeText` and space-separated `pressKey` sequences use one native keyboard transaction, avoiding a blur between characters. Each call supports at most 4096 key events; use explicit plain-text paste for longer or unsupported text. Individual `pressKey` calls are separate transactions. Shortcut-only Ctrl+L navigation in a fresh inactive Chromium window still fails a diagnostic probe; clicking the address bar first works. Other applications and XWayland need their own coverage.

The sequence implementation requires `testing/plugin-reliability-sequence-result/lib/libhypr-agent-portal.so` or a newer matching build. It is loaded for this compositor session only. Regression checks are `node --test mcp/unified/test.mjs`, `python3 testing/reliability50/test_general_fixes.py`, `python3 testing/reliability50/test_function_keys.py`, and `python3 testing/test-ax-frame-preparation.py`.

### API cost experiments

The unified adapter now skips the portal's separate D-Bus global-menu discovery. The JS API exposes AT-SPI elements and never returned that menu collection or offered `activate_menu_item`; visible menus in the AX tree still work. `HYPR_USE_GLOBAL_MENU=1` restores discovery for controlled comparisons. Ordinary portal clients retain their original behavior. Input identity rematching, frame preparation and popup guards are unchanged.

Focused before/after Astra runs and controlled action probes are described in `testing/reliability50/api-performance.md`. The 50-task suite was not rerun for this experiment.

The API instructions now explain the existing keyboard batching support. For a selected spreadsheet cell, `await app.typeText("Total\n=B2*C2\n=B3*C3\n=B4*C4\n")` sends one transaction. Newlines press Enter and tabs press Tab; they are not clipboard insertion. Batch only when the next action does not depend on an intermediate observation. There is no automatic conversion of separate awaited calls into a batch.

`pressKey` accepts both `Down` and `ArrowDown` spellings, likewise Up/Left/Right, including modifier chords. This prevents browser-style arrow names from reaching the native dispatcher as unknown keys.

### Common workflow tools

Four additional MCP tools are available alongside `js`: `fill_form`, `replace_text`, `navigate`, and `wait_for`. The same implementations are exposed as `app.fillForm(options)`, `app.replaceText(options)`, `app.navigate(options)` and `app.waitFor(options)`; omit `app` from the arguments when using an already bound JS app. No table-writing helper is added.

```json
{"app":"hypr-use-r50-browser","fields":[{"name":"Full name","value":"Grace Hopper"},{"name":"Email","value":"grace@example.test"}],"submit":{"name":"Save profile"}}
```

Pass that object to `fill_form`. Selectors use an exact accessible name and optional role; ambiguous names fail. String values edit text/value controls; boolean values set checkbox state. Dropdown selection is not included. Text methods apply only to string fields. Default field input uses a supported setter, otherwise native keys, verified by AX readback; explicit `keys` and `paste` methods are available.

`replace_text` takes `target`, `text`, optional `method` and boolean `submit`. It replaces the entire field, not every matching word in a document. Native keys are the default. `navigate` takes an http(s) `url`, optional `new_tab` and an `address` selector when its default address-bar names do not match the browser. Navigation returns submitted status; use `wait_for` for a page condition.

`wait_for` takes exactly one of `target` with optional exact string `value` or boolean checked state, AX substring `text`, or `dialog_title`, plus optional `timeout_ms` up to 30000. It returns the matching element index or related-dialog target where applicable. Observations are bounded polls with a 300 ms minimum interval between scans; an in-progress scan can exceed the deadline. Timeout returns an error.

Workflows validate arguments before mutations, retain ordinary portal identity and background checks, stop on the first error, and return completed-step timings. They are not atomic: completed actions remain applied. They reduce model/tool round trips; they do not remove per-action guard waits or automatically retry failed actions. Final AX is emitted once. Worker cancellation and timeout retain the existing partial-output behavior.

Tests: `node --test mcp/unified/test.mjs mcp/unified/workflows.test.mjs`. Fresh Astra test evidence is under `testing/reliability50/runs/workflow-tools-v1`.

Agent adoption: all four tools were used directly by fresh Astra CLI instances; seven focused runs passed with no refocuses. One old `selectText` call failed and the agent recovered using `replace_text`. See `testing/reliability50/workflow-tools.md`; no paired speedup is claimed.

Field selectors ignore same-name labels and match editable/value controls or text-entry roles, because Chromium can omit editability interface flags. Multiple matching fields remain an error; supply a role to disambiguate. Selection readback now allows 150 ms for asynchronous AT-SPI updates without repeating the mutation.

Target PID matching no longer requests every application name first. This avoids a blocked name query preventing access to a healthy target. `HYPR_USE_AX_DEBUG_STACK=1` enables a four-second stack dump in isolated AT-SPI children for private diagnostics; normal operation leaves it disabled.

Within a workflow, the latest preflight or verification snapshot is reused until another mutation. Each indexed action still performs the backend's fresh identity rematch. This avoids duplicate reads without weakening target checks.

`typeText(text,{replaceAll:true,submit:true})` can prepend Ctrl+A and append Enter in one keyboard transaction. Empty replacement clears the selected field. The 4096-key limit includes those extra keys. Workflow key input uses this path automatically where it fits; each complete transaction retains the ordinary popup guard.

Checkbox fields are clicked only when their checked state differs from the requested boolean, then verified. Repeating an already-satisfied checkbox operation performs no input. Mixed/unknown checkbox states fail before changing fields; AX reports mixed state explicitly.
