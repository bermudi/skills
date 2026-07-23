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

## Colab MCP: Hard-Learned Caveats

The Colab MCP server (`colab-mcp`) has a fragile connection model that will
bite you if you don't understand it. These are all things we learned the hard
way.

### How the Connection Works

1. The MCP server runs a local WebSocket server on a random port with a random
   auth token.
2. `open_colab_browser_connection` opens a browser tab to
   `colab.research.google.com/notebooks/empty.ipynb#mcpProxyToken=<token>&mcpProxyPort=<port>`.
3. The Colab frontend in that tab connects back to the local WebSocket.
4. The MCP proxies all tool calls through that WebSocket.

The connection is **single-client exclusive** — a new tab connecting will kick
out the old one.

### Never Call `open_colab_browser_connection` Twice

Each call opens a **new** browser tab with a **new** token and port. The new
tab's connection replaces the old one (single-client lock). The old tab is
orphaned — its WebSocket is severed and it cannot auto-reconnect.

If `open_colab_browser_connection` times out (e.g. because the first call
succeeded but a subsequent tool call took longer than the timeout), **do not
call it again**. The server process is still running with the original
connection. Calling again will open a new tab and destroy the original
connection.

If the server restarted, call **`reconnect_colab_session`** instead. It waits
for the existing tab to reconnect without opening a new one.
`open_colab_browser_connection` will refuse to open a new tab if a persisted
session exists, which prevents orphaned tabs.

Instead: check `mcporter list colab-mcp` — if the tools are still there, the
connection is still live. If the tools dropped to just `open_colab_browser_connection`
and `reconnect_colab_session`, the connection was lost and you should use
`reconnect_colab_session` after the server restarts.

### Scratch Notebooks Don't Survive Refreshes

`empty.ipynb` is a **scratch notebook**. Cells added via the MCP are never saved
to a persistent file. If the user refreshes the tab, **all cells are lost**.
The kernel may keep running (in-memory state persists briefly), but the notebook
UI resets to a single empty cell.

**Never tell the user to refresh a Colab scratch notebook tab.** If you need
persistence, have the user save a copy to Drive first (`File > Save a copy in
Drive`).

### Long-Running Cells Block Everything

Colab executes cells sequentially. If a cell is running (e.g. embedding 25k
messages), no other cell can execute — `run_code_cell` will time out waiting
for the kernel to become available. There is no way to interrupt a running
cell through the MCP.

For long-running jobs, put the **entire pipeline in a single cell** — load
data, process, save output, trigger download — so it runs unattended without
needing MCP interaction mid-run.

### The MCP Server Process Can Die Silently

mcporter manages the MCP server process with a `keep-alive` lifecycle, but if a
tool call times out, mcporter may kill the server. The patched `colab-mcp`
server persists its WebSocket token and port to
`~/.local/share/colab-mcp/session.json`, so a restart reuses the same endpoint.

To reconnect after a restart:

1. Call `reconnect_colab_session` — it does **not** open a new tab.
2. Refresh the existing Colab tab. Because the endpoint is unchanged, the
   frontend reconnects instead of starting a new session.
3. For long jobs, use a **saved notebook** (not `empty.ipynb`) so the refresh
   doesn't destroy your cells.

### Practical Pattern for Long Jobs

1. Build the notebook in a **saved** notebook (not `empty.ipynb`)
2. Put the entire pipeline in **one cell** — no MCP interaction needed mid-run
3. Have the cell **save to Google Drive** as a checkpoint, not just `/content/`
4. Have the cell trigger `files.download()` at the end
5. Don't touch the tab while it's running
6. If the MCP connection drops, just wait — the kernel keeps running
