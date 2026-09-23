# Desktop benchmark rules

Use only the `cua_repl` MCP tools for desktop interaction. Do not use shell commands, direct
filesystem access, browser automation, or process-control tools. Do not change global focus or
call `hyprctl`. Inspect the app again after a mutation when success is not visible. Bind dialogs
with `getDialog`. Stop when the task is complete or the step limit is reached. Never claim
success based only on a tool acknowledgement.
