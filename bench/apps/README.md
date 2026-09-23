# Benchmark apps

`bench_app.py` provides the deterministic GTK 4 fixtures. The lab scenario starts it with one
of `forms-app`, `list-app`, `editor-app`, `dialog-storm`, or `multi-window-app`. Each process
writes `<BENCH_STATE_DIR>/<app>.json` after every state change using an atomic rename.

Run one inside the benchmark runtime:

```sh
nix-shell runtime.nix --run 'BENCH_STATE_DIR=/tmp/cua-state python3 apps/bench_app.py forms-app'
```
