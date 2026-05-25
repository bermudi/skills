#!/usr/bin/env bash
# litespec-pipeline review panel — spawn, poll, and report.
#
# Usage:
#   review-panel.sh --change <name> [options]
#
# Creates a zellij session, spawns named panes for each reviewer,
# polls until all finish, and prints a status report.
#
# Options:
#   --change <name>          Litespec change name (required)
#   --session <name>         Zellij session name (default: review-<change>)
#   --config <file>          Config file (default: .litespec-pipeline.yaml or default-panel.yaml)
#   --output <dir>           Output directory (default: /tmp/litespec-pipeline-<change>)
#   --no-cleanup             Don't kill the zellij session after completion
#   -h, --help               Show this help

set -euo pipefail

PROG="$(basename "$0")"
CHANGE=""
SESSION=""
CONFIG=""
OUTDIR=""
CLEANUP=1

while [[ $# -gt 0 ]]; do
    case $1 in
        --change)         CHANGE="$2"; shift 2 ;;
        --session)        SESSION="$2"; shift 2 ;;
        --config)         CONFIG="$2"; shift 2 ;;
        --output)         OUTDIR="$2"; shift 2 ;;
        --no-cleanup)     CLEANUP=0; shift ;;
        -h|--help)
            sed -n '/^# Usage:/,/^#   -h/p' "$0"
            exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$CHANGE" ]]; then
    echo "Error: --change is required" >&2
    echo "Usage: $PROG --change <name> [--session <name>] [--config <file>]" >&2
    exit 1
fi

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SESSION="${SESSION:-review-$CHANGE}"
OUTDIR="${OUTDIR:-/tmp/litespec-pipeline-$CHANGE}"

# Find config file
if [[ -z "$CONFIG" ]]; then
    if [[ -f ".litespec-pipeline.yaml" ]]; then
        CONFIG=".litespec-pipeline.yaml"
    else
        CONFIG="$SKILL_DIR/assets/default-panel.yaml"
    fi
fi

# Read reviewer list from YAML
parse_reviewers() {
    python3 -c '
import yaml, sys, json
try:
    data = yaml.safe_load(open(sys.argv[1]))
    for r in data.get("reviewers", []):
        provider = r.get("provider", "")
        print(f"{r["tool"]}:{r["model"]}:{provider}:{r.get("label", "")}")
except Exception as e:
    sys.stderr.write(f"yaml error: {e}\n")
    sys.exit(1)
' "$1"
}

REVIEWERS=()
while IFS= read -r line; do
    REVIEWERS+=("$line")
done < <(parse_reviewers "$CONFIG" 2>/dev/null || true)

if [[ ${#REVIEWERS[@]} -eq 0 ]]; then
    echo "Warning: no reviewers found in config, using hardcoded defaults" >&2
    REVIEWERS=(
        "pi:glm-5.1:zai:GLM-5.1"
        "pi:deepseek-v4-pro:opencode-go:DeepSeek-V4-Pro"
        "devin:kimi-k2.6::Kimi-K2.6"
    )
fi

echo "[$PROG] Change: $CHANGE"
echo "[$PROG] Session: $SESSION"
echo "[$PROG] Config: $CONFIG"
echo "[$PROG] Reviewers: ${#REVIEWERS[@]}"

# Ensure output dirs exist
mkdir -p "$OUTDIR/reviews" "$OUTDIR/sessions"

# Create zellij session
echo "[$PROG] Creating zellij session..."
if zellij attach "$SESSION" --create-background 2>/dev/null; then
    echo "[$PROG] Session ready"
else
    echo "[$PROG] Warning: could not create session, is zellij installed?" >&2
    exit 1
fi

export ZELLIJ_SESSION_NAME="$SESSION"
CWD="$(pwd)"

# Helper: build the command for a reviewer
build_command() {
    local tool="$1" model="$2" provider="$3" label="$4"
    local sessdir="$OUTDIR/sessions/${label}"
    local outfile="$OUTDIR/reviews/${tool}-${model//\//-}.md"
    local logfile="$OUTDIR/reviews/${tool}-${model//\//-}.log"

    mkdir -p "$sessdir"

    case "$tool" in
        pi)
            local prov_flag=""
            if [[ -n "$provider" ]]; then
                prov_flag="--provider $provider"
            fi
            echo "pi -p $prov_flag --model '$model' --session-dir '$sessdir' 'Review litespec change $CHANGE' > '$outfile' 2>'$logfile'; echo DONE"
            ;;
        devin)
            echo "devin -p --model '$model' --permission-mode dangerous -- 'Review litespec change $CHANGE' > '$outfile' 2>'$logfile'; echo DONE"
            ;;
        agent)
            echo "agent -p --model '$model' --trust 'Review litespec change $CHANGE' > '$outfile' 2>'$logfile'; echo DONE"
            ;;
        *)
            echo "Error: unknown tool '$tool'" >&2
            exit 1
            ;;
    esac
}

# Spawn reviewers
echo "[$PROG] Spawning reviewers..."
for reviewer in "${REVIEWERS[@]}"; do
    IFS=: read -r tool model provider label <<< "$reviewer"
    safe_label="${label:-${tool}-${model}}"
    safe_label="${safe_label//\//-}"

    CMD=$(build_command "$tool" "$model" "$provider" "$safe_label")

    echo "[$PROG]   → $safe_label ($tool / $model)"
    zellij run -n "$safe_label" --cwd "$CWD" -- \
        bash -c "$CMD" &
done

sleep 2

# Verify panes exist
mapfile -t PANES < <(zellij action list-panes --json 2>/dev/null | jq -r '.[].title')
echo "[$PROG] Active panes: ${PANES[*]}"

# Wait for completion
echo "[$PROG] Waiting for all reviewers... (watch: zellij attach $SESSION)"
ELAPSED=0
while true; do
    # Get exited status for all reviewer-named panes
    mapfile -t STATES < <(zellij action list-panes --json 2>/dev/null | jq -r '.[] | select(.title | test("GLM|DeepSeek|Kimi|glm|deepseek|kimi")) | .exited')

    ALL_DONE=1
    for state in "${STATES[@]}"; do
        if [[ "$state" != "true" ]]; then
            ALL_DONE=0
            break
        fi
    done

    if [[ $ALL_DONE -eq 1 ]]; then
        echo "[$PROG] All reviewers finished (${ELAPSED}s elapsed)"
        break
    fi

    sleep 10
    ELAPSED=$((ELAPSED + 10))
done

# Collect results
echo ""
echo "=== Review Results ==="

FAILED=0
for reviewer in "${REVIEWERS[@]}"; do
    IFS=: read -r tool model provider label <<< "$reviewer"
    safe_label="${label:-${tool}-${model}}"
    outfile="$OUTDIR/reviews/${tool}-${model//\//-}.md"
    logfile="$OUTDIR/reviews/${tool}-${model//\//-}.log"

    SIZE=$(wc -c < "$outfile" 2>/dev/null || echo 0)
    if [[ "$SIZE" -gt 200 ]]; then
        echo "✓ $safe_label  ($SIZE bytes)"
    else
        echo "✗ $safe_label  FAILED (${SIZE} bytes)"
        if [[ -f "$logfile" ]]; then
            echo "    Last log lines:"
            tail -3 "$logfile" | sed 's/^/      /' >&2
        fi
        FAILED=1
    fi
done

echo ""
echo "Output directory: $OUTDIR/reviews"

# Cleanup
if [[ $CLEANUP -eq 1 ]]; then
    echo "[$PROG] Killing session $SESSION"
    zellij action kill-session 2>/dev/null || true
fi

exit $FAILED
