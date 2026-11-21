---
name: mcporter
description: >
  Use when calling or configuring MCP servers through mcporter.
---

# mcporter

CLI bridge to MCP servers (`mcporter call server.tool key=value`). `mcporter --help`, `call --help`, `list --help`, `config --help` cover usage; this skill covers what they don't.

## Two timeouts

mcporter's `--timeout` (ms, default 60s) and the host's outer command timeout (seconds in Pi; ms in Claude Code / Devin CLI). **Outer timeout must strictly exceed `--timeout`.** mcporter's own timeout returns a readable error; the outer one SIGKILLs it, so a call that vanishes with no error means the outer fired first.

Set `--timeout` explicitly: ~15s local/fast, ~120s single call, ~300s video or deep research. With no configurable outer timeout, keep `--timeout` under the host's hard limit.

## Argument coercion gotcha

`mcporter call` coerces numeric- and boolean-looking `key=value` args into numbers/booleans. For string IDs like `"00123"` or literal `"true"`, pass `--raw-strings` / `--no-coerce` or JSON via `--args '{...}'`.

## Dynamic tool surfaces

Stateful servers (Colab) change their tool list mid-session. On "tool not found", re-run `mcporter list <server> --schema` and retry with current names.

## MCP 2.0: bridge, not mediator

- Servers may pause a call to elicit input (forms, URLs, auth). mcporter prompts only in a real terminal; under an agent shell, the daemon, or `serve`, it declines immediately with `Server requested interactive input; run mcporter in a terminal.` Only a harness-embedded client can mediate this.
- Avoid elicitation: pass complete args (`--args '{...}'`, shape from `list <server> --schema`) and pre-authenticate with `mcporter config login <server>` (`--no-browser` prints a URL for the user). If it still declines, the server wants a human decision: tell the user, don't guess.
- A server that misbehaves under MCP 2.0 (handshake loops, dropped tools) can be pinned per server with `protocolVersion` (`auto` | `legacy` | `2026-07-28`). Check with `mcporter config get <server>`.

## Colab MCP

Its connection model is fragile and single-client (double-opening a tab orphans the old connection, scratch notebooks lose cells on refresh, long cells block the kernel, the server can die silently). Read `references/colab-mcp.md` before driving it.
