# colab-mcp playbook

How to drive a Colab notebook remotely through the **colab-mcp** bridge via
`mcporter`. Source of truth for the bridge's quirks; verified live 2026-07.
Bridge source lives at `~/build/colab-mcp/` (notably `src/colab_mcp/session.py`).

## The tools

After a successful `open_colab_browser_connection`, `mcporter list colab-mcp
--schema` shows 8 tools:

```
open_colab_browser_connection()                          # (re)connect; returns {result: bool}
add_code_cell(cellIndex, language, code) -> {newCellId}  # NOTE the key: "newCellId"
add_text_cell(cellIndex, content)
update_cell(cellId, content)
delete_cell(cellId)
move_cell(cellId, cellIndex)
get_cells(cellIndexStart?, cellIndexEnd?, includeOutputs?)   # read cells + their outputs
run_code_cell(cellId)                                    # BLOCKS until the cell finishes
```

## Connecting (and the tool-gating gotcha)

1. `mcporter call colab-mcp.open_colab_browser_connection --timeout 60000`.
   Returns `{"result": true}` — but that only means the local websocket server
   started. The browser **front-end** may not be connected yet.
2. `mcporter list colab-mcp --schema | grep -c function` — until the FE
   reconnects this prints **1** (only `open_colab_browser_connection`). Every
   other tool will report `Unknown tool`.
3. **Wait ~10 s and re-list.** Once it prints **8**, the editing tools are live.
   Don't call `update_cell`/`run_code_cell` before that.

The scratch notebook's cells (the *document*) persist across a runtime
disconnect; the kernel *variables* do not. After a reconnect, expect an empty
kernel but the same cell IDs — probe with `get_cells` to see what survived.

## The timeout trap (the big one)

`run_code_cell` is a proxied, **blocking** call: mcporter → stdio → colab-mcp →
websocket → browser, and it does not return until the cell finishes.

- mcporter's **default per-call timeout is 120 s.** A transcribe/diarize cell
  runs minutes.
- When the timeout fires, mcporter kills the in-flight call and tears down the
  proxy connection (`connection_live` is cleared; "colab-mcp appears offline").
- The cell may still be running in Colab — the kill is local to the bridge.
- **Recovery mistake to avoid:** calling `open_colab_browser_connection` now.
  Its `check_session_proxy_tool_fn` (in `session.py`) sees `fe_connected ==
  False` and runs `webbrowser.open_new(...)`, which **opens a new Colab window
  and forces a "Connect" click.** (This is the intended "connect me" behaviour,
  but it's the wrong tool for recovering from a local timeout.)

**Mitigations:**
- **Long cells get a long timeout:**
  `mcporter call colab-mcp.run_code_cell --timeout 900000 cellId=...` (15 min).
  And raise the surrounding shell (`bash`) timeout above it, in seconds
  (e.g. `--timeout 960`), so the shell doesn't kill mcporter first.
- **After a timed-out call, poll with `get_cells`** (read the cell's tail output
  for progress) — do not call `open_colab_browser_connection`.
- Only reconnect if `get_cells` itself fails (genuine FE drop), not because a
  long cell is still running.

## Driving a kernel restart (e.g. after the environment install)

Some installs (the numpy/torch fix in `whisperx-stack.md`) require restarting the
kernel so the new packages load. There's no restart tool — do it from a cell:

```python
import os; os.kill(os.getpid(), 9)
```

- Colab **auto-restarts** a crashed kernel (a few seconds). The colab-mcp bridge
  survives it — it's tied to the browser *page*, not the kernel.
- The `run_code_cell` that ran the kill returns empty/no output (the kernel died
  mid-cell). That's expected; don't treat it as a hard failure.
- After ~10–15 s, run a **probe cell** (`print(sys.version)` etc.) to confirm the
  new kernel is up. If the probe errors, the auto-restart may need a moment —
  wait and retry. If the FE itself dropped (probe call errors at the MCP level),
  *then* `open_colab_browser_connection`.
- All kernel variables are gone after a restart; the cell *contents* persist.

## Working pattern

- **Reuse one scratch cell** by `update_cell(cellId, content)` then
  `run_code_cell(cellId)`, overwriting per step. Cheaper than managing indices.
  (Or `add_code_cell` to build a record; remember the return key is
  `newCellId`.)
- **Parse outputs** — `run_code_cell` returns JSON:
  `{"outputs":[{"output_type":"stream","name":"stdout","text":[...]}, ...]}`.
  Pull stdout/stderr with a one-liner, and surface `error` outputs:
  ```bash
  mcporter call colab-mcp.run_code_cell --timeout 90000 cellId="$CID" 2>/dev/null \
    | python3 -c '
  import sys,json
  d=json.load(sys.stdin)
  for x in d.get("outputs",[]):
      if x.get("output_type")=="stream":  print("".join(x.get("text",[])).rstrip())
      elif x.get("output_type")=="error": print("ERROR:",x.get("ename"),"|",x.get("evalue"))
  '
  ```
- **Never block blindly on long cells.** Either pass a long `--timeout`, or
  dispatch a short timeout and poll `get_cells(cellIndexStart=N
  cellIndexEnd=N includeOutputs=true)` until the cell shows a completed output.
