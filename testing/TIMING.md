# Internal tool timings

The Calc test server loads `portal-timing.py` automatically. Subsequent tool responses include `_meta["hypr-use/timing"]`, which the existing `calc-session/wire.jsonl` recorder preserves.

Each span has a stage name, parent index, start offset, inclusive duration, and exclusive `self_ms`. Use exclusive time plus `unattributed_ms` to reconcile against `total_ms`. Inclusive parent and child durations overlap and must not be added together.

Measured stages include cached-state lookup, geometry refresh, window resolution, indicator updates, typing, each key/helper call, explicit sleeps, screenshot capture, accessibility snapshots, menus, related popup previews, result packaging, request preparation, and audit calls. These are server-side function boundaries; a helper duration still combines process startup and its internal operations. Timing metadata contains no typed text or screenshot data.

The total ends before final JSON serialization and transport. Uninstrumented policy and orchestration work remains in exclusive or unattributed time. Existing historical calls cannot gain this detail retroactively. No new desktop actions were performed when adding instrumentation.

Validation: `python testing/test-portal-timing.py` checks nested spans, failure recording, total reconciliation, context cleanup, non-tool responses, and idempotent installation. Both instrumentation and the modified test server also pass Python compilation.
