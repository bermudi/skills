#!/usr/bin/env bash
# litespec-pipeline — automate the full change pipeline
#
# Usage: pipeline.sh <change> [options]
#
# Phases:
#   1. Apply: loop agent until all tasks checked (apply-phases.sh)
#   2. Review: fan out 3 reviewers in parallel (fan-out.sh)
#   3. Consolidate: merge reviews into actionable findings (pi --print)
#   4. Fix: feed consolidated findings to agent with litespec-build skill
#   5. Report: print summary, suggest archive
#
# Options:
#   --skip-apply         Skip the apply phase (reviews are already done)
#   --skip-review        Skip review+consolidate+fix (just apply)
#   --reviewers <file>   Custom reviewer config YAML
#   --apply-tool <spec>  Tool for apply (default: agent:auto)
#   --fix-tool <spec>    Tool for fix (default: agent:auto)
#   --consolidate-model <spec>  Model for consolidation (default: pi default)
#   --output <dir>       Working directory (default: /tmp/litespec-pipeline-<change>)
#   --max-apply <N>      Max apply iterations (default: 15)
#   --timeout <secs>     Per-step timeout (default: 600)
#   --verbose            Stream agent output to stdout
#   -h, --help           Show help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

CHANGE=""
SKIP_APPLY=0
SKIP_REVIEW=0
REVIEWER_CONFIG=""
APPLY_TOOL="agent:auto"
FIX_TOOL="agent:auto"
CONSOLIDATE_MODEL=""   # defaults to pi's default provider/model
OUTDIR=""
MAX_APPLY=15
TIMEOUT=600
VERBOSE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-apply)      SKIP_APPLY=1; shift ;;
        --skip-review)     SKIP_REVIEW=1; shift ;;
        --reviewers)       REVIEWER_CONFIG="$2"; shift 2 ;;
        --apply-tool)      APPLY_TOOL="$2"; shift 2 ;;
        --fix-tool)        FIX_TOOL="$2"; shift 2 ;;
        --consolidate-model) CONSOLIDATE_MODEL="$2"; shift 2 ;;
        --output)          OUTDIR="$2"; shift 2 ;;
        --max-apply)       MAX_APPLY="$2"; shift 2 ;;
        --timeout)         TIMEOUT="$2"; shift 2 ;;
        --verbose)         VERBOSE=1; shift ;;
        -h|--help)
            sed -n '2,/^$/p' "$0" | sed 's/^# //; s/^#//'
            exit 0 ;;
        -*)
            echo "Unknown option: $1" >&2; exit 1 ;;
        *)
            if [[ -z "$CHANGE" ]]; then
                CHANGE="$1"; shift
            else
                echo "Unexpected argument: $1" >&2; exit 1
            fi ;;
    esac
done

if [[ -z "$CHANGE" ]]; then
    echo "Usage: pipeline.sh <change> [options]" >&2
    echo "Run with --help for details" >&2
    exit 1
fi

# Validate change exists
TASKS_FILE="specs/changes/${CHANGE}/tasks.md"
if [[ ! -f "$TASKS_FILE" ]]; then
    echo "Error: no tasks.md at ${TASKS_FILE}" >&2
    exit 1
fi

OUTDIR="${OUTDIR:-/tmp/litespec-pipeline-${CHANGE}}"
mkdir -p "$OUTDIR"/{apply,reviews,consolidation}

# Resolve reviewer config
if [[ -z "$REVIEWER_CONFIG" ]]; then
    if [[ -f ".litespec-pipeline.yaml" ]]; then
        REVIEWER_CONFIG=".litespec-pipeline.yaml"
    else
        REVIEWER_CONFIG="$SCRIPT_DIR/../assets/default-panel.yaml"
    fi
fi

# Parse reviewers from config (same format as review-panel.sh)
parse_reviewers() {
    python3 -c '
import yaml, sys
data = yaml.safe_load(open(sys.argv[1]))
for r in data.get("reviewers", []):
    provider = r.get("provider", "")
    if provider:
        print(f"{r["tool"]}:{r["model"]}:{provider}")
    else:
        print(f"{r["tool"]}:{r["model"]}")
' "$1" 2>/dev/null
}

