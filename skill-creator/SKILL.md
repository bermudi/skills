---
name: skill-creator
description: Create and iteratively improve Agent Skills. Use when users want to create a skill from scratch, edit or improve an existing skill, run evals or benchmarks, or optimize a skill's description for better triggering accuracy.
disable-model-invocation: true
---

# Skill Creator

Loop: decide what the skill does → draft → write test prompts and run them → evaluate (qualitative and quantitative; draft assertions while runs execute; present with the eval viewer) → rewrite on feedback → repeat, then widen the test set. Offer the description optimizer at the end.

Meet the user where they are: "make a skill for X" → full process; existing draft → jump to eval/iterate; "no evals, just vibe with me" → do that.

**Read `references/best-practices.md` at the start of every session** (expertise sourcing, context spending, calibrating prescriptiveness, reusable instruction patterns).

Global skills live in `~/.agents/skills/<name>/`; project skills in `<project>/.agents/skills/<name>/` (tracked in `skills-lock.json`). `skills ls -g` / `skills ls` show what's installed where.

## Creating a skill

**Capture intent.** The conversation may already contain the workflow: extract tools used, step sequences, corrections and I/O formats, then have the user fill gaps. Settle: what it enables, what phrases/contexts trigger it, expected output format, and whether to set up test cases (verifiable outputs like transforms, extraction, codegen benefit; subjective ones like writing style usually don't; suggest a default, user decides). Ask about edge cases, example files, success criteria and dependencies before writing test prompts. For research, use MCPs or parallel subagents and bring the findings back.

**Write SKILL.md:** `name` (kebab-case, ≤64 chars, matches directory), `description` (all the "when to use" lives here; it is the only triggering mechanism), optional `compatibility`, then the body. Full format: `references/specification.md`; walkthrough: `references/quickstart.md`.

```
skill-name/
├── SKILL.md      (required: frontmatter + instructions)
├── scripts/      deterministic/repetitive code
├── references/   docs loaded on demand
└── assets/       templates, icons, fonts used in output
```

**Progressive disclosure:** metadata is always in context (~100 words); the body loads on trigger (<500 lines; near that, add hierarchy); resources load on demand. Reference files **with trigger conditions** ("Read `references/aws.md` if deploying to AWS"); give >300-line references a table of contents; split multi-framework skills into one reference per framework with selection logic in the body.

**Test cases:** run `skills-ref validate ./skill-name` (install: `uv tool install git+https://github.com/agentskills/agentskills.git#subdirectory=skills-ref`; it catches broken YAML, and the `skills` CLI silently skips skills with invalid YAML), then write ≥3 realistic prompts, confirm them with the user, and save to `evals/evals.json` (schema in `references/schemas.md`; design, assertions and grading in `references/evaluating-skills.md`):

```json
{"skill_name": "example-skill", "evals": [{"id": 1, "prompt": "User's task prompt", "expected_output": "Description of expected result", "files": []}]}
```

## Running and evaluating

Run this as one continuous sequence; each step has a completion criterion (e.g. "every run has a `timing.json`"): don't advance until it's met. Workspace: `<skill-name>-workspace/` beside the skill, `iteration-N/eval-ID/`, created as needed.

1. **Spawn all runs in the same turn**, with-skill and baseline, so they finish together. With-skill: skill path, task, input files, `…/iteration-N/eval-ID/with_skill/outputs/`, what to save. Baseline: same prompt with no skill (new skill, `without_skill/`) or against a pre-edit snapshot (`cp -r <skill-path> <workspace>/skill-snapshot/`, `old_skill/`). Write `eval_metadata.json` per case (`eval_id`, `eval_name`, `prompt`, `assertions`).
2. **While runs execute, draft assertions:** objectively verifiable, descriptively named (subjective skills: qualitative review instead). Explain them to the user; update `eval_metadata.json` and `evals/evals.json`.
3. **As each run completes, write `timing.json`** (`total_tokens`, `duration_ms`, `total_duration_seconds`); process notifications as they arrive.
4. **Grade, aggregate, view.** Grade each run into `grading.json` (`text`, `passed`, `evidence`): script what's checkable, give the rest to the grader subagent (`references/grading-subagent.md`). Aggregate: `uv run python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>` → `benchmark.json`/`.md`. Run an analyst pass for patterns the stats hide (`references/analysis-subagent.md`). Launch the viewer:
   ```bash
   nohup uv run python <skill-creator-path>/eval-viewer/generate_review.py <workspace>/iteration-N \
     --skill-name "my-skill" --benchmark <workspace>/iteration-N/benchmark.json >/dev/null 2>&1 &
   VIEWER_PID=$!
   ```
   Iteration 2+: add `--previous-workspace <workspace>/iteration-<N-1>`; headless: `--static <output_path>`. Tell the user the Outputs tab takes per-case feedback and Benchmark shows the comparison.
5. **Read `feedback.json`** when they're done (empty = fine; focus on specific complaints), then `kill $VIEWER_PID`.

## Improving

When feedback is vague ("feels weak"), read `references/writing-skills.md` (diagnostic rubric and symptom→fix table).

1. **Generalize.** A skill meets many prompts; if a problem recurs across cases, fix the underlying instruction, not the single case.
2. **Read transcripts, not just outputs:** find the instruction behind each wasted detour and cut it.
3. **Explain why.** `Do X because Y` beats `MUST do X`; the agent handles edge cases better when it knows the reason.
4. **Bundle repeated work:** helper scripts the agent keeps rewriting go into `scripts/` (`references/using-scripts.md`).

Re-read the draft as a first-time reader and cut what doesn't pull its weight. Then rerun everything (baselines too) into `iteration-N+1/`, view with `--previous-workspace`, collect feedback, repeat until the user is happy, feedback is empty, or progress stalls. Optional rigor: blind A/B comparison (`references/comparison-subagent.md`, `references/analysis-subagent.md`); the human review loop is usually enough.

## Description optimization

The description carries the whole triggering burden (only name and description load at startup). Agents consult skills mainly for tasks beyond their own ability, so one-step queries may not trigger even on a match. Full guide (query design, loop, splits): `references/optimizing-descriptions.md`.

Writing: imperative ("Use this skill when…"); user intent, not implementation; a bit pushy, listing contexts where the user doesn't name the domain; concise, **hard limit 1024 chars**. Reuse the body's *leading words* (compact pretraining-resident terms the agent echoes when the skill fires, e.g. "vertical slice" for TDD) so a prompt containing them links to the skill (`writing-skills.md`).

1. **~20 realistic trigger queries**, 8–10 should-trigger and 8–10 shouldn't, as `[{"query": …, "should_trigger": true}]`: file paths, personal context, column names, casual speech, typos. Should-trigger: vary phrasing, explicitness and complexity, favoring cases where the connection isn't obvious. Should-not: near-misses sharing keywords but needing something else; obviously irrelevant ones test nothing.
2. **Review with the user** via `assets/eval_review.html`: replace `__EVAL_DATA_PLACEHOLDER__`, `__SKILL_NAME_PLACEHOLDER__`, `__SKILL_DESCRIPTION_PLACEHOLDER__`, write to a temp file and open it; they edit and export to `~/Downloads/eval_set.json`. Bad queries make bad descriptions.
3. **Run the loop** in the background (it takes a while; tail it):
   ```bash
   uv run python -m scripts.run_loop --eval-set <trigger-eval.json> --skill-path <skill> --model <provider/model> --max-iterations 5 --verbose
   ```
   `run_loop.py` shells out to `pi -p`, so pi must be installed and authenticated, and the model needs the full `provider/model` form (e.g. `poe-responses/Claude-Sonnet-4.6`). It splits 60% train / 40% held-out test, runs each query 3×, proposes improvements, and picks the best description by test score. Never let the optimization see held-out results, or it overfits to phrasings.
4. **Apply:** put the best description in the frontmatter, show before/after with scores, confirm it's under 1024 chars.

## Before sharing

- `skills-ref validate ./skill-name` passes (rerun after any frontmatter edit).
- The description says what and when; body <500 lines; references have "when to read" triggers; examples are concrete (real paths, real commands); contents are transparent: nothing that would surprise a user reading the raw files.
- Scripts solve problems instead of punting to the agent, handle errors explicitly, list and verify required packages, and validate critical operations.
- ≥3 cases on real scenarios; ablation (with vs without the skill) confirms it adds value; 2–6 trials per case for non-determinism; assertions test outcomes (task achieved), not paths (skill invoked).

## References

| Need | File |
|---|---|
| Expertise sourcing, context spending, prescriptiveness, skill vs script, capability vs preference, retirement | `references/best-practices.md` |
| Full SKILL.md format | `references/specification.md` |
| End-to-end walkthrough | `references/quickstart.md` |
| Test design, assertions, grading, workspace, regression gate | `references/evaluating-skills.md` |
| Trigger optimization, splits | `references/optimizing-descriptions.md` |
| Scripts with inline dependencies | `references/using-scripts.md` |
| JSON schemas (evals, grading, benchmark) | `references/schemas.md` |
| Grading subagent | `references/grading-subagent.md` |
| Blind A/B comparison | `references/comparison-subagent.md` |
| Why one version beat another | `references/analysis-subagent.md` |
| Diagnostic rubric: invocation, hierarchy, leading words, completion criteria, pruning | `references/writing-skills.md` |
