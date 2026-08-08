---
name: mcporter
description: >
  Use when calling or configuring MCP servers through mcporter.
---

# mcporter

CLI bridge to MCP servers: `mcporter call server.tool key=value`.

The CLI documents itself. For invocation, arguments, output, tool discovery, and
config, run:

```
mcporter --help
mcporter call --help
mcporter list --help
mcporter config --help
```

This skill covers only the two things those won't tell you.

## Two Timeouts

Every non-trivial call involves **two** timeouts you control:

- **mcporter `--timeout`** (ms) — how long mcporter waits for the server.
- **the outer timeout** bounding the shell command that runs mcporter (seconds)
  — whatever your host uses to limit command execution (the `bash` tool's
  `timeout` parameter in pi/Claude Code; Devin and others have their own
  equivalent). Set that one.

**The outer timeout (seconds) must be strictly greater than mcporter ms ÷ 1000.**

mcporter returns a clean, readable error when *its* timeout fires. The outer
expiry *SIGKILLs* the process — no result, no error, just silence. A call that
vanishes without an error almost always means the outer timeout fired first and
killed mcporter before it could report.

```text
# outer timeout=600s (bash max), mcporter --timeout 540000 (ms = 540s)
# 600 > 540  → mcporter times out first, returns an error  ✓
# ≤ 540      → outer kill → silence                        ✗
```

If your host exposes no configurable outer timeout, mcporter's `--timeout` is
your only lever — set it comfortably *under* the host's hard limit so mcporter
returns an error instead of getting killed.

The default `--timeout` is 60s — too short for most remote/AI tools. Set it
explicitly: local/fast ~15s, single call ~120s, video or deep research ~300s.

## Dynamic Tool Surfaces

Some servers (Colab is the example) change their tool list with session state.
If a call fails with "tool not found" or "not a known tool", the surface
shifted under you — re-run `mcporter list <server> --schema` and retry with the
current names. Don't assume a tool list you saw earlier still holds for
stateful servers.

## MCP 2.0: Bridge, Not Mediator

mcporter speaks MCP 2026-07-28 (MCP 2.0) and every legacy revision back to
2024-10-07, negotiating each server automatically. Know its limits:

- **Elicitation is user-facing by design.** The spec requires clients to
  show which server is asking, let the user review/decline, and get consent
  before URL navigation — servers MUST NOT use form elicitation for secrets.
  MCP 2.0 servers can pause a call and ask for input (forms, URLs, auth
  confirmations). mcporter only prompts in a real terminal; from an agent
  shell — and unconditionally in the daemon and `serve` bridge — it declines
  immediately, logging `Server requested interactive input; run mcporter in a
  terminal.` The serve bridge cannot pass elicitation through either. A CLI
  bridge has no user-interaction surface, so it cannot mediate this: the
  client must live in the harness itself (in pi, an extension embedding the
  MCP SDK v2 client with `ctx.ui`).
- **What you can do through mcporter:** pass complete arguments
  (`--args '{"...": ...}'`; see `mcporter list <server> --schema`) so servers
  never need to elicit; pre-authenticate auth-style servers with
  `mcporter config login <server>` (`--no-browser` prints a URL the user
  completes in a browser). If a call still declines with that hint, the server
  wants a human decision — tell the user and have them run it interactively;
  don't guess.
- **Pin a broken server to an older protocol.** Auto-negotiation is normally
  invisible, but a server can misbehave under MCP 2.0 (handshake loops, dropped
  tools, odd errors). Pin it per-server in config with `protocolVersion`
  (snake_case alias `protocol_version`): `auto` (default), `legacy`, or a
  pinned `2026-07-28`. Check the effective value with
  `mcporter config get <server>`.

## Colab MCP

The Colab MCP server (`colab-mcp`) has a fragile, single-client connection
model that bites you if you don't understand it — double-opening tabs orphans
the old connection, scratch notebooks lose cells on refresh, long-running cells
block the kernel, and the server process can die silently.

Read `references/colab-mcp.md` before driving `colab-mcp` (opening a session,
running cells, or recovering from a dropped connection). It covers the
connection model, the never-call-twice rule, scratch-vs-saved notebooks,
long-job patterns, and silent-restart recovery.
