# Portal permission modes

The server now accepts `HYPR_AGENT_PORTAL_PERMISSION_MODE=standard|read-only|full`.
`unrestricted` aliases `full`. Settings are read at MCP startup, not from tool arguments.

- `standard`: previous defaults; view-only unconfigured apps and external confirmation for high-risk actions.
- `read-only`: mutations disabled and mutation tools hidden.
- `full`: full application and clipboard defaults, no high-risk confirmation token, and server-level grab/layer/takeover gates disabled by default.

Explicit narrower settings still win over full-mode defaults. App allowlists, workspace confinement, clipboard settings and read-only controls can be configured independently. `HYPR_AGENT_PORTAL_APPROVAL_POLICY=external|never` separates confirmation from access scope. Canonical `HYPR_AGENT_PORTAL_SECURITY_*` names win over aliases. Misspelled values reject startup. Emergency panic, locked-session handling, identity validation, mutation serialization and native compositor limits remain active.

Codex host approval and Portal server authorization are separate layers. Configure Codex with `default_tools_approval_mode="approve"` and the server environment with `HYPR_AGENT_PORTAL_PERMISSION_MODE="full"` to avoid prompts at both layers. This is not inferred from the parent Codex sandbox setting.

The Calc test uses full mode with its existing LibreOffice confinement and clipboard disabled. These are explicit test scope choices, not full-mode defaults. The original failures and operator policy changes remain in the same recorded thread.

Validation: all 17 upstream Python test scripts passed. Added coverage for full-mode high-risk execution without invoking confirmation validation, unchanged standard defaults, read-only, explicit clipboard/confinement restrictions, panic, full-mode menu grabs and explicit grab overrides, dry-run, alias precedence, and invalid values. No native rebuild is required for this Python policy change.

Source comparisons:
- [Codex MCP tool approval configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli): server defaults and per-tool approval modes.
- [Claude Code permission modes](https://code.claude.com/docs/en/permissions): multiple modes including explicit bypassPermissions.

Patch: `portal-permission-modes.patch`, against Portal bc0b100. Existing background/input fixes are in `portal-background-fixes.patch`.
