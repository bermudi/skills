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
  — whatever your host uses to limit command execution. In pi that's the `bash`
  tool's `timeout` parameter; other hosts (Devin, Claude Code, …) have their own
  equivalent. You know your own tool — set that one.

**The outer timeout (seconds) must be strictly greater than mcporter ms ÷ 1000.**

mcporter returns a clean, readable error when *its* timeout fires. The outer
expiry *SIGKILLs* the process — no result, no error, just silence. A call that
vanishes without an error almost always means the outer timeout fired first and
killed mcporter before it could report.

```text
# outer timeout=660s, mcporter --timeout 600000 (ms = 600s)
# 660 > 600  → mcporter times out first, returns an error  ✓
# ≤ 600      → outer kill → silence                        ✗
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
