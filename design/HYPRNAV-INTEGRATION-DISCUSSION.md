# cua MCP + hyprnav: discussion notes

Date: 2026-09-19, updated 2026-09-20. Status: discussion, decisions below.

## Decided so far

| Topic | Decision |
|---|---|
| Placement | Live compositor. An agent either spawns new windows into its own slot via `hyprnav spawn` (stuck), or drives an existing window where it already is. Headless desktop is dropped for this integration. |
| Identity | Layered: T3 Code sends the thread's hyprnav env id and title to the MCP (small T3 change, approved); fallback to cwd via `hyprnav status --cwd`; last resort a nested self-registered environment. |
| Agent scope | `cua.listApps()` keeps returning everything. New `cua.listWorkspaceApps()` returns windows in the agent's own stuck workspace and its thread environment's slots. `cua.myWorkspace()` returns `{ env, slot, workspace, label }`. |
| Follow | A live portal of the agent's window inside T3 Code, via PipeWire screencast through xdg-desktop-portal-hyprland. Hard requirement: no share-picker dialog, ever. |

### No-dialog screencast, verified against xdph source (main, ba31964)

xdph has no built-in picker UI. `promptForScreencopySelection()` runs an
external program (`screencopy:custom_picker_binary`, default
`hyprland-share-picker`) with env `XDPH_WINDOW_SHARING_LIST` =
`<handleLo>[HC>]<class>[HT>]<title>[HE>]<hyprland address>[HA>]...` and parses
stdout for `[SELECTION]<flags>/window:<handleLo>` (`r` flag = allow restore
token; `screen:<output>` and `region:<output>@x,y,w,h` also exist).
`screencopy:allow_token_by_default = 1` passes `--allow-token` to the picker.

Plan: a picker script `hyprnav-share-picker`:
1. If `$XDG_RUNTIME_DIR/hyprnav/screencast-request` exists and is younger than
   10 s, read the Hyprland window address in it, find the matching entry in
   `XDPH_WINDOW_SHARING_LIST` by the `[HA>]` field, print
   `[SELECTION]r/window:<handleLo>`, delete the file, exit.
2. Otherwise exec the stock `hyprland-share-picker` with the same argv, so
   browser screen sharing keeps its normal dialog.

T3 writes the request file right before `navigator.mediaDevices.getDisplayMedia()`
(Electron 41, Wayland, PipeWire capturer). Config lives in
`~/.config/hypr/xdph.conf`, which does not exist yet; the change is two lines.


## What exists today (verified)

- **Two desktops.** The `cua_repl` MCP launcher (`~/.local/bin/hypr-use-mcp`)
  reads `~/.local/share/hypr-use/headless-env.json` and drives a separate
  headless Hyprland (output TEST 1280x800, runtime `/tmp/hypr-use-dahf9c63`),
  with the Portal plugin loaded and three windows (fixture, sentinel, a Zen).
  Agents do not touch the live desktop at all right now. The live compositor
  has no hyprnav-plugin loaded, so `hyprnav spawn` placement is dead there.
- **T3 Code already speaks hyprnav.** Each project, worktree and thread gets a
  hyprnav environment (`p.<hash>.w.<hash>.t.<uuid>`, client `t3code`, thread
  title stored). T3 assigns slots per scope, stores launch commands, and locks
  the thread environment when a thread is active. The live DB shows slot 1
  "Terminal" (managed) and slot 2 "T3code" (fixed, workspace 2).
- **The MCP knows very little about itself.** One `server.mjs` per agent
  process, stdio. It has no agent id, no thread id, no cwd, no notion of "my
  workspace". `cua.listApps()` returns every window on the compositor it is
  connected to. Sessions exist only per bound target window, for dialog
  protection, and end on `turn_ended`.
- **hyprnav now has sticks.** A spawned tree stays on its workspace; the grid
  snapshot exposes `stuck` per cell; the shell draws a pin.

## The gap

"Which agent is doing what, where" is not represented anywhere. hyprnav knows
environments and workspaces. T3 knows threads. The MCP knows windows and
actions. Nobody joins them.

## Design options

### A. Identity: how an MCP instance learns who it is

1. **Environment variables from the launcher.** T3 (or Claude Code, Codex)
   passes `HYPRNAV_ENV=<env-id>`, `HYPR_USE_AGENT_LABEL=<thread title>` when it
   starts the MCP. Cheapest; T3 already computes the env id. Other hosts need
   their own wiring.
