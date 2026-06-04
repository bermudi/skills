#!/usr/bin/env bash
# Apply all phases of a litespec change by repeatedly invoking an AI coding agent.
#
# Usage:
#   apply-phases.sh --change <name> --tool <tool:model> [options]
#
# The script loops:
#   1. Count unchecked boxes in tasks.md
#   2. If any remain, run the tool with the apply prompt
#   3. Repeat until all checked or progress stalls
#
# Outputs one .md file per iteration in the output directory.
set -euo pipefail

CHANGE=""
TOOL_SPEC=""
OUTPUT_DIR=""
MAX_ITERATIONS="${APPLY_MAX_ITERATIONS:-15}"
TIMEOUT="${APPLY_TIMEOUT:-300}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --change)         CHANGE="$2"; shift 2 ;;
        --tool)           TOOL_SPEC="$2"; shift 2 ;;
        --output)         OUTPUT_DIR="$2"; shift 2 ;;
        --max-iterations) MAX_ITERATIONS="$2"; shift 2 ;;
        --timeout)        TIMEOUT="$2"; shift 2 ;;
        -h|--help)
            cat <<'EOF'
Usage: apply-phases.sh --change <name> --tool <tool:model> [options]

Options:
  --change <name>         Litespec change name to apply
  --tool <tool:model>     Tool and model (e.g., agent:sonnet-4, pi:sonnet-4)
                          Tools: pi, devin, agent
  --output <dir>          Directory for phase outputs
  --max-iterations <N>    Max apply iterations (default: 15, env: APPLY_MAX_ITERATIONS)
  --timeout <seconds>     Per-iteration timeout (default: 300, env: APPLY_TIMEOUT)
  -h, --help              Show this help

Example:
  apply-phases.sh --change my-feature --tool agent:sonnet-4 --output /tmp/litespec-pipeline-my-feature/apply
EOF
            exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$CHANGE" || -z "$TOOL_SPEC" || -z "$OUTPUT_DIR" ]]; then
    echo "Error: --change, --tool, and --output are required" >&2
    echo "Run with --help for usage" >&2
    exit 1
fi

TOOL="${TOOL_SPEC%%:*}"
MODEL="${TOOL_SPEC#*:}"
if [[ "$TOOL" == "$MODEL" ]]; then
    echo "Error: --tool requires <tool:model> format (e.g., agent:auto, pi:sonnet-4)" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

TASKS_FILE="specs/changes/${CHANGE}/tasks.md"

if [[ ! -f "$TASKS_FILE" ]]; then
    echo "Error: No tasks.md found at ${TASKS_FILE}" >&2
    exit 1
fi

count_unchecked() {
    grep -cP '^\s*- \[ \]' "$1" 2>/dev/null || echo "0"
}

count_checked() {
    grep -cP '^\s*- \[x\]' "$1" 2>/dev/null || echo "0"
}

PROMPT="Use your litespec-build skill to implement the next phase of change '${CHANGE}'. Read specs/changes/${CHANGE}/tasks.md, implement the first unchecked phase, mark tasks done, commit."

ITERATION=0
PREV_UNCHECKED=-1
STALLED=0

echo "[apply] $(date +%H:%M:%S) Starting apply loop for change '${CHANGE}' with ${TOOL} (${MODEL})"

while [[ $ITERATION -lt $MAX_ITERATIONS ]]; do
    UNCHECKED=$(count_unchecked "$TASKS_FILE")
    CHECKED=$(count_checked "$TASKS_FILE")

    if [[ "$UNCHECKED" -eq 0 && "$CHECKED" -gt 0 ]]; then
        echo "[apply] $(date +%H:%M:%S) All ${CHECKED} tasks complete. Done."
        exit 0
    fi

    if [[ "$UNCHECKED" -eq 0 && "$CHECKED" -eq 0 ]]; then
        echo "[apply] $(date +%H:%M:%S) No tasks found in tasks.md. Nothing to apply."
        exit 0
    fi

    ITERATION=$((ITERATION + 1))
    OUTPUT_FILE="${OUTPUT_DIR}/phase-${ITERATION}.md"
    LOG_FILE="${OUTPUT_DIR}/phase-${ITERATION}.log"

    echo "[apply] $(date +%H:%M:%S) Iteration ${ITERATION}/${MAX_ITERATIONS}: ${UNCHECKED} tasks remaining"

    case "$TOOL" in
        pi)
            timeout "$TIMEOUT" pi -p --model "$MODEL" --no-session "$PROMPT" \
                > "$OUTPUT_FILE" 2>"$LOG_FILE" ;;
        devin)
            timeout "$TIMEOUT" devin -p --model "$MODEL" "$PROMPT" \
                > "$OUTPUT_FILE" 2>"$LOG_FILE" ;;
        agent)
            timeout "$TIMEOUT" agent -p --model "$MODEL" --trust "$PROMPT" \
                > "$OUTPUT_FILE" 2>"$LOG_FILE" ;;
        *)
            echo "Error: Unknown tool '${TOOL}' (supported: pi, devin, agent)" >&2
            exit 1 ;;
    esac

    EXIT_CODE=$?

    if [[ $EXIT_CODE -ne 0 ]]; then
        echo "[apply] $(date +%H:%M:%S) ✗ Agent exited with code ${EXIT_CODE}" >&2
        if [[ -f "$LOG_FILE" ]]; then
            echo "[apply]   Last 10 lines of log:" >&2
            tail -10 "$LOG_FILE" >&2
        fi
        echo "[apply] Stopping due to agent failure." >&2
        exit 1
    fi

    SIZE=$(wc -c < "$OUTPUT_FILE" 2>/dev/null || echo 0)
    echo "[apply] $(date +%H:%M:%S) ✓ Phase ${ITERATION} output: ${SIZE} bytes"

    # Check for stall: if unchecked count didn't decrease, the agent hit a pause condition
    NEW_UNCHECKED=$(count_unchecked "$TASKS_FILE")
    if [[ "$NEW_UNCHECKED" -ge "$UNCHECKED" ]]; then
        STALLED=$((STALLED + 1))
        echo "[apply] $(date +%H:%M:%S) ⚠ No progress (${UNCHECKED} → ${NEW_UNCHECKED} unchecked). Stall ${STALLED}/3."
        if [[ $STALLED -ge 3 ]]; then
            echo "[apply] $(date +%H:%M:%S) Stalled 3 times. Agent likely hit a pause condition." >&2
            echo "[apply] Read ${OUTPUT_FILE} for details." >&2
            exit 2
        fi
    else
        STALLED=0
    fi
done

echo "[apply] $(date +%H:%M:%S) Reached max iterations (${MAX_ITERATIONS}). Stopping." >&2
echo "[apply] Remaining unchecked tasks: $(count_unchecked "$TASKS_FILE")" >&2
exit 2