REVIEWER_SPECS=()
if [[ "$SKIP_REVIEW" -eq 0 ]]; then
    while IFS= read -r line; do
        [[ -n "$line" ]] && REVIEWER_SPECS+=("$line")
    done < <(parse_reviewers "$REVIEWER_CONFIG" 2>/dev/null || true)

    if [[ ${#REVIEWER_SPECS[@]} -eq 0 ]]; then
        echo "Warning: no reviewers in config, using defaults" >&2
        REVIEWER_SPECS=(
            "pi:glm-5.1:zai"
            "pi:deepseek-v4-pro:opencode-go"
            "devin:kimi-k2.6"
        )
    fi
fi

count_unchecked() {
    grep -cP '^\s*- \[ \]' "$1" 2>/dev/null || echo "0"
}

echo "═══════════════════════════════════════════════════════════"
echo "  litespec pipeline: ${CHANGE}"
echo "  apply: ${APPLY_TOOL}  |  reviewers: ${#REVIEWER_SPECS[@]}  |  fix: ${FIX_TOOL}"
echo "  consolidate: ${CONSOLIDATE_MODEL:-pi (default)}"
echo "  output: ${OUTDIR}"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ── Phase 1: Apply ──────────────────────────────────────────

if [[ "$SKIP_APPLY" -eq 0 ]]; then
    UNCHECKED=$(count_unchecked "$TASKS_FILE")
    if [[ "$UNCHECKED" -eq 0 ]]; then
        echo "[pipeline] ✓ All tasks already complete, skipping apply"
    else
        echo "[pipeline] ── Phase 1: Apply (${UNCHECKED} unchecked tasks) ──"
        echo ""

        bash "$SCRIPT_DIR/apply-phases.sh" \
            --change "$CHANGE" \
            --tool "$APPLY_TOOL" \
            --output "$OUTDIR/apply" \
            --max-iterations "$MAX_APPLY" \
            --timeout "$TIMEOUT"

        UNCHECKED_AFTER=$(count_unchecked "$TASKS_FILE")
        if [[ "$UNCHECKED_AFTER" -gt 0 ]]; then
            echo ""
            echo "[pipeline] ⚠ Apply finished with ${UNCHECKED_AFTER} tasks still unchecked"
            echo "[pipeline] Read the last apply output for details:"
            echo "[pipeline]   $OUTDIR/apply/"
            exit 2
        fi

        echo ""
        echo "[pipeline] ✓ Apply complete — all tasks checked"
    fi
else
    echo "[pipeline] Skipping apply (--skip-apply)"
fi

if [[ "$SKIP_REVIEW" -eq 1 ]]; then
    echo ""
    echo "[pipeline] Done (--skip-review). Ready to archive."
    exit 0
fi

# ── Phase 2: Review fan-out ─────────────────────────────────

echo ""
echo "[pipeline] ── Phase 2: Review (${#REVIEWER_SPECS[@]} reviewers) ──"
echo ""

REVIEWER_ARGS=()
for spec in "${REVIEWER_SPECS[@]}"; do
    REVIEWER_ARGS+=(--reviewer "$spec")
done

bash "$SCRIPT_DIR/fan-out.sh" \
    --change "$CHANGE" \
    --output "$OUTDIR/reviews" \
    --timeout "$TIMEOUT" \
    "${REVIEWER_ARGS[@]}"

echo ""

# Check we actually got reviews
REVIEW_COUNT=$(ls "$OUTDIR/reviews/"*.md 2>/dev/null | wc -l)
if [[ "$REVIEW_COUNT" -eq 0 ]]; then
    echo "[pipeline] ✗ No review outputs found. Stopping." >&2
    exit 1
fi

echo "[pipeline] ✓ ${REVIEW_COUNT} reviews collected"

# ── Phase 3: Consolidate ────────────────────────────────────

echo ""
echo "[pipeline] ── Phase 3: Consolidate ──"
echo ""

CONSOLIDATED="$OUTDIR/consolidation/consolidated.md"
CONSOLIDATION_GUIDE="$SCRIPT_DIR/../references/consolidation.md"

# Build the consolidation prompt — reference review files by path, don't inline them
# This keeps the prompt small and lets pi read them from disk
REVIEW_FILES=()
for review_file in "$OUTDIR/reviews/"*.md; do
    REVIEW_FILES+=("$review_file")
done

CONSOLIDATION_PROMPT="You are consolidating ${REVIEW_COUNT} independent reviews of litespec change '${CHANGE}'.

Read each of these review files, then produce a single consolidated report following the consolidation guide."
if [[ -f "$CONSOLIDATION_GUIDE" ]]; then
    CONSOLIDATION_PROMPT+="

Consolidation guide: ${CONSOLIDATION_GUIDE}"
fi

for review_file in "${REVIEW_FILES[@]}"; do
    CONSOLIDATION_PROMPT+="
Review file: ${review_file}"
done

# Write prompt to file so we can pass it cleanly
PROMPT_FILE="$OUTDIR/consolidation/prompt.txt"
echo "$CONSOLIDATION_PROMPT" > "$PROMPT_FILE"

# Run consolidation via pi
PI_FLAGS=(-p --no-session)
if [[ -n "$CONSOLIDATE_MODEL" ]]; then
    if [[ "$CONSOLIDATE_MODEL" == */* ]]; then
        PI_FLAGS+=(--provider "${CONSOLIDATE_MODEL%%/*}" --model "${CONSOLIDATE_MODEL#*/}")
    else
        PI_FLAGS+=(--model "$CONSOLIDATE_MODEL")
    fi
fi

echo "[pipeline] Running consolidation with pi ${CONSOLIDATE_MODEL:-default}..."
timeout "$TIMEOUT" pi "${PI_FLAGS[@]}" "$CONSOLIDATION_PROMPT" > "$CONSOLIDATED" 2>"$OUTDIR/consolidation/pi.log"
CONSOLIDATION_EXIT=$?

if [[ $CONSOLIDATION_EXIT -ne 0 ]]; then
    echo "[pipeline] ✗ Consolidation failed (exit $CONSOLIDATION_EXIT)" >&2
    echo "[pipeline]   Log: $OUTDIR/consolidation/pi.log" >&2
    exit 1
fi

CONSOLIDATED_SIZE=$(wc -c < "$CONSOLIDATED" 2>/dev/null || echo 0)
if [[ "$CONSOLIDATED_SIZE" -lt 200 ]]; then
    echo "[pipeline] ✗ Consolidation output suspiciously short (${CONSOLIDATED_SIZE} bytes)" >&2
    exit 1
fi

echo "[pipeline] ✓ Consolidated report: ${CONSOLIDATED_SIZE} bytes"
echo "[pipeline]   $CONSOLIDATED"

# ── Phase 4: Fix ─────────────────────────────────────────────

echo ""
echo "[pipeline] ── Phase 4: Fix ──"
echo ""

FIX_PROMPT="Use your litespec-build skill to fix the following consolidated review findings for litespec change '${CHANGE}'.

Read specs/changes/${CHANGE}/proposal.md, specs/changes/${CHANGE}/design.md, and specs/changes/${CHANGE}/tasks.md for full context.

Consolidated findings file: ${CONSOLIDATED}
Read that file, then fix every issue it describes."

FIX_OUTPUT="$OUTDIR/fix-output.md"
FIX_LOG="$OUTDIR/fix.log"

TOOL="${FIX_TOOL%%:*}"
MODEL="${FIX_TOOL#*:}"

echo "[pipeline] Running fix with ${TOOL} (${MODEL})..."

case "$TOOL" in
    pi)
        timeout "$TIMEOUT" pi -p --model "$MODEL" --no-session "$FIX_PROMPT" \
            > "$FIX_OUTPUT" 2>"$FIX_LOG" ;;
    devin)
        timeout "$TIMEOUT" devin -p --model "$MODEL" -- "$FIX_PROMPT" \
            > "$FIX_OUTPUT" 2>"$FIX_LOG" ;;
    agent)
        timeout "$TIMEOUT" agent -p --model "$MODEL" --trust "$FIX_PROMPT" \
            > "$FIX_OUTPUT" 2>"$FIX_LOG" ;;
    *)
        echo "Error: unknown tool '${TOOL}'" >&2; exit 1 ;;
