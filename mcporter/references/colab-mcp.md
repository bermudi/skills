# Colab MCP: Hard-Learned Caveats

`colab-mcp` proxies tool calls over a local WebSocket opened from a Colab browser tab. Its connection is **single-client exclusive** — a second tab connecting kicks out the first and severs its WebSocket permanently.

## Connecting & reconnecting

- **Never call `open_colab_browser_connection` twice** while a session is alive or after a subsequent tool call times out — the server is still running with the original tab, and a second call opens a new tab that orphans the first. (If a tab is already connected, `open_colab_browser_connection` returns `true` immediately.)
- **If the server process died/restarted** (e.g., mcporter killed keep-alive after a timeout): the patched server persists its WebSocket token and port in `~/.local/share/colab-mcp/session.json`, so restarts reuse the endpoint. Reconnect one of two ways:
  1. **`reconnect_colab_session`** + user refreshes the existing tab — keeps the same tab/notebook (only safe on a **saved** notebook, never a scratch notebook).
  2. **`open_colab_browser_connection`** — opens a fresh tab to the persisted URL (disconnects any old tab). Use this when the old tab is gone or you want a fresh one.

## Scratch notebooks don't survive refreshes

`empty.ipynb` is a **scratch notebook** — cells added via MCP are never saved. Refreshing the tab wipes all cells back to one empty cell (even if the kernel briefly keeps running). **Never tell the user to refresh a scratch notebook.** Have them save a copy to Drive first (`File > Save a copy in Drive`).

## Long-running cells block everything

Colab runs cells sequentially and the MCP cannot interrupt a running cell. While a long cell executes, `run_code_cell` times out waiting for the kernel.

**Pattern for long jobs:**
1. Work in a **saved** notebook (not `empty.ipynb`).
2. Put the entire pipeline in **one cell** so no mid-run MCP interaction is needed.
3. Checkpoint outputs to **Google Drive** (not only `/content/`), then trigger `files.download()` at the end.
4. Leave the tab alone while running; if the MCP connection drops, wait — the kernel keeps executing.
