---
name: herdr
description: >
  Control Herdr, a terminal multiplexer for coding agents. Only when the user
  explicitly mentions Herdr or asks to inspect or control its panes, tabs,
  workspaces or another agent; not for generic background terminals,
  delegation or parallel work.
---

# Herdr

Stub: the installed binary is the authority. Load the real instructions with `herdr --skill`; for any command group's syntax, run the group bare (`herdr agent`, `herdr pane`, `herdr workspace`, ...).

If `herdr --skill` still demands `HERDR_ENV=1` unconditionally, the connection policy below overrides it.

## Connection

- Inside Herdr (`HERDR_ENV=1`): use the inherited context.
- Outside: an explicit user-supplied socket/session is enough. Pass it on every command (`HERDR_SOCKET_PATH=/path herdr agent list`).
- Neither available: ask which session. Never attach to the user's focused session silently.
- Never set `HERDR_ENV=1` to pose as inside. Outside Herdr, use explicit pane IDs or agent names, never `--current` or implicit focus.

## Traps

- Most commands return JSON: parse IDs, never guess them.
- Bare `herdr` launches the TUI. Mutating commands run with defaults when given no arguments (`herdr workspace create`), so don't probe them.
