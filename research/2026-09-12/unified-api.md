# Unified Computer Use API — September 12, 2026

We now have bundled API declarations, implementation code, the plugin manifest, and a real MCP discovery response. The compatibility target is **`unified-computer-use` → `cua_repl` → JavaScript `cua`**, rather than ten separately advertised desktop action tools.

## Evidence and scope

Source: [OpenAI-distributed ChatGPT package 26.908.40834](https://persistent.oaistatic.com/codex-app-prod/linux/deb/pool/main/c/chatgpt/chatgpt_26.908.40834_amd64.deb), HTTP Last-Modified September 11, 2026, 18:52:20 UTC. Download SHA-256: `da37b8e7bcefaaea019c478cacbe6c73ee1ddd15e0e1ebb3c7ef0a42dd818ac2`; it matches the independently recorded package pin in the inspected Linux port.

This is a **Linux distribution containing shared JavaScript and the Mac adapter implementation**, not a Mac execution test or proof that every Mac rollout contains identical bytes. Bundled versions: plugin `26.908.40834`, `@oai/cua` `0.2.4-premerge-pr-1459319-5451279f30a0`, `@oai/sky` `0.6.33-premerge-pr-1459319-5451279f30a0`. The package names include premerge labels; they are reported as found.

A September 11 [Mac/Astra reproduction](https://github.com/openai/codex/issues/44927) independently confirms the app-object interface, including `getApp`, `click` and `getScreenshot`, on desktop build 8576/helper 26.902.1000968. It does not establish an Astra-specific API change.

Local evidence:

- `package/usr/lib/chatgpt/resources/plugins/openai-bundled/plugins/unified-computer-use/.mcp.json`
- The same directory's `.codex-plugin/plugin.json` (lifecycle hooks).
- `package/usr/lib/chatgpt/resources/cua_node/lib/node_modules/@oai/cua/docs/tinysky-alt-core-cua-repl.md` (agent-facing documentation).
- That package's `dist/lib/js/oai_js_cua/src/tinysky_alt/types.d.ts`, `globals.js`, and `create_tinysky_alt.js` (declarations, surface selection and implementation).
- `node-repl-discovery.json`: actual initialize/tools-list exchange against the bundled executable. No JavaScript execution, desktop control, browser connection or app launch was requested.
- `unified-mcp-tools.json`: the three enabled tool schemas, filtered from that discovery response.
- `unified-api.d.ts`: the API declarations extracted from the bundled documentation for local reference.

## Structure

```text
Codex / ChatGPT model
  └─ MCP server: cua_repl
       ├─ js({code, timeout_ms?, title?})
       │    └─ persistent JavaScript environment
       │         └─ cua
       │              ├─ app/browser inventory and binding methods
       │              ├─ App → shared Target methods → native Sky service
       │              └─ Tab → shared Target methods + browser methods
       ├─ js_reset({})
       └─ turn_ended({...}) ← host lifecycle hooks
```

`click` and `pressKey` are JavaScript methods inside `js`, not independent MCP tools in this plugin. The lower-level native Sky layer still uses snake_case operations. Naming that lower layer as the model-facing contract was the mistake in our initial adapter.

## MCP tools

| Name | Arguments | Role |
|---|---|---|
| `js` | Required `code: string`; optional positive integer `timeout_ms`, and `title: string` of 1–80 characters | Execute code with top-level await. Default timeout 30 seconds. Bindings persist and may be redeclared. |
| `js_reset` | Empty object | Clear JavaScript bindings by resetting the kernel. |
| `turn_ended` | Required nonempty `hook_event_name`, `session_id`, `turn_id` strings | Notify trusted libraries of a completed/interrupted turn; duplicate session/turn notifications are ignored. |

The raw executable also advertises `js_add_node_module_dir({path})`; the unified plugin's `enabled_tools` excludes it. `turn_ended` carries empty UI visibility metadata and is wired to Stop, Interrupt and SubagentStop hooks. It is lifecycle plumbing, not an action the model must perform after every click.

The shipped `.mcp.json` is an app-managed placeholder (`enabled: false`, `command: node`, empty args), with a 120-second startup timeout and a 25,000-token JS output limit. It is not a standalone runnable configuration as shipped; the desktop host supplies runtime configuration.

## Top-level `cua`

| Method | Meaning |
|---|---|
| `getState({emit?}?)` | Inventory: `{apps, browsers, errors?}`. Browser entries contain tabs; inventory failures can be reported separately. |
| `listApps({emit?}?)` | App records: `id`, optional `displayName`, `isRunning`, `lastUsedDate`, `useCount`. |
| `getApp(app: string)` | Bind an app by name, path or bundle ID and emit its initial full AX state. Docs describe background launch if needed. |
| `getBrowser({id?, url?}?)` | Select a browser without creating a tab; show its first-use documentation. |
| `listBrowsers({emit?}?)` | Browser IDs and optional name, family, type (`iab`, `extension`, `cdp`), profile and metadata. |
| `createBrowserTab(browserId, url?, {visible?, sessionName?}?)` | Create a tab and emit initial AX state. |
| `getTab(id, {browser?}?)` | Bind a tab and emit initial full AX state. |
| `listTabs({browser?, emit?}?)` | List tab IDs, browser IDs and optional provider ID/title/URL. |

Implementation/declaration extras: `initialize()` aliases `getState()`, `rewriteDocumentation()` re-emits previously displayed documentation, `browsers` exposes the browser provider, and `computer` references the lower-level Sky client. These are distinct from the short public workflow documented above.

Available methods depend on `CUA_REPL_ENABLED_SURFACES=browser,computer`. A browser-only session can lack `getApp` entirely. The shared implementation explicitly requires a `mac` native target for app bindings. Its inclusion in a Linux package is not evidence that native Linux support is enabled.

## Shared `Target`: all 12 methods

Both an App and a Tab implement these methods. Each call returns a Promise.

| Method | Return / arguments |
|---|---|
| `getAXState({emit?, disableDiffing?}?)` | Accessibility text string. |
| `getScreenshot({emit?}?)` | Image bytes (`Uint8Array`). |
| `getAXStateAndScreenshot({emit?, disableDiffing?}?)` | `{state: string, screenshot?: Uint8Array}`. |
| `click(target, {mouseButton?, clickCount?}?)` | Target is a numeric AX index or `[x,y]`. |
| `drag([fromX,fromY], [toX,toY])` | Coordinate drag. |
| `pressKey(key)` | xdotool-style string, including combinations. |
| `scroll(target, direction, pages?)` | Numeric AX index or `[x,y]`; full direction names or `u/d/l/r`. |
| `typeText(text)` | Literal keyboard text. |
| `paste(text, {format?}?)` | Format is `text`, `md`, or `html`; default text. |
| `setValue(elementIndex, value)` | Set an accessibility element's value. |
| `selectText(elementIndex, text, {prefix?, suffix?, selectionType?}?)` | Selection type: `text`, `cursor_before`, or `cursor_after`. |
| `performSecondaryAction(elementIndex, action)` | An action actually exposed by that element. |

Input methods are declared `Promise<void>`; observations provide the resulting evidence. Mouse buttons accept full names or `l/r/m`. AX element indices are **numbers**, unlike the strings in the older MCP contract.

Tab additionally exposes `id`, `goto(url)`, `back()`, `forward()`, `reload()`, `close()`, `markDeliverable()` and `markHandoff()`. Its full type also intersects with the underlying BrowserTab type. Browser-specific APIs, including Playwright, are documented on selection; they are not native-app methods.

## Observation, performance and output semantics

1. Bind an app/tab; the initial AX observation is emitted automatically. The native wrapper binds subsequent calls to the app identifier returned by the native state response.
2. Run deterministic actions, then read AX state before deciding the next action. Multiple actions plus their resulting observation can share one `js` call.
3. AX output normally uses diffs. `disableDiffing: true` asks for a full tree. Element indices must come from current observations; screenshot-only observations require a fresh full tree before relying on indices again.
4. Observation/discovery methods both return values and emit model-visible output by default. `emit: false` suppresses that output, but not first-use documentation. Re-emitting a default observation duplicates output.
5. `nodeRepl.write` and `nodeRepl.emitImage` are the runtime output helpers. Returned bytes and emitted images are different parts of the contract.
6. The docs specify built-in observation waits. They discourage adding sleeps before state reads; exact wait duration is not specified by this API.
7. **Mac implementation detail:** all three observation methods call native `get_app_state`. `getScreenshot` obtains its screenshot URL from that response and emits only the image. Thus screenshot-only model output is not proof of screenshot-only backend work. Browser observations use distinct `state`, `screenshot` and `both` modes.
8. Native paste restores the prior clipboard according to the bundled docs. Browser paste does not, and Markdown is inserted as plain source there.

## Native translation relevant to Hypr-use

| Unified method/option | Native Sky operation/field |
|---|---|
| `getApp`, AX/image observations | `get_app_state` |
| `disableDiffing` | `disableDiff` |
| numeric click/scroll target | `element_index` |
| coordinate click/scroll target | `x`, `y` |
| `mouseButton`, `clickCount` | `mouse_button`, `click_count` |
| `selectText(..., {selectionType})` | `select_text`, `selection_type` |
| `pressKey`, `typeText`, `setValue` | `press_key`, `type_text`, `set_value` |
| `performSecondaryAction` | `perform_secondary_action` |
| `paste` | `paste` with text and format |

Our existing portal is still useful as the executor. Matching the current interface requires a persistent JS layer, app handles, numeric element IDs, these observation/output rules, and lifecycle notifications. Simple tool renaming is insufficient. Rich paste and automatic background launch are additional behavior gaps; app identity and no-refocus guarantees still need our own compositor enforcement.

A September 8 [native Mac report](https://github.com/openai/codex/issues/43859) shows that the public app selector does not expose PID/window targeting. We should retain our stronger internal identity binding without pretending those selectors are part of the upstream API.

## What remains unverified

- Running this full plugin on a Mac with the latest account-specific surface flags.
- Exact Mac rollout equivalence to the inspected shared package.
- Complete browser-specific provider API and lower-level Sky API (outside the core native-app compatibility target).
- Native wait timings, background input behavior and lifecycle cleanup effects at runtime. The discovery probe tested only initialize/tools-list.

No server implementation was changed during this collection.
