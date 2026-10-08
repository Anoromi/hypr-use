// Window recording for the unified cua MCP.
//
// Screen capture tools cannot see a background window, but the portal's
// screenshots can. A recording grabs them in a loop and pipes each frame
// straight into ffmpeg, so frames never accumulate in the JS runtime or in
// tool output. Frames keep their capture time (wall clock), and the encoder
// repeats frames to a constant rate, so slow captures still play back in
// real time. Fragmented MP4 stays playable if the worker is killed mid-way.
import {spawn} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

/** Width and height of PNG or JPEG bytes. */
export function imageSize(bytes) {
  const b = Buffer.from(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (b.length >= 24 && b.readUInt32BE(0) === 0x89504e47) return {width: b.readUInt32BE(16), height: b.readUInt32BE(20)};
  if (b[0] === 0xff && b[1] === 0xd8) {
    for (let i = 2; i + 9 < b.length;) {
      if (b[i] !== 0xff) { i++; continue; }
      const marker = b[i + 1];
      if (marker === 0xd8 || marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) { i += 2; continue; }
      // SOF0–SOF15 carry the frame size; C4 (DHT), C8 (JPG) and CC (DAC) do not.
      if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker))
        return {width: b.readUInt16BE(i + 7), height: b.readUInt16BE(i + 5)};
      i += 2 + b.readUInt16BE(i + 2);
    }
  }
  throw Error('Recording frame is not PNG or JPEG');
}

export function defaultRecordingPath(env = process.env, now = new Date()) {
  const videos = env.XDG_VIDEOS_DIR || path.join(os.homedir(), 'Videos');
  const stamp = now.toISOString().replace(/[:.]/g, '-').replace(/-\d+Z$/, '');
  return path.join(videos, 'hypr-use', `recording-${stamp}.mp4`);
}

/**
 * capture(target) resolves to one frame's image bytes. Only one recording
 * runs per MCP process; the agent's other actions interleave with its frames.
 */
export function createRecorder(capture, {ffmpeg = 'ffmpeg', env = process.env} = {}) {
  let active = null;

  async function start(target, opt = {}) {
    if (active) throw Error(`A recording is already running (${active.path}); stop it first`);
    if (!opt || typeof opt !== 'object' || Array.isArray(opt) || Object.keys(opt).some(k => !['path', 'fps', 'maxSeconds'].includes(k)))
      throw Error('startRecording options are path, fps and maxSeconds');
    const fps = opt.fps ?? 10, maxSeconds = opt.maxSeconds ?? 600;
    if (!Number.isFinite(fps) || fps < 1 || fps > 30) throw Error('fps must be 1–30');
    if (!Number.isFinite(maxSeconds) || maxSeconds < 1 || maxSeconds > 3600) throw Error('maxSeconds must be 1–3600');
    const file = opt.path ?? defaultRecordingPath(env);
    if (typeof file !== 'string' || !path.isAbsolute(file) || !/\.(mp4|mkv)$/i.test(file)) throw Error('path must be an absolute .mp4 or .mkv file');
    fs.mkdirSync(path.dirname(file), {recursive: true});

    // The first frame fixes the video size; later frames of another size
    // (a resized window) are scaled into it, keeping their aspect ratio.
    const first = await capture(target);
    let {width, height} = imageSize(first);
    width -= width % 2; height -= height % 2;
    const filter = `scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p`;
    const child = spawn(ffmpeg, [
      '-hide_banner', '-loglevel', 'error', '-y',
      '-use_wallclock_as_timestamps', '1', '-f', 'image2pipe', '-i', '-',
      '-vf', filter, '-fps_mode', 'cfr', '-r', String(fps),
      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
      ...(/\.mp4$/i.test(file) ? ['-movflags', '+frag_keyframe+empty_moov+default_base_moof'] : []),
      file,
    ], {stdio: ['pipe', 'ignore', 'pipe'], env});
    let stderr = '';
    child.stderr.on('data', d => { stderr = (stderr + d).slice(-4000); });
    const exited = new Promise(resolve => child.on('close', code => resolve(code)));
    child.stdin.on('error', () => {});

    const rec = {path: file, target, frames: 0, started: Date.now(), stopping: false, error: null};
    const write = bytes => new Promise((resolve, reject) => {
      if (child.exitCode !== null) return reject(Error(`ffmpeg exited: ${stderr.trim() || child.exitCode}`));
      child.stdin.write(Buffer.from(bytes.buffer, bytes.byteOffset, bytes.byteLength), e => e ? reject(e) : resolve());
    });
    rec.loop = (async () => {
      try {
        await write(first); rec.frames++;
        const interval = 1000 / fps;
        let due = Date.now() + interval;
        while (!rec.stopping && Date.now() - rec.started < maxSeconds * 1000) {
          const wait = due - Date.now();
          if (wait > 0) await new Promise(r => setTimeout(r, wait));
          due = Math.max(due + interval, Date.now());
          if (rec.stopping) break;
          await write(await capture(target)); rec.frames++;
        }
      } catch (e) { rec.error = e.message; }
      child.stdin.end();
      rec.code = await exited;
    })();
    active = rec;
    return {path: file, width, height, fps};
  }

  async function stop() {
    const rec = active;
    if (!rec) throw Error('No recording is running');
    rec.stopping = true;
    await rec.loop;
    active = null;
    const seconds = Math.round((Date.now() - rec.started) / 100) / 10;
    if (rec.code !== 0) throw Error(`Recording failed${rec.error ? `: ${rec.error}` : ''} (ffmpeg exit ${rec.code}); partial video may be at ${rec.path}`);
    return {path: rec.path, frames: rec.frames, seconds, ...(rec.error ? {stoppedEarly: rec.error} : {})};
  }

  const status = () => active ? {path: active.path, frames: active.frames, seconds: (Date.now() - active.started) / 1000, error: active.error} : null;
  return {start, stop, status};
}
