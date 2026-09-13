# Project scope

Confirmed with the user on 6 September 2026.

- Build an MCP server for Codex. Responses API integration is out of scope.
- Background operation is a requirement, including while the user works in another app. A foreground-only MVP does not meet the goal.
- Preserve the user's physical cursor, keyboard focus and current workspace. Ordinary operation must not interrupt their typing or redirect their input.
- If an operation requires taking over foreground input, report it as unsupported in background mode. Do not silently fall back to foreground control.
- Hyprland upgrades are acceptable. The currently installed version is not a compatibility requirement. This does not authorize upgrading the machine during research.
- Evaluate maintenance through recent substantive commits, fixes, tests and compatibility with current Hyprland. A newer version target is a useful signal, not proof of better maintenance.

## Working assumptions

Prefer controlling existing apps and sessions. A VM or nested desktop is useful for testing, but is not presumed to satisfy that experience.

The user's tolerance for small visible effects is not yet quantified. For now, require no input theft or workspace switching; measure overlays, popup behavior and other visible effects separately.

## Candidate selection

Prioritize compositor-assisted background implementations and AT-SPI actions. Treat foreground-oriented projects as sources of reusable components rather than complete solutions.

Evaluate native Wayland and XWayland separately. Test human typing during agent activity, dialogs, clipboard interactions, cancellation and focus restoration. Report unsupported operations explicitly.

This scope supersedes the initial reports' foreground-first and dual-adapter recommendations.
