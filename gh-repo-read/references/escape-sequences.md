# Escape-Sequence Safety in `gh repo read-file`

By default `read-file` **refuses to print files containing terminal escape
sequences** to a terminal or pipe — a guard against malicious content that
could manipulate your terminal. It will error rather than emit them.

## Getting the file anyway

- Use `--allow-escape-sequences`, **or**
- Write to disk with `--output` — disk writes always contain the raw bytes
  (equivalent to `--allow-escape-sequences`), where the bytes can't hijack a
  terminal.

## What the guard keys on

The guard keys on **literal ESC (`0x1b`) bytes** — actual ANSI/CSI sequences.
Files that merely *look* escapey (zsh `%{$fg[green]%}` prompt syntax, `$\033`-
as-text in source) are not blocked, and arbitrary binaries are only blocked if
they happen to contain an `0x1b` byte.

## When in doubt

`--output` to a temp path and read it back, rather than streaming to stdout.