esac

FIX_EXIT=$?
if [[ $FIX_EXIT -ne 0 ]]; then
    echo "[pipeline] ✗ Fix failed (exit $FIX_EXIT)" >&2
    echo "[pipeline]   Log: $FIX_LOG" >&2
    exit 1
fi

FIX_SIZE=$(wc -c < "$FIX_OUTPUT" 2>/dev/null || echo 0)
echo "[pipeline] ✓ Fix complete: ${FIX_SIZE} bytes"

# ── Summary ──────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Pipeline complete: ${CHANGE}"
echo ""
echo "  Apply:     $([ "$SKIP_APPLY" -eq 0 ] && echo "✓ done" || echo "— skipped")"
echo "  Reviews:   ✓ ${REVIEW_COUNT} collected"
echo "  Consolidated: ✓ $(wc -l < "$CONSOLIDATED") lines"
echo "  Fix:       ✓ done"
echo ""
echo "  Artifacts:"
echo "    Reviews:       $OUTDIR/reviews/"
echo "    Consolidated:  $CONSOLIDATED"
echo "    Fix output:    $FIX_OUTPUT"
echo ""
echo "  Next: review the diff, then archive if happy:"
echo "    git diff"
echo "    litespec archive ${CHANGE}"
echo "═══════════════════════════════════════════════════════════"