2. **Derive from cwd.** `hyprnav status --cwd $PWD` resolves the project or
   worktree environment. Works for any host that starts the MCP in the repo,
   fails for thread scope (threads share a cwd).
3. **Register on first use.** MCP calls `hyprnav env ensure --client cua
   --title <label>` itself and creates `cua.<pid>` environments. No host
   cooperation needed, but produces environments nobody navigates to unless
   they nest under the T3 one (`<thread-env>.cua`).

Recommendation: 1 with 2 as fallback, and the MCP always tags its hyprnav
records with client `cua` so the dashboard can tell agent-owned slots apart.

### B. Placement: where an agent's windows live

1. **Headless desktop, as now.** Zero interference with the user, but the
   windows are invisible to the live shell. "Visible in dashboards" then means
   the Portal renders screenshots and the shell shows them as images, refreshed
   on demand. No live thumbnails, no "go there".
2. **Live compositor, one managed slot per agent.** The MCP gains
   `cua.launch(cmd)` which runs `hyprnav spawn --no-focus <ws>` into an
   agent-owned slot of its environment (e.g. slot 9 "Agent: <label>"). Sticks
   keep dialogs there. The shell's grid then shows the agent's windows as live
   frames with a pin, and "follow" is just `hyprnav goto`. This is what the
   sticking work was for.
3. **Both.** Headless for untrusted or noisy work, live slot for anything the
   user might want to watch. A per-call flag.

Recommendation: 2 as the default for T3-launched agents, keep 1 available.
This is the only option where the existing shell dashboard works unchanged.

### C. What the dashboard shows

Minimum: the grid cell already says "stuck". Add to the hyprnav grid snapshot
per cell: `agent: { label, client, last_action_at, action_count, state }`
where state is `working | waiting_for_user | idle | finished`. Sources:

- `label`, `client`: from the environment/slot record (A).
- `last_action_at`, `action_count`: the MCP reports after each dispatched
  action (`hyprnav agent beat --env .. --slot .. --state working`). One socket
  request per action is cheap; the daemon keeps it in memory, not SQLite.
- `waiting_for_user`: the MCP sets it when it finishes a turn while a dialog
  it cannot handle is open, or when the host says so via `turn_ended`.

Shell rendering: the pin becomes a small status dot (yellow working, paper
idle, warn waiting). The environment row title gets "2 agents" after it. The
switcher card subtitle shows the label.

### D. Follow

Three different things people mean by "follow":

1. **Go there.** `hyprnav goto` to the agent's slot. Exists.
2. **Peek without leaving.** A floating live thumbnail of the agent's window on
   the user's current workspace, 320 px wide, bottom right, click to go.
   Quickshell `ScreencopyView` can do this today for live-compositor windows.
   `qs ipc call follow start <env> <slot>`.
3. **Ride along.** The user's view switches to whatever the agent is acting on,
   action by action. Disruptive by definition; only sensible as an explicit
   mode you turn on for one agent, and it conflicts with the whole point of
   sticking. Cheap to build once 2 exists (the MCP's beat carries the target
   window address), but I would not build it first.

Recommendation: 2, with 1 as the click action.

### E. Agent-side awareness

Should the agent itself know about hyprnav? Two small additions to the `cua`
JS surface would help agents behave:

- `cua.myWorkspace()` returns `{ env, slot, workspace, label }`.
- `cua.listApps()` gains a `mine: true` flag for windows in its own stick, and
  a default filter `{ scope: "mine" }`, so an agent stops seeing (and
  accidentally acting on) the user's windows. Explicit `{ scope: "all" }` is
  still possible under the owner's permission mode.

The second one is a safety improvement independent of dashboards.

## Open questions, in the order I want to ask them

1. Should agents move from the headless desktop to live managed slots (B2), or
   stay headless with screenshot-based dashboards (B1)?
2. Who supplies identity: T3 passes env vars (A1), or the MCP derives it (A2/A3)?
3. Follow: peek thumbnail (D2) first, or ride-along (D3)?
4. Should `listApps` default to the agent's own windows (E)?
5. Which hosts matter: T3 Code only, or also Claude Code and Codex CLI started
   from a terminal in the thread's worktree?

## Out of scope for now

Multi-monitor placement policy, remote (SSH) agents, anything in `/etc/nixos`.
