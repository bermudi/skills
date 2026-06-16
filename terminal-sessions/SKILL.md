---
name: terminal-sessions
description: >
  Use this skill when terminal work needs a durable or interactive session:
  dev servers, watchers, REPLs, TUIs, prompts, readiness gates, log monitoring,
  or typed input. Do not use for ordinary one-shot shell commands, including long
  builds or tests, unless they require interactive control or later inspection.
---

# Terminal Sessions

Use `boo` only when terminal state has to survive beyond a single command invocation. If a command simply runs to completion, run it directly with bash.

## Route before you run

- **Direct shell:** one-shot builds, tests, linters, codegen, searches, scripts, and any command where final stdout/stderr/exit code is enough.
- `boo`: dev servers, watchers, daemons, REPLs, TUIs, command prompts, or programs that need typed input.
- `boo`: commands that need a readiness gate before other work proceeds, then keep running while you edit/test elsewhere.
- `boo`: sessions you need to inspect later with terminal screen state or scrollback.
- `boo`: multiple independent terminal jobs that need continued monitoring; use one session per job.

## If you choose boo

Read `references/boo.md` before the first `boo` command in the task. It covers the command set, recipes, and the sharp edges that matter during automation.

Default loop:

1. Pick a unique, purpose-specific session name.
2. Start detached: `boo new <name> -d -- <command>`.
3. Prefer a readiness gate: `boo wait <name> --text '<ready marker>' --timeout <duration>`.
4. Use `boo peek <name>` for current screen state; use `boo peek <name> --scrollback` for history.
5. Send input only when needed: `boo send <name> --text '<literal text>' --enter` or `boo send <name> --key C-c`.
6. Kill sessions when they are no longer needed: `boo kill <name>`.

## Gotchas to keep in working memory

- `send --text` is literal: no shell escaping and no implicit Enter. Add `--enter` when the program needs Enter.
- `send --key` and `send --text` cannot be combined; use separate calls.
- `wait --text` and plain `peek` match the rendered screen, not all prior output. Use `peek --scrollback` when debugging history.
- `wait --idle` means “no output for 2 seconds,” not “the process finished.”
- `wait` exits `4` on timeout. Treat that as a real branch: inspect scrollback, adjust the readiness marker, or stop the session.
- Avoid blind sleeps for readiness. Wait on the program's actual ready text whenever it has one.
