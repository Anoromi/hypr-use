# Local Hyprnav comparison

Inspected 6 September 2026. This is a source comparison, not a runtime test. No plugin was rebuilt or reloaded.

Hyprnav checkout: `/home/anoromi/code/stolen/hyprland-plugins`, HEAD `6905278cb7c646ee8b28512efbd554e38bd0c6a7`, including existing uncommitted changes in the preview/plugin and Rust UI/runtime files. Those changes were read, not modified.

Portal checkout: `vendor/hypr-agent-portal`, HEAD `bc0b100719dafb8bdf893ace4d3be1d78b1a0876`.

## The language boundary

Both projects use a C++23 shared library inside Hyprland. Hyprnav's Rust runs outside the compositor, in its daemon and Qt/QML application. Its `cxx-qt` bridge connects Rust to Qt and UI helper C++, not to the in-process Hyprland plugin.

Portal uses Python for the corresponding external orchestration layer. Changing Python to Rust or Go would leave the compositor plugin as a separate concern.

| Responsibility | Hyprnav | Hypr-Agent-Portal |
|---|---|---|
| In-process plugin | C++ preview and spawn managers | C++ screenshot capture, targeted input, sessions, window management, cancellation and approval handling |
| External service | Rust daemon with SQLite state, environments, workspace slots and spawn tracking | Python MCP server with app state, accessibility, image processing, policy and action orchestration |
| UI | Qt/QML overlays with Rust and C++ bridges | Compositor-rendered agent cursor and external MCP client |
| Plugin communication | Unix sockets for preview events/requests and spawn transactions; preview dispatcher also exists | Named Hyprland dispatchers invoked through the external bridge; screenshot artifacts and metadata |
| Image purpose | Workspace-card previews, default height 480, JPEG quality 82 | Target-window or output captures with image/coordinate metadata for automation |
| Input purpose | Navigate workspaces and place spawned windows, optionally preserving original focus | Deliver pointer/keyboard actions into existing background application surfaces |
| ABI dependency | Internal headers, host/client hash check, hooks into monitor damage functions | Internal renderer, seat, surface and keyboard resources; matching compositor build required |

## What Hyprnav already demonstrates

Its Rust daemon and C++ plugin communicate across a process boundary. That is a useful local pattern for a Rust hypr-use MCP server with a narrow C++ plugin.

Hyprnav also offers relevant experience with compositor rendering, preview invalidation, per-instance runtime sockets and spawn placement. However, its workspace previews are not a direct substitute for full-detail, snapshot-bound application captures.

The spawn manager's `preserve` policy restores the original focus around application placement. That is different from Portal's keyboard-resource transactions for repeatedly typing into a background app without changing compositor-global keyboard focus.

## What Portal adds

Portal resolves target surfaces, routes keyboard events to target-client resources, restores surface/modifier state and handles physical-input interruption. It also handles pointer transactions, related windows and XWayland compatibility. Hyprnav's plugin has no equivalent background computer-use action API in the inspected source.

Both native plugins can affect compositor stability. Rust outside the compositor does not make the C++ plugin memory-safe or remove its version coupling. Moving native logic into Rust would still require a carefully designed FFI boundary to Hyprland's C++ internals; the current Hyprnav architecture does not demonstrate that approach.

## Implication for hypr-use

Prefer the same separation of processes that Hyprnav already uses:

```text
Codex → Rust MCP service → explicit IPC contract → narrow C++ Hyprland plugin
```

Keep model-facing schemas, snapshot bookkeeping, accessibility queries and policy outside the compositor. Keep surface resolution, rendering and input transactions in the plugin. Native code must still validate targets and enforce lock/input-restoration invariants.

Use Hyprnav as the architecture and local packaging reference; use Portal as the background-input implementation reference. Do not merge automation into the working Hyprnav plugin merely to reuse its build flow. A separate plugin keeps the responsibilities and upgrade/testing boundaries clearer.

Rust is a credible alternative to the previously suggested Go service, especially given the local Rust tooling. This comparison establishes architecture fit, not a performance advantage or a decision to rewrite.

## Source locations

- [Hyprnav plugin build](/home/anoromi/code/stolen/hyprland-plugins/hyprnav-plugin/CMakeLists.txt)
- [Plugin initialization and ABI/hooks](/home/anoromi/code/stolen/hyprland-plugins/hyprnav-plugin/main.cpp:117)
- [Workspace preview rendering](/home/anoromi/code/stolen/hyprland-plugins/hyprnav-plugin/PreviewManager.cpp:396)
- [Spawn focus restoration](/home/anoromi/code/stolen/hyprland-plugins/hyprnav-plugin/SpawnManager.cpp:505)
- [Rust-to-Qt build bridge](/home/anoromi/code/stolen/hyprland-plugins/hyprnav/build.rs)
- [Rust daemon socket communication](/home/anoromi/code/stolen/hyprland-plugins/hyprnav/src/server.rs:1978)
- [Portal keyboard transaction](vendor/hypr-agent-portal/src/plugin/main.cpp)
- [Portal capture implementation](vendor/hypr-agent-portal/src/plugin/screenshot_capture.cpp)
