---
name: herdr
description: "Control Herdr, a terminal multiplexer for coding agents. Use only when the user explicitly mentions Herdr or asks to use Herdr to inspect or control panes, tabs, workspaces, commands, or another agent. Do not use merely because a task could benefit from a background terminal, delegation, or parallel work. Use the inherited Herdr context or a socket/session explicitly supplied by the user."
---

# Herdr

This is a discovery stub — the installed `herdr` binary is the authority and its embedded skill always matches the running version.

Before any control command, establish the intended Herdr connection:

- Inside Herdr (`HERDR_ENV=1`), use the inherited connection context.
- Outside Herdr, an explicit user-provided socket or session is sufficient authorization to connect. Pass that connection explicitly on every command; for example, `HERDR_SOCKET_PATH=/path/from/user herdr agent list`.
- If neither inherited context nor an explicit user-provided connection is available, ask which session to use. Do not silently attach to the user's focused session.

Do not set `HERDR_ENV=1` to pretend this agent is inside Herdr. Use explicit pane IDs or agent names when operating from outside Herdr; do not use `--current` or implicit focus.

## Get the real instructions

Load the full skill from the binary (pane vs agent model, IDs, start/prompt/wait, safety). Its command documentation is authoritative for the installed version. If its embedded skill still requires `HERDR_ENV=1` unconditionally, use the explicit-connection policy above instead; being outside Herdr alone is not a reason to refuse a user-specified connection:

```bash
herdr --skill
```

For syntax of any group, run the group without a subcommand:

```bash
herdr --help
herdr agent
herdr pane
herdr workspace
herdr tab
herdr worktree
herdr terminal
herdr notification
herdr integration
herdr session
```

Most commands return JSON — parse IDs from the response, never guess them. Do not run bare `herdr` for discovery (it launches the TUI) and do not probe mutating commands like `herdr workspace create` without arguments — they execute with defaults.
