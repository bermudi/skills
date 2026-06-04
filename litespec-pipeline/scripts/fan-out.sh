#!/usr/bin/env bash
# Fan out litespec change reviews to multiple AI coding agents in parallel.
#
# Usage:
#   fan-out.sh --change <name> --output <dir> --reviewer <spec> [--reviewer ...]
#
#   <spec> format: tool:model or tool:model:provider
#   Examples: pi:glm-5.1:opencode-go  devin:kimi-k2.6  agent:auto
#
# Tools: pi, devin, agent
# Each reviewer runs in the CWD (must be a litespec project root for skill discovery).
# Outputs: one .md file per reviewer in the output directory.
set -euo pipefail

CHANGE=""
OUTPUT_DIR=""
REVIEWERS=()
TIMEOUT="${REVIEW_PANEL_TIMEOUT:-1200}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --change)   CHANGE="$2"; shift 2 ;;
        --output)   OUTPUT_DIR="$2"; shift 2 ;;
        --reviewer) REVIEWERS+=("$2"); shift 2 ;;
        --timeout)  TIMEOUT="$2"; shift 2 ;;
        -h|--help)
            cat <<'EOF'
Usage: fan-out.sh --change <name> --output <dir> --reviewer <spec> [--reviewer ...]

Options:
  --change <name>      Litespec change name to review
  --output <dir>       Directory for review output files
  --reviewer <spec>    Reviewer spec: tool:model[:provider]. Repeat for multiple.
                       Tools: pi, devin, agent
                       :provider is optional, used by pi for disambiguation
  --timeout <seconds>  Per-reviewer timeout (default: 600, env: REVIEW_PANEL_TIMEOUT)
  -h, --help           Show this help

Example:
  fan-out.sh --change my-feature --output /tmp/reviews \
    --reviewer pi:glm-5.1:zai \
    --reviewer pi:deepseek-v4-pro:deepseek \
    --reviewer devin:kimi-k2.6
EOF
            exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$CHANGE" || -z "$OUTPUT_DIR" || ${#REVIEWERS[@]} -eq 0 ]]; then
    echo "Error: --change, --output, and at least one --reviewer are required" >&2
    echo "Run with --help for usage" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

PROMPT="Use your litespec-review skill to review litespec change '${CHANGE}'. Read all change artifacts (proposal, specs, design, tasks) and the implementation code. Produce a full review report."

PIDS=()
NAMES=()

# Pre-flight: verify each tool exists
for reviewer in "${REVIEWERS[@]}"; do
    TOOL="${reviewer%%:*}"
    if ! command -v "$TOOL" &>/dev/null; then
        echo "Error: '${TOOL}' not found in PATH" >&2
        exit 1
    fi
done

echo "[fan-out] $(date +%H:%M:%S) Starting ${#REVIEWERS[@]} reviewers for change '${CHANGE}'"

for reviewer in "${REVIEWERS[@]}"; do
    # Parse tool:model[:provider]
    TOOL="${reviewer%%:*}"
    REST="${reviewer#*:}"
    if [[ "$TOOL" == "$REST" ]]; then
        echo "Error: --reviewer requires <tool:model> format (e.g., pi:sonnet-4)" >&2
        exit 1
    fi
    # Check for optional :provider suffix
    if [[ "$REST" == *:* ]]; then
        MODEL="${REST%%:*}"
        PROVIDER="${REST#*:}"
    else
        MODEL="$REST"
        PROVIDER=""
    fi
    SAFE_NAME="${TOOL}-${MODEL//\//--}"
    OUTPUT_FILE="${OUTPUT_DIR}/${SAFE_NAME}.md"
    LOG_FILE="${OUTPUT_DIR}/${SAFE_NAME}.log"

    case "$TOOL" in
        pi)
            PROVIDER_FLAG=""
            if [[ -n "$PROVIDER" ]]; then
                PROVIDER_FLAG="--provider $PROVIDER"
            fi
            timeout "$TIMEOUT" pi -p $PROVIDER_FLAG --model "$MODEL" --no-session "$PROMPT" \
                > "$OUTPUT_FILE" 2>"$LOG_FILE" &
            ;;
        devin)
            timeout "$TIMEOUT" devin -p --model "$MODEL" -- "$PROMPT" \
                > "$OUTPUT_FILE" 2>"$LOG_FILE" &
            ;;
        agent)
            timeout "$TIMEOUT" agent -p --model "$MODEL" --trust "$PROMPT" \
                > "$OUTPUT_FILE" 2>"$LOG_FILE" &
            ;;
        *)
            echo "Error: Unknown tool '${TOOL}' (supported: pi, devin, agent)" >&2
            exit 1
            ;;
    esac

    PIDS+=($!)
    NAMES+=("$SAFE_NAME")
    echo "[fan-out] $(date +%H:%M:%S)   → ${TOOL} with ${MODEL} (pid $!)"
done

echo "[fan-out] $(date +%H:%M:%S) Waiting for all reviewers..."

FAILED=0
COMPLETED=0
for i in "${!PIDS[@]}"; do
    if wait "${PIDS[$i]}"; then
        SIZE=$(wc -c < "${OUTPUT_DIR}/${NAMES[$i]}.md" 2>/dev/null || echo 0)
        if [[ "$SIZE" -lt 100 ]]; then
            echo "[fan-out] $(date +%H:%M:%S) ⚠ ${NAMES[$i]} — suspiciously short (${SIZE} bytes)"
            FAILED=1
        else
            echo "[fan-out] $(date +%H:%M:%S) ✓ ${NAMES[$i]} (${SIZE} bytes)"
            COMPLETED=$((COMPLETED + 1))
        fi
    else
        EXIT_CODE=$?
        echo "[fan-out] $(date +%H:%M:%S) ✗ ${NAMES[$i]} — exited with code ${EXIT_CODE}" >&2
        if [[ -f "${OUTPUT_DIR}/${NAMES[$i]}.log" ]]; then
            echo "[fan-out]   Last 5 lines of log:" >&2
            tail -5 "${OUTPUT_DIR}/${NAMES[$i]}.log" >&2
        fi
        FAILED=1
    fi
done

echo ""
echo "[fan-out] $(date +%H:%M:%S) Done: ${COMPLETED} completed, $((${#PIDS[@]} - COMPLETED)) failed"
echo "[fan-out] Output directory: ${OUTPUT_DIR}"
ls -1 "${OUTPUT_DIR}"/*.md 2>/dev/null | while read -r f; do
    echo "  $(basename "$f")"
done

exit $FAILED
