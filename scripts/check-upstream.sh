#!/usr/bin/env bash
#
# check-upstream.sh
# Compare locally-derived skills against their upstream sources.
#
# Body-only diff (YAML frontmatter stripped) so intentional local description
# rewrites don't create noise. Reports OK / DIFF per file, then prints the
# actual diffs for anything that diverged.
#
# Usage:
#   SKILLS_DIR=/path/to/skills ./check-upstream.sh          # all tracked skills
#   ./check-upstream.sh domain-modeling                     # substring filter
#
# Env:
#   BRANCH       upstream branch to compare against (default: main)
#   SKILLS_DIR   path to the local skills repo (default: /home/daniel/build/skills)

set -uo pipefail

BRANCH="${BRANCH:-main}"
SKILLS_DIR="${SKILLS_DIR:-/home/daniel/build/skills}"

# local_rel_path | upstream_repo | upstream_path
CHECKS=(
  "codebase-design/SKILL.md|mattpocock/skills|skills/engineering/codebase-design/SKILL.md"
  "domain-modeling/SKILL.md|mattpocock/skills|skills/engineering/domain-modeling/SKILL.md"
  "agent-browser/SKILL.md|vercel-labs/agent-browser|skills/agent-browser/SKILL.md"
  "mcporter/SKILL.md|steipete/clawdis|skills/mcporter/SKILL.md"
  "content-retrieval/references/documents/liteparse.md|run-llama/llamaparse-agent-skills|skills/liteparse/SKILL.md"
  "html-communication/SKILL.md|plannotator/effective-html|skills/html/SKILL.md"
  "html-communication/references/charts-and-data.md|plannotator/effective-html|skills/html/references/charts-and-data.md"
  "html-communication/references/creative-direction.md|plannotator/effective-html|skills/html/references/creative-direction.md"
  "html-communication/references/diagrams.md|plannotator/effective-html|skills/html/references/diagrams.md"
  "html-communication/references/documents-and-presentations.md|plannotator/effective-html|skills/html/references/documents-and-presentations.md"
  "html-communication/references/interfaces.md|plannotator/effective-html|skills/html/references/interfaces.md"
  "html-communication/references/wireframes.md|plannotator/effective-html|skills/html-wireframe/SKILL.md"
  "html-communication/references/prototypes.md|plannotator/effective-html|skills/html-prototype/SKILL.md"
  "html-communication/references/plans.md|plannotator/effective-html|skills/html-plan/SKILL.md"
)

# Drop YAML frontmatter (from first `---` through the next `---`).
strip_fm() {
  awk 'NR==1 && $0=="---"{s=1; next} s && $0=="---"{s=0; next} !s{print}' "$1"
}

# Fetch upstream file into $3. Tries gh (authenticated) then raw curl.
fetch_upstream() {
  local repo="$1" path="$2" out="$3"
  if command -v gh >/dev/null 2>&1 && \
     gh api -H "Accept: application/vnd.github.raw" \
       "repos/$repo/contents/$path?ref=$BRANCH" >"$out" 2>/dev/null; then
    return 0
  fi
  curl -fsSL "https://raw.githubusercontent.com/$repo/$BRANCH/$path" -o "$out" 2>/dev/null
}

FILTER="${1:-}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

declare -a DIFFS=()
printf "%-56s %s\n" "LOCAL FILE" "STATUS"
printf "%-56s %s\n" "----------------------------------------" "------"

for entry in "${CHECKS[@]}"; do
  IFS='|' read -r local_rel repo up_path <<< "$entry"
  [[ -n "$FILTER" && "$local_rel" != *"$FILTER"* ]] && continue

  local_file="$SKILLS_DIR/$local_rel"
  base="$(echo "$local_rel" | tr '/' '_')"
  up_file="$TMP/up_$base"; lb="$TMP/lb_$base"; ub="$TMP/ub_$base"

  if [[ ! -f "$local_file" ]]; then
    printf "%-56s %s\n" "$local_rel" "MISSING LOCAL"
    continue
  fi
  fetch_upstream "$repo" "$up_path" "$up_file" || true
  if [[ ! -s "$up_file" ]]; then
    printf "%-56s %s\n" "$local_rel" "FETCH FAILED"
    continue
  fi

  strip_fm "$local_file" > "$lb"
  strip_fm "$up_file"   > "$ub"
  if diff -q "$lb" "$ub" >/dev/null 2>&1; then
    printf "%-56s %s\n" "$local_rel" "OK   in sync"
  else
    printf "%-56s %s\n" "$local_rel" "DIFF"
    DIFFS+=("$local_rel")
  fi
done

if ((${#DIFFS[@]})); then
  echo
  echo "===== DIFFS (body only, frontmatter stripped) ====="
  for d in "${DIFFS[@]}"; do
    base="$(echo "$d" | tr '/' '_')"
    echo
    echo "----- $d -----"
    diff -u "$TMP/lb_$base" "$TMP/ub_$base" || true
  done
fi
