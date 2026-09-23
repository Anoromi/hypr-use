# Nix package sources

`flake.lock` pins Nixpkgs and Hypr-Agent-Portal at upstream commit
`bc0b100719dafb8bdf893ace4d3be1d78b1a0876`. The portal runtime applies
`vendor/portal-checkpoint.patch` and then `portal-mcp-runtime.patch`, which
captures the MCP backend changes in the local checkout after that checkpoint.
Only the portal's `mcp/*.py` files and control script enter the package. The flake does not read
the ignored `vendor/hypr-agent-portal-0.56.2` directory.

The MCP launcher uses the current Hyprland session by default. Pass
`--headless` to read `~/.local/share/hypr-use/headless-env.json`, or set
`HYPR_USE_HEADLESS_ENV` to another file. Both modes check their Wayland and
Hyprland sockets before starting the server. `--help` needs no session.

`nix run .#bench -- list` reads the packaged task catalog. Benchmark runs
write to `~/Artifacts/cua-bench/results` by default; set
`HYPR_BENCH_RESULTS_DIR` to change it. Set `HYPR_LAB_ROOT` to the testbed
checkout containing `lab/cua-mcp`, and set `HYPR_LAB` or put `hypr-lab`
on PATH. The benchmark uses the packaged MCP and never writes into the Nix
store.
