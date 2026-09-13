# Upstream checkout

`hypr-agent-portal/` is an independent Git clone of https://github.com/gfhdhytghd/Hypr-Agent-Portal.git. Its own Git history, origin and GPL-3.0-only license are preserved. The parent repository ignores the nested checkout.

To reproduce from the hypr-use root:

```sh
git clone https://github.com/gfhdhytghd/Hypr-Agent-Portal.git vendor/hypr-agent-portal
git -C vendor/hypr-agent-portal checkout bc0b100719dafb8bdf893ace4d3be1d78b1a0876
```

This is source for inspection and development. No plugin has been installed or loaded.

## Tested local version

`hypr-agent-portal-0.56.2/` is the modified checkout used by the unified MCP. Its checkpoint is recorded in `checkpoint.json`; `portal-checkpoint.patch` contains all changes from the pinned upstream revision, including new files. Recreate it with:

```sh
git clone https://github.com/gfhdhytghd/Hypr-Agent-Portal.git vendor/hypr-agent-portal-0.56.2
git -C vendor/hypr-agent-portal-0.56.2 checkout bc0b100719dafb8bdf893ace4d3be1d78b1a0876
git -C vendor/hypr-agent-portal-0.56.2 apply ../portal-checkpoint.patch
```

The native plugin was built and loaded for the current compositor session. Build paths and the installed Hyprland ABI are recorded under `testing/reliability50/plugin-builds.json`. Raw recordings and browser profiles remain local and are not part of the source checkpoint.
