# Screenshot transport mitigation

2026-09-13. Bounded follow-up; no desktop inputs or background improvement loop.

## What Codex does

OpenAI describes persistent WebSockets with incremental requests: https://openai.com/index/speeding-up-agentic-workflows-with-websockets/ . Connection loss may require full history again.

Reviewed upstream source snapshot 36f0dbe796d9bb1a18a0fc0640ed08b3e1d54564: codex-rs/utils/image/src/lib.rs uses JPEG quality 85 for its JPEG encoding path, while PNG input can remain PNG. This is not proof that every native macOS screenshot uses JPEG. No desktop binary was inspected in this follow-up.

A user report also describes image-history failures in Codex desktop: https://github.com/openai/codex/issues/28150 . That report is not proof of this incident's cause or an OpenAI guarantee.

## Changes

The MCP encodes large opaque PNG screenshots as JPEG 85 only when smaller, preserves dimensions and transparency, and provides HYPR_USE_IMAGE_FORMAT=png. The JS emitImage helper detects PNG/JPEG bytes instead of labeling every image PNG. Encoding timing and byte counts are included in operation timing metadata.

## Evidence

40 JS/protocol tests and four native image tests pass. Eight synthetic PNG files total 23,053,944 bytes; the implemented encoder produces 5,809,706 bytes (74.8% reduction). One image encoded in about 9 ms. A fresh Astra CLI accepted all eight encoded images and finished in 40.19 seconds. The prior uncompressed PNG run hit its 90-second watchdog; a shorter send-timeout reproduction emitted the exact websocket send timeout. These are single trials, not a reliability guarantee or a measured 90-to-40 speedup.

No dimensions were reduced. JPEG quality 85 is lossy; the lossless override is available for exact pixel comparisons. The MCP cannot prune Codex history or alter the client retry policy, so this mitigates accumulation rather than guaranteeing reconnections always succeed. Existing stored screenshots are unchanged.
