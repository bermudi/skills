#!/usr/bin/env bash
# pull_colab_output.sh — extract a file from the connected Colab VM to local,
# via chunked base64 through the colab-mcp bridge.
#
# WHY THIS EXISTS: Colab free runtimes disconnect on idle. The only safe copy of
# a transcript must not live in the VM. Run this the INSTANT rendering finishes.
#
# Usage: pull_colab_output.sh <remote_path> <local_out> [cellId]
#   remote_path : path inside the Colab VM, e.g. /content/work/x.json
#   local_out   : local destination path
#   cellId      : optional scratch code cell to reuse (else one is added)
#
# Prereqs:
#   - mcporter installed
#   - colab-mcp connected: open_colab_browser_connection done AND the 8 editing
#     tools visible (`mcporter list colab-mcp --schema | grep -c function` == 8).
#     If it shows 1, reconnect and wait ~10s (see references/colab-mcp-playbook.md).
set -euo pipefail

REMOTE="${1:?usage: pull_colab_output.sh <remote_path> <local_out> [cellId]}"
LOCAL="${2:?local_out required}"
CELL="${3:-}"

command -v mcporter >/dev/null || { echo "mcporter not found" >&2; exit 1; }

# sanity: are the editing tools live?
if [ "$(mcporter list colab-mcp --schema 2>/dev/null | grep -c function)" -lt 8 ]; then
  echo "ERROR: colab-mcp editing tools not visible. Run open_colab_browser_connection," >&2
  echo "       wait ~10s, and re-check \`mcporter list colab-mcp\` shows 8 tools." >&2
  exit 1
fi

# reuse or create a scratch cell
if [ -z "$CELL" ]; then
  CELL="$(mcporter call colab-mcp.add_code_cell --timeout 60000 \
            cellIndex=0 language=python code='_' 2>/dev/null \
          | python3 -c 'import sys,json;print(json.load(sys.stdin).get("newCellId",""))')"
fi
[ -n "$CELL" ] || { echo "ERROR: no cellId (add_code_cell failed)" >&2; exit 1; }

# get the remote file size
SIZE="$(mcporter call colab-mcp.update_cell --timeout 60000 cellId="$CELL" \
          content="import os;print(os.path.getsize('$REMOTE'))" >/dev/null 2>&1
        mcporter call colab-mcp.run_code_cell --timeout 60000 cellId="$CELL" 2>/dev/null \
          | python3 -c 'import sys,json
d=json.load(sys.stdin); b=""
for x in d.get("outputs",[]):
    if x.get("output_type")=="stream": b+="".join(x.get("text",[]))
print(b.strip())')"
[ -n "$SIZE" ] && [ "$SIZE" -gt 0 ] 2>/dev/null || {
  echo "ERROR: could not stat $REMOTE (wrong path? runtime gone?)" >&2; exit 1; }

CHUNK=26000   # raw bytes per chunk (~35KB base64; stays under shell output limits)
NCHUNKS=$(( (SIZE + CHUNK - 1) / CHUNK ))
B64="$(mktemp)"; : > "$B64"

for (( i=0; i<NCHUNKS; i++ )); do
  OFF=$(( i * CHUNK ))
  mcporter call colab-mcp.update_cell --timeout 60000 cellId="$CELL" >/dev/null 2>&1 \
    content="import base64
_d=open('$REMOTE','rb').read()
print(base64.b64encode(_d[$OFF:$OFF+$CHUNK]).decode())"
  OUT="$(mcporter call colab-mcp.run_code_cell --timeout 90000 cellId="$CELL" 2>/dev/null \
    | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin); b=""
    for x in d.get("outputs",[]):
        if x.get("output_type")=="stream": b+="".join(x.get("text",[]))
        elif x.get("output_type")=="error": sys.stderr.write(x.get("evalue",""))
    sys.stdout.write(b.strip())
except Exception as e:
    sys.stderr.write(str(e))')" || true
  [ -n "$OUT" ] || { echo "ERROR: empty chunk $((i+1))/$NCHUNKS at offset $OFF" >&2; rm -f "$B64"; exit 1; }
  printf '%s' "$OUT" >> "$B64"
done

python3 -c "import base64; open('$LOCAL','wb').write(base64.b64decode(open('$B64').read()))"
rm -f "$B64"
echo "pulled $REMOTE -> $LOCAL ($(wc -c < "$LOCAL") bytes, $NCHUNKS chunks)"
