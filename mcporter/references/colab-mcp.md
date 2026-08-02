# Colab MCP: Hard-Learned Caveats

The Colab MCP server (`colab-mcp`) has a fragile connection model that will
bite you if you don't understand it. These are all things we learned the hard
way.

## How the Connection Works

1. The MCP server runs a local WebSocket server on a random port with a random
   auth token.
2. `open_colab_browser_connection` opens a browser tab to
   `colab.research.google.com/notebooks/empty.ipynb#mcpProxyToken=<token>&mcpProxyPort=<port>`.
3. The Colab frontend in that tab connects back to the local WebSocket.
4. The MCP proxies all tool calls through that WebSocket.

The connection is **single-client exclusive** — a new tab connecting will kick
out the old one.

## Never Call `open_colab_browser_connection` Twice

Each call opens a **new** browser tab with a **new** token and port. The new
tab's connection replaces the old one (single-client lock). The old tab is
orphaned — its WebSocket is severed and it cannot auto-reconnect.

If `open_colab_browser_connection` times out (e.g. because the first call
succeeded but a subsequent tool call took longer than the timeout), **do not
call it again**. The server process is still running with the original
connection. Calling again will open a new tab and destroy the original
connection.

If the server restarted, you have two options:

1. Call **`reconnect_colab_session`** and refresh the existing Colab tab. This
   keeps the same notebook and does not open a new tab.
2. Call **`open_colab_browser_connection`** to open a fresh copy of the same
   persisted URL in a new tab. The single-client lock will disconnect the old
   tab.

If a tab is already connected, `open_colab_browser_connection` returns `true`
immediately. Use `reconnect_colab_session` when you want to keep the existing
browser tab; use `open_colab_browser_connection` when the old tab is gone or
you want a fresh one.

## Scratch Notebooks Don't Survive Refreshes

`empty.ipynb` is a **scratch notebook**. Cells added via the MCP are never saved
to a persistent file. If the user refreshes the tab, **all cells are lost**.
The kernel may keep running (in-memory state persists briefly), but the notebook
UI resets to a single empty cell.

**Never tell the user to refresh a Colab scratch notebook tab.** If you need
persistence, have the user save a copy to Drive first (`File > Save a copy in
Drive`).

## Long-Running Cells Block Everything

Colab executes cells sequentially. If a cell is running (e.g. embedding 25k
messages), no other cell can execute — `run_code_cell` will time out waiting
for the kernel to become available. There is no way to interrupt a running
cell through the MCP.

For long-running jobs, put the **entire pipeline in a single cell** — load
data, process, save output, trigger download — so it runs unattended without
needing MCP interaction mid-run.

## The MCP Server Process Can Die Silently

mcporter manages the MCP server process with a `keep-alive` lifecycle, but if a
tool call times out, mcporter may kill the server. The patched `colab-mcp`
server persists its WebSocket token and port to
`~/.local/share/colab-mcp/session.json`, so a restart reuses the same endpoint.

To reconnect after a restart:

1. Call `reconnect_colab_session` — it does **not** open a new tab — then
   refresh the existing Colab tab.
2. Or call `open_colab_browser_connection` to open a fresh copy of the same
   persisted URL in a new tab.
3. For long jobs, use a **saved notebook** (not `empty.ipynb`) so the refresh
   doesn't destroy your cells.

## Practical Pattern for Long Jobs

1. Build the notebook in a **saved** notebook (not `empty.ipynb`)
2. Put the entire pipeline in **one cell** — no MCP interaction needed mid-run
3. Have the cell **save to Google Drive** as a checkpoint, not just `/content/`
4. Have the cell trigger `files.download()` at the end
5. Don't touch the tab while it's running
6. If the MCP connection drops, just wait — the kernel keeps running
