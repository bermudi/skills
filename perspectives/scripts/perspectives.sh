#!/usr/bin/env bash
# perspectives.sh — run the same prompt across 3 different model families in
# parallel, capture each session's output to its own file, and print the
# output directory so the caller can read and synthesize.
set -uo pipefail

DEFAULT_MODELS=(
    "opencode-go/kimi-k2.6"
    "deepseek/deepseek-v4-pro"
    "zai/glm-5.1"
)

usage() {
    cat <<'EOF'
Usage:
  perspectives.sh [-m m1,m2,m3] [-o outdir] [-t thinking] [-f promptfile] [PROMPT...]

Runs the same prompt against 3 different model families in parallel using
`pi --print`. Each model's stdout, stderr, and session directory are saved
in a per-run output directory.

Options:
  -m  comma-separated list of EXACTLY 3 model patterns (provider/model[:thinking])
      Default: opencode-go/kimi-k2.6, deepseek/deepseek-v4-pro, zai/glm-5.1
  -o  output directory (default: /tmp/perspectives-<unix-timestamp>)
  -t  thinking level applied to all 3 (off|minimal|low|medium|high|xhigh)
  -f  read prompt from a file (passed to pi as @file so its contents inline)
  -h  show this help

Positional args after options are appended to the prompt verbatim. Combine
with -f to add extra instructions on top of the file's contents.

Examples:
  perspectives.sh -f /tmp/prompt.md
  perspectives.sh -t high -f /tmp/prompt.md "Be brutally honest."
  perspectives.sh -m anthropic/sonnet,openai/gpt-5,zai/glm-5-turbo "Rethink X"

Exit codes:
  0  all 3 perspectives produced output
  N  N of the runs failed (see *.err files in the output dir)
EOF
}

models_csv=""
outdir=""
thinking=""
prompt_file=""

while getopts "m:o:t:f:h" opt; do
    case $opt in
        m) models_csv=$OPTARG ;;
        o) outdir=$OPTARG ;;
        t) thinking=$OPTARG ;;
        f) prompt_file=$OPTARG ;;
        h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done
shift $((OPTIND - 1))

if [[ -n "$models_csv" ]]; then
    IFS=',' read -ra MODELS <<<"$models_csv"
else
    MODELS=("${DEFAULT_MODELS[@]}")
fi

if [[ "${#MODELS[@]}" -ne 3 ]]; then
    echo "error: expected exactly 3 models, got ${#MODELS[@]} (${MODELS[*]:-})" >&2
    exit 2
fi

if [[ -n "$prompt_file" && ! -r "$prompt_file" ]]; then
    echo "error: prompt file not readable: $prompt_file" >&2
    exit 2
fi

# Build prompt args for pi
declare -a PROMPT_ARGS=()
if [[ -n "$prompt_file" ]]; then
    PROMPT_ARGS+=("@$prompt_file")
fi
if (($# > 0)); then
    PROMPT_ARGS+=("$@")
fi
if [[ "${#PROMPT_ARGS[@]}" -eq 0 ]]; then
    echo "error: no prompt provided (use -f FILE or pass positional args)" >&2
    usage >&2
    exit 2
fi

if [[ -z "$outdir" ]]; then
    outdir="/tmp/perspectives-$(date +%s)"
fi
mkdir -p "$outdir"

# Record what we ran
{
    echo "# Perspectives run"
    echo ""
    echo "- timestamp: $(date -Is)"
    echo "- cwd: $PWD"
    [[ -n "$thinking" ]] && echo "- thinking: $thinking"
    echo ""
    echo "## Prompt"
    if [[ -n "$prompt_file" ]]; then
        echo ""
        echo "From file: \`$prompt_file\`"
        echo ""
        echo '```'
        cat "$prompt_file"
        echo '```'
    fi
    if (($# > 0)); then
        echo ""
        echo "Extra positional args:"
        for a in "$@"; do
            printf -- '- %q\n' "$a"
        done
    fi
    echo ""
    echo "## Models"
} >"$outdir/README.md"

declare -a PIDS=()
declare -a OUT_FILES=()
declare -a ERR_FILES=()

for i in 0 1 2; do
    model="${MODELS[$i]}"
    safe=$(printf '%s' "$model" | tr '/:' '__')
    out="$outdir/${i}_${safe}.txt"
    err="$outdir/${i}_${safe}.err"
    sess="$outdir/${i}_${safe}.session"
    mkdir -p "$sess"

    OUT_FILES+=("$out")
    ERR_FILES+=("$err")

    echo "- slot $i: \`$model\` -> \`$(basename "$out")\`" >>"$outdir/README.md"

    (
        echo "[perspectives] starting slot $i: $model" >&2
        args=(--print --model "$model" --session-dir "$sess")
        [[ -n "$thinking" ]] && args+=(--thinking "$thinking")
        if pi "${args[@]}" "${PROMPT_ARGS[@]}" >"$out" 2>"$err"; then
            echo "[perspectives] done slot $i: $model" >&2
        else
            rc=$?
            echo "[perspectives] FAILED slot $i: $model (rc=$rc, see $(basename "$err"))" >&2
            exit "$rc"
        fi
    ) &
    PIDS+=("$!")
done

fail=0
for pid in "${PIDS[@]}"; do
    if ! wait "$pid"; then
        fail=$((fail + 1))
    fi
done

echo
echo "Output directory: $outdir"
echo
ls -lh "$outdir"
echo
if ((fail > 0)); then
    echo "WARNING: $fail of 3 perspectives failed. Check the .err files." >&2
fi
exit "$fail"
