---
name: herdr
description: "Control Herdr, a terminal multiplexer for coding agents. Use only when the user explicitly mentions Herdr or asks to use Herdr to inspect or control panes, tabs, workspaces, commands, or another agent. Do not use merely because a task could benefit from a background terminal, delegation, or parallel work. Requires HERDR_ENV=1."
---

# Herdr

This is a discovery stub — the installed `herdr` binary is the authority and its embedded skill always matches the running version.

Before any control command, verify you are inside Herdr:

```bash
test "${HERDR_ENV:-}" = 1
```

If that fails, stop. Do not control the user's focused session from outside Herdr.

## Get the real instructions

Load the full skill from the binary (pane vs agent model, IDs, start/prompt/wait, safety):

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
