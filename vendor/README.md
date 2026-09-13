# Upstream checkout

`hypr-agent-portal/` is an independent Git clone of https://github.com/gfhdhytghd/Hypr-Agent-Portal.git. Its own Git history, origin and GPL-3.0-only license are preserved. The parent repository ignores the nested checkout.

To reproduce from the hypr-use root:

```sh
git clone https://github.com/gfhdhytghd/Hypr-Agent-Portal.git vendor/hypr-agent-portal
git -C vendor/hypr-agent-portal checkout bc0b100719dafb8bdf893ace4d3be1d78b1a0876
```

This is source for inspection and development. No plugin has been installed or loaded.
