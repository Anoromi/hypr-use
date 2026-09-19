# cua MCP + hyprnav: plan

Date: 2026-09-20. Decisions come from `HYPRNAV-INTEGRATION-DISCUSSION.md`.
Four repos are touched, each in its own phase and directory:

| Repo | Role |
|---|---|
| `~/code/stolen/hyprland-plugins` (hyprnav) | agent registry, heartbeat, snapshot fields, picker script |
| `~/code/experiments/hypr-use` (cua MCP) | self-registration, `cua.launch`, workspace-scoped listing, labels, beats |
| `~/code/experiments/hyprnav-shell` | pins become status, agent labels, peek |
| `~/code/stolen/t3code-upstream-rebuild-20260718` | thread enrichment notification, portal panel |

No `/etc/nixos` change except the two-line `xdph.conf`, done last and only
with approval.

## Model

An **agent** is one MCP server process. On startup it creates a hyprnav
environment `<parent>.agent-<pid>` where `<parent>` is the environment that
owns its working directory (`hyprnav status --cwd`), or `agents` when none
exists. The environment gets slot 1 as a managed workspace named after the
agent's label. Everything the agent launches goes through `hyprnav spawn
--no-focus` into that slot, so it sticks there. Windows the agent merely
drives stay where they are and are recorded as "attached".

hyprnav's daemon keeps an in-memory **agent registry** keyed by environment:
`{ label, client, pid, state, last_beat_ms, action_count, attached_windows[],
current_target }`. It is filled by beats from the MCP and pruned when the PID
dies. It is exposed in `ui_snapshot_grid` per cell and in a new
`agents_list` request.

## Phase 1: hyprnav daemon and CLI

1. Requests: `agent_register {env, label, client, pid}`,
   `agent_beat {env, state, target?, action?}`,
   `agent_label {env, label}`, `agent_attach {env, address}`, `agents_list`.
   States: `working | waiting_for_user | idle | finished`.
2. Registry in memory; environments and slots persist as they already do.
   A cleanup pass every 2 s marks agents whose PID is gone as `finished` and
   removes them after 60 s, deleting the environment if its slot workspace is
   empty. Otherwise the environment stays so windows remain reachable.
3. `ui_snapshot_grid` cells gain `agent: { label, state, last_beat_ms,
   action_count } | null`. Row snapshot gains `agent_count`.
4. `ui_snapshot_switcher` items gain the same `agent` field when the card's
   workspace belongs to an agent slot.
5. CLI: `hyprnav agents` (table), `hyprnav agent label <env> <text>`,
   `hyprnav agent goto <env>`.
6. `hyprnav-share-picker`: a shell script installed next to `hyprnav`.
   Reads `$XDG_RUNTIME_DIR/hx/<instance>/screencast-request` (a Hyprland
   window address, ignored if older than 10 s), matches it against the `[HA>]`
   field of `XDPH_WINDOW_SHARING_LIST`, prints `[SELECTION]r/window:<handle>`
   and removes the file. Without a request it execs `hyprland-share-picker`
   with the original arguments. Unit test: a fake window list and request.
7. `hyprnav screencast request <address>` writes that file, for any client.

Exit: all six requests round-trip in the lab; a fake xdph invocation of the
picker returns the right handle; `hyprnav agents` prints a live table.

## Phase 2: cua MCP

1. Startup (`server.mjs`, before the first tool call): resolve parent env
   from cwd, `agent_register` with label = host name from `initialize`
   clientInfo plus the folder basename, client `cua`. Hold the env id in
   memory for the process lifetime. Failure to reach the daemon is logged and
   leaves the MCP working exactly as today.
2. New JS surface:
   - `cua.setLabel(text)`: `agent_label`. Tool instructions ask the agent to
     call it once with a short description of its task.
   - `cua.myWorkspace()`: `{ env, slot, workspace, label }`.
   - `cua.launch(argv, {follow?: false})`: `hyprnav spawn --no-focus <ws> --
     argv` into the agent's slot, waits for the first window of the tree,
     returns a bound app like `getApp`. The README's "launching apps is
     unsupported" line goes away.
   - `cua.listWorkspaceApps()`: windows in the agent's slot workspace plus
     the parent environment's other slots (the thread terminal etc.).
     `cua.listApps()` unchanged.
   - `getApp(existing)` additionally sends `agent_attach` so the dashboard
     can show "driving Zen on frame 3".
3. Beats: after every dispatched action, `agent_beat {state: working,
   target, action}`. On `turn_ended`: `idle`. When an action returns a
   related dialog the agent has not handled by turn end: `waiting_for_user`.
   On process exit: `finished`. Beats are fire-and-forget over a short
   connection, never on the action's critical path.
4. Host enrichment hook: accept an optional `hyprnav_env` and `label` in the
   existing `turn_ended` payload or a new `notifications/hyprnav/context`.
   When present, re-register under that env instead of the cwd-derived one.
5. Launcher: `~/.local/bin/hypr-use-mcp` currently targets the headless
   desktop. Add a live-session launcher that uses the current
   `HYPRLAND_INSTANCE_SIGNATURE`, and make the headless one the explicit
   `--headless` variant. The Portal plugin must be loaded live for input
   routing; that is already the case.

Exit: from a plain terminal Claude Code session in the lab, `cua.launch(["zen-beta"])`
opens Zen in the agent's frame, `hyprnav agents` shows it working with a
label, and a stray dialog from Zen lands in that frame.

## Phase 3: hyprnav-shell

1. Pin becomes a status mark: pencil dot pulsing while `working`, steady when
   `idle`, warn colour when `waiting_for_user`, fixer when `finished`.
2. Grid cell title shows the agent label under the slot name; row title
   shows "2 agents" when the environment has nested agent environments.
   Agent environments render as sub-rows under their parent, indented, not
   as separate rolls.
3. Switcher card subtitle shows the label and state.
4. Bar: the slot digit strip shows the same status dot; hovering shows label.
5. Peek: `qs ipc call follow start <env>` shows a 360 px live thumbnail of
   the agent's current target window bottom right of the current workspace,
   click to `goto`, `follow stop` hides. Uses the existing `WorkspaceThumb`.
6. Grid gets `f` to peek the selected frame's agent.

Exit: recording with two agents in two frames, one waiting, peek open.

## Phase 4: T3 Code

1. When T3 starts the cua MCP for a thread, send `hyprnav_env` (the thread
   environment id) and `label` (thread title) in the first `turn_ended`-style
   notification, and again when the title changes.
2. Portal panel in the thread view: lists the thread's agents from
   `agents_list` (filtered to environments nested under the thread env),
   with state. Clicking one calls `hyprnav screencast request <address>`
   for the agent's current target window, then `getDisplayMedia({video: true})`
   and attaches the stream to a `<video>` element. Electron 41 on Wayland
   goes through the PipeWire portal; with the picker script in place no
   dialog appears. `setDisplayMediaRequestHandler` in the main process
   selects the first screen source when the portal returns one.
3. When the agent's target changes (beat), the panel re-requests; a stream
   already open is kept until the new one plays to avoid flicker.
4. Close the panel: stop tracks, release the session.

Exit: recording of T3 with a thread whose agent drives Zen on another frame,
live in the panel, while the user types in the thread.

## Phase 5: verification

Lab scenarios, recorded, in `hyprnav-shell/recordings/agents-*.mp4`:

1. Two agents, two folders, both launched from terminals: separate frames,
   labels, states.
2. Agent drives an existing window: attached marker on that frame, no move.
3. Agent dies: state finished, then environment cleaned once its frame empties.
4. Picker: a fake xdph call with a request file returns the handle; without
   one execs the stock picker (asserted by a stub).
5. T3 portal end to end (Phase 4 exit).
6. Unit tests: registry pruning, picker script, `listWorkspaceApps` filter,
   `cua.launch` waiting for the first window.

## Phase 6: live rollout (with approval)

Load the fixed hyprnav-plugin live (`hyprnav-plugin-dev-reload`), restart the
daemon with the new build at a moment the switcher may drop, switch the MCP
launcher to the live variant, add the two `xdph.conf` lines, restart
`xdg-desktop-portal-hyprland`. Verify a Claude Code session in a terminal
appears in the grid within a second of its first `cua` call.

## Risks

- **Portal plugin and hyprnav-plugin both hook window open.** Portal's
  session guard moves related windows to the target's workspace; the stick
  manager moves to the slot. Both agree when the target lives in the slot;
  they disagree for attached windows on the user's frames. Rule: sticks only
  apply to spawned trees, so attached windows follow Portal's guard. Test 2
  covers it.
- **Electron's PipeWire path.** `getDisplayMedia` needs
  `WebRTCPipeWireCapturer` enabled; Electron 41 has it on by default on
  Wayland, but the flag will be asserted in the T3 launcher.
- **Picker is global.** A bug in the script would break all screen sharing.
  The script fails open to the stock picker on any error.
- **Beat volume.** One request per action; the daemon serves one connection
  at a time. Beats use a 200 ms timeout and are dropped on contention.
- **Environment sprawl.** Agent environments are removed once finished and
  empty; `hyprnav agents --prune` removes stragglers.
