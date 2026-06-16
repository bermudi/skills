---
name: terminal-sessions
description: >
  Drive durable or interactive terminal sessions: dev servers, REPLs, TUIs,
  and programs you need to start now and inspect later. Use when a command
  needs a readiness gate before you proceed, produces output you must monitor
  or read back while it keeps running, or needs typed input sent to an
  interactive program. Do not use for one-shot commands — even long builds
  or tests — run those directly with bash.
---

# Terminal Sessions

One routing rule: **if it needs a durable or interactive terminal session, use `boo`; otherwise run one-shot commands directly with bash.**

## Decision Tree

```
What are you doing?
│
├─ One-shot command (even a long build/test) → direct shell (bash)
│
├─ Output over time, wait on readiness, or inspect later → boo
│
├─ Drive an interactive program (REPL, TUI, prompts) → boo
│
└─ Multiple terminal tasks in parallel → boo (multiple sessions)
```

## Read the reference before you act

`boo` has non-obvious behavior that will bite you. On your first session, read its reference first — not as background, but before you spawn or drive anything.

- **boo** → `references/boo.md`. Two sharp edges to know up front: `send --text` is literal — no implicit Enter, no shell escaping — and `wait`/`peek` match the *rendered screen*, not scrollback. The reference covers the command set, core loop, recipes, and gotchas.
