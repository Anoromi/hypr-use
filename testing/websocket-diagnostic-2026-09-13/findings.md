# WebSocket investigation — 2026-09-13

Installed CLI: 0.154.0. No user configuration or MCP implementation changed. All desktop access was read-only listApps.

## Finding

The observed failure is a model transport send stall, not an MCP connection failure. The affected thread accumulated screenshots. At HTTPS fallback its request was 27,328,696 bytes, compressed to 19,535,388 bytes. Later requests grew to roughly 29 MB. The rollout contains repeated input_image blocks of roughly 0.6–2.7 MB each.

Actual incident UTC: 13:10:53 connection reset; 13:16:01 send idle timeout; 13:16:36 broken pipe; 13:17:10 broken pipe; 13:22:12 send idle timeout; 13:22:49 first logged HTTPS compression. Nearly 12 minutes elapsed from first reset to HTTPS fallback.

## CLI reproduction

- No MCP, no image: CONNECTION_OK; logged WebSocket handshake 445 ms.
- Hypr-use attached, one listApps call: tool completed and CONNECTION_OK.
- One synthetic PNG: 21.25 s, success.
- Eight synthetic PNGs, 23,053,944 file bytes (~30.7 MB base64): watchdog stopped at 90.02 s, no completion.
- Same eight PNGs with custom WebSocket provider, 15 s idle timeout and zero stream retries: explicit `idle timeout sending websocket request`, followed by HTTPS fallback. This reproduces the exact error without MCP.
- Same eight PNGs using HTTPS: no completion before 90.02 s watchdog. HTTPS alone is not a demonstrated solution.
- Same eight images JPEG quality 65, 3,710,555 file bytes (~4.95 MB base64): 33.08 s, success over WebSocket.

Single trials establish reproduction and a successful mitigation case, not an exact size limit or a reliability rate. Synthetic noise is deliberately difficult to compress. JPEG is lossy; text legibility must be checked before changing screenshot defaults.

## Source trace

Reviewed upstream snapshot 36f0dbe796d9bb1a18a0fc0640ed08b3e1d54564, not asserted identical to the installed binary.

- codex-rs/codex-api/src/endpoint/responses_websocket.rs, send_websocket_request: wraps ws_stream.send in stream idle timeout and produces the exact observed error string.
- codex-rs/model-provider-info/src/lib.rs: default stream idle timeout is 300,000 ms.
- codex-rs/core/src/responses_retry.rs: exhausts stream retry budget before switching to HTTP.
- codex-rs/core/src/client.rs: incremental history depends on previous response/connection state; reset clears that state, requiring full request input again.
- Hypr-use mcp/unified/facade.mjs image(): forwards the backend image block directly, without a transport size reduction.

## Interpretation and next fix

Large accumulated image payloads explain the reproduction and are strongly implicated in the real incident. The precise underlying network/proxy/server bottleneck is not established: a socket send timeout alone cannot identify which peer stopped draining data. No evidence establishes a fixed server payload cap.

Reduce screenshot payload sizes, avoid unnecessary screenshots, and handle large-history reconnects with a bounded send timeout/earlier fallback. A fresh thread avoids accumulated image history. Do not describe this as an accessibility or Hyprland focus bug.

Raw reproduction data and synthetic images are in /tmp/hypr-ws-diagnostic. The scripts here record the exact invocations and use that directory. Event summaries omit image content and headers. Original user logs were read through SQLite mode=ro and were not changed.
