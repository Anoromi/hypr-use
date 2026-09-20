// hyprnav bridge for the unified cua MCP.
//
// One MCP server process is one agent. On startup it registers with the
// hyprnav daemon and gets a temporary slot (an unnumbered frame) in the
// environment of its working directory. Every dispatched action sends a
// heartbeat with the target window so dashboards can show what the agent is
// doing. Everything here is best effort: without a daemon the MCP behaves as
// before.
import net from 'node:net';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawn, execFile} from 'node:child_process';

function fnv1a64(text) {
  let h = 0xcbf29ce484222325n;
  for (const b of Buffer.from(text, 'utf8')) { h ^= BigInt(b); h = (h * 0x100000001b3n) & 0xffffffffffffffffn; }
  return h.toString(16).padStart(16, '0');
}

export function socketPath(env = process.env) {
  const runtime = env.XDG_RUNTIME_DIR || `/run/user/${os.userInfo().uid}`;
  const sig = env.HYPRLAND_INSTANCE_SIGNATURE || 'default';
  return path.join(runtime, 'hx', fnv1a64(sig), 'hyprnav.sock');
}

/** One request per connection, like the Rust client. Resolves the result or throws. */
export function request(op, params = {}, {timeoutMs = 2000, env = process.env} = {}) {
  return new Promise((resolve, reject) => {
    const sock = net.createConnection(socketPath(env));
    let buf = '';
    const timer = setTimeout(() => { sock.destroy(); reject(new Error(`hyprnav ${op}: timeout`)); }, timeoutMs);
    sock.on('connect', () => sock.write(JSON.stringify({op, ...params}) + '\n'));
    sock.on('data', d => { buf += d; const i = buf.indexOf('\n'); if (i < 0) return; clearTimeout(timer); sock.end();
      try { const r = JSON.parse(buf.slice(0, i)); r.ok ? resolve(r.result) : reject(new Error(`hyprnav ${op}: ${r.error?.message ?? 'failed'}`)); }
      catch (e) { reject(e); } });
    sock.on('error', e => { clearTimeout(timer); reject(e); });
  });
}

export function addressOf(target) {
  const m = /address:(0x[0-9a-fA-F]+)/.exec(String(target ?? ''));
  return m ? m[1].toLowerCase() : null;
}

export function hyprctlJson(args, env = process.env) {
  return new Promise((resolve, reject) => execFile('hyprctl', ['-j', ...args], {env, maxBuffer: 8 << 20}, (e, out) => {
    if (e) return reject(e);
    try { resolve(JSON.parse(out)); } catch (err) { reject(err); }
  }));
}

export class HyprnavAgent {
  constructor({id, label, client = 'cua', pid = process.pid, cwd = process.cwd(), env = process.env}) {
    this.id = id; this.label = label; this.client = client; this.pid = pid; this.cwd = cwd; this.env = env;
    this.info = null; this.enabled = false; this.pendingBeat = null;
  }
  async register() {
    if (this.env.HYPR_USE_NO_HYPRNAV === '1') { this.enabled = false; return null; }
    try {
      const params = {agent_id: this.id, label: this.label, client: this.client, pid: this.pid, cwd: this.cwd, env: this.env.HYPRNAV_ENV || null};
      // Thread attribution: the host app (T3 Code) exports these for its MCP children.
      if (this.env.T3CODE_THREAD_ID) params.thread_id = this.env.T3CODE_THREAD_ID;
      if (this.env.T3CODE_ENVIRONMENT_ID) params.thread_environment_id = this.env.T3CODE_ENVIRONMENT_ID;
      this.info = await request('agent_register', params, {env: this.env});
      this.enabled = true;
    } catch (e) {
      this.enabled = false;
      if (this.env.HYPR_USE_HYPRNAV_DEBUG) process.stderr.write(`hyprnav: not registered: ${e.message}\n`);
    }
    return this.info;
  }
  /** Fire-and-forget heartbeat; never blocks an action. */
  beat({state, target, action} = {}) {
    if (!this.enabled) return;
    const params = {agent_id: this.id};
    if (state) params.state = state;
    const address = addressOf(target); if (address) params.target = address;
    if (action) params.action = action;
    request('agent_beat', params, {timeoutMs: 400, env: this.env}).then(info => { this.info = info; }).catch(() => {});
  }
  async setLabel(label) {
    this.label = label;
    if (!this.enabled) return {label};
    return request('agent_label', {agent_id: this.id, label}, {env: this.env});
  }
  async finish() { if (this.enabled) await request('agent_finish', {agent_id: this.id}, {env: this.env}).catch(() => {}); }
  myWorkspace() {
    const i = this.info; if (!i) return null;
    return {env: i.environment_id, slot: i.slot_index, workspace: i.workspace_id, label: i.label, agentId: i.agent_id};
  }
  /** Spawn argv into the agent's slot with a stick; resolves when the first window maps or after timeoutMs. */
  async launch(argv, {timeoutMs = 15000} = {}) {
    const ws = this.info?.workspace_id;
    if (!ws) throw new Error('hyprnav: agent has no workspace; is the daemon running?');
    const before = new Set((await hyprctlJson(['clients'], this.env)).map(c => c.address));
    const child = spawn('hyprnav', ['spawn', '--no-focus', String(ws), '--', ...argv], {env: this.env, stdio: 'ignore', detached: true});
    child.unref();
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      await new Promise(r => setTimeout(r, 250));
      const clients = await hyprctlJson(['clients'], this.env);
      const fresh = clients.find(c => !before.has(c.address) && c.workspace?.id === ws && c.mapped);
      if (fresh) { this.beat({state: 'working', target: `address:${fresh.address}`, action: `launch ${argv[0]}`}); return fresh; }
    }
    throw new Error(`hyprnav: no window appeared on workspace ${ws} within ${timeoutMs} ms`);
  }
  /** Windows on the agent's workspace plus the other slots of its environment. */
  async workspaceWindows() {
    const ws = this.info?.workspace_id; if (!ws) return [];
    const [clients, grid] = await Promise.all([hyprctlJson(['clients'], this.env), request('ui_snapshot_grid', {cwd: null}, {env: this.env}).catch(() => null)]);
    const own = new Set([ws]);
    if (grid) for (const cell of grid.items) if (cell.environment_id === this.info.environment_id) own.add(cell.physical_workspace_id);
    return clients.filter(c => c.mapped && own.has(c.workspace?.id)).map(c => ({address: c.address, class: c.class, title: c.title, workspace: c.workspace.id, pid: c.pid, mine: c.workspace.id === ws}));
  }
}

export function defaultLabel(env = process.env, cwd = process.cwd()) {
  const host = env.HYPR_USE_HOST_NAME || env.CLAUDE_CODE_ENTRYPOINT || env.CODEX_HOME && 'codex' || 'agent';
  return `${host} in ${path.basename(cwd)}`;
}
