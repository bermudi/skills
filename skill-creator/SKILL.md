---
name: skill-creator
description: Create and iteratively improve Agent Skills. Use when users want to create a skill from scratch, edit or improve an existing skill, run evals or benchmarks, or optimize a skill's description for better triggering accuracy.
---

# Skill Creator

The creation process:

1. Decide what the skill should do
2. Write a draft
3. Create test prompts and run them
4. Evaluate results qualitatively and quantitatively
   - While runs execute in the background, draft quantitative evals
   - Use the eval viewer to present results
5. Rewrite based on feedback
6. Repeat until satisfied, then expand the test set

Meet the user where they are. If they say "I want to make a skill for X", work through the full process. If they already have a draft, jump to eval/iterate. If they say "I don't need evaluations, just vibe with me", do that instead.

After the skill is done, offer to run the description optimizer for better triggering accuracy.

## Communicating with the user

Most skill creators are experienced developers, but don't assume. Match terminology to the user's demonstrated familiarity — clarify jargon (e.g., "progressive disclosure") only when the user's phrasing suggests they need it. Show, don't tell: demonstrate concepts through examples rather than defining them.

---

## Best practices

**Read `references/best-practices.md` at the start of every skill creation session.** It covers expertise sourcing, context spending, calibrating prescriptiveness, and reusable instruction patterns. Don't summarize it here — the agent will read the full file.

---

## Creating a skill

### Capture Intent

Start by understanding the user's intent. Check the current conversation — it may already contain a workflow to capture. Extract the tools used, step sequences, corrections made, and I/O formats, then have the user fill gaps and confirm.

1. What should this skill enable the agent to do?
2. When should this skill trigger? (what user phrases/contexts)
3. What's the expected output format?
4. Should we set up test cases? Skills with verifiable outputs (file transforms, data extraction, code generation) benefit; subjective skills (writing style, art) often don't. Suggest the default, let the user decide.

### Interview and Research

Ask about edge cases, I/O formats, example files, success criteria, and dependencies. Don't write test prompts until these are clear.

For research (finding similar skills, looking up patterns), use available MCPs or spawn subagents in parallel. Bring findings back to reduce back-and-forth with the user.

### Write the SKILL.md

Based on the user interview, fill in these components:

- **name**: Skill identifier (kebab-case, max 64 chars, must match directory name)
- **description**: When to trigger and what the skill does. All "when to use" information goes here — this is the primary triggering mechanism. See [Description Optimization](#description-optimization) for writing effective descriptions.
- **compatibility**: Required tools, dependencies (optional, rarely needed)
- **the rest of the skill**

#### Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

#### Progressive Disclosure

Skills use a three-level loading system:
1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** - Loaded on demand

**Key patterns:**
- Keep SKILL.md under 500 lines; approaching this limit → add hierarchy with clear pointers
- Reference files **with trigger conditions**: tell the agent when to load them (e.g., "Read `references/aws.md` if deploying to AWS")
- For large reference files (>300 lines), include a table of contents

**Domain organization** (skills supporting multiple frameworks):
```
cloud-deploy/
├── SKILL.md (workflow + selection)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

Read `references/specification.md` for complete format details (all frontmatter fields, naming constraints, validation).

Read `references/quickstart.md` for a complete end-to-end example (especially useful on your first skill).

### Test Cases

After drafting the skill, run `skills-ref validate ./skill-name` to catch any frontmatter issues. Then create at least three realistic test prompts. Share them with the user for confirmation before running.

Read `references/evaluating-skills.md` when setting up evals (covers test case design, assertions, grading, and workspace structure).

Save test cases to `evals/evals.json`:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

See `references/schemas.md` for the full schema (including the `assertions` field, which you'll add later).

---

## Running and evaluating test cases

**Execute this section as a continuous sequence** — stopping mid-way leaves runs incomplete and feedback uncollected.

**Workspace structure**: Use `<skill-name>-workspace/` as a sibling to the skill directory. Within it, organize by iteration (`iteration-1/`, `iteration-2/`, etc.) and within each, by test case (`eval-0/`, `eval-1/`, etc.). Create directories as needed rather than upfront.

### Step 1: Spawn all runs (with-skill AND baseline) in the same turn

For each test case, spawn two runs in the same turn — one with the skill, one without. Launch everything at once so it all finishes around the same time.

**With-skill run:**

```
Execute this task:
- Skill path: <path-to-skill>
- Task: <eval prompt>
- Input files: <eval files if any, or "none">
- Save outputs to: <workspace>/iteration-<N>/eval-<ID>/with_skill/outputs/
- Outputs to save: <what the user cares about>
```

**Baseline run** (same prompt, no skill):
- **Creating a new skill**: no skill at all. Same prompt, no skill path, save to `without_skill/outputs/`.
- **Improving an existing skill**: the old version. Snapshot the skill before editing (`cp -r <skill-path> <workspace>/skill-snapshot/`), then point the baseline at the snapshot. Save to `old_skill/outputs/`.

Write an `eval_metadata.json` for each test case:

```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "The user's task prompt",
  "assertions": []
}
```

### Step 2: While runs are in progress, draft assertions

Don't wait for runs to finish — draft quantitative assertions for each test case now. Explain them to the user.

Good assertions are objectively verifiable and have descriptive names. Subjective skills (writing style, design quality) are better evaluated qualitatively.

Update `eval_metadata.json` and `evals/evals.json` with the assertions.

### Step 3: As runs complete, capture timing data

When each run completes, record token count and duration to `timing.json` in the run directory:

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

Process each notification as it arrives rather than batching.

### Step 4: Grade, aggregate, and launch the viewer

Once all runs are done:

1. **Grade each run** — evaluate each assertion against the outputs. Save results to `grading.json` in each run directory. The grading.json expectations array must use `text`, `passed`, and `evidence` fields. For assertions that can be checked programmatically, write and run a script rather than eyeballing it.

2. **Aggregate into benchmark** — run the aggregation script:
   ```bash
   python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
   ```
   This produces `benchmark.json` and `benchmark.md`. See `references/schemas.md` for the exact schema.

3. **Run an analyst pass** — read the benchmark data and surface patterns the aggregate stats might hide. See `references/analysis-subagent.md` for what to look for.

4. **Launch the viewer** with both qualitative outputs and quantitative data:
   ```bash
   nohup python <skill-creator-path>/eval-viewer/generate_review.py \
     <workspace>/iteration-N \
     --skill-name "my-skill" \
     --benchmark <workspace>/iteration-N/benchmark.json \
     > /dev/null 2>&1 &
   VIEWER_PID=$!
   ```
   For iteration 2+, also pass `--previous-workspace <workspace>/iteration-<N-1>`.
   For headless environments, use `--static <output_path>` to write a standalone HTML file.

5. **Tell the user**: "I've opened the results. 'Outputs' lets you click through test cases and leave feedback; 'Benchmark' shows the quantitative comparison. Let me know when you're done."

The viewer shows output files rendered inline, previous iteration's output (iteration 2+), formal grades, and a feedback textbox per test case. The Benchmark tab shows aggregate stats with per-eval breakdowns.

### Step 5: Read the feedback

When the user is done, read `feedback.json`. Empty feedback = fine. Focus on cases with specific complaints.

Kill the viewer when done: `kill $VIEWER_PID 2>/dev/null`

---

## Improving the skill

This is the heart of the loop. You've run the test cases, the user has reviewed the results, and now you need to make the skill better.

### How to think about improvements

1. **Generalize from feedback.** A skill runs against many prompts. Resist overfitting to a single test case — if a problem persists across cases, rewrite the underlying instruction rather than patching around it.

2. **Read transcripts, not just outputs.** If the agent wastes time on unproductive steps, trace which instruction triggered the detour and cut it.

3. **Explain why, don't just command.** Instructions that explain their purpose let the agent adapt to edge cases. Replace `MUST do X` with `Do X because Y` — the agent will make better judgment calls when it understands the reasoning.

4. **Bundle repeated work.** If the agent independently writes similar helper scripts across test cases, extract it into `scripts/`. Read `references/using-scripts.md` for making scripts self-contained with inline dependency declarations.

Write a draft revision, then re-read it as if you're encountering it for the first time. Cut anything that doesn't pull its weight.

### The iteration loop

After improving the skill:

1. Apply improvements to the skill
2. Rerun all test cases into a new `iteration-<N+1>/` directory, including baseline runs
3. Launch the reviewer with `--previous-workspace` pointing at the previous iteration
4. Wait for the user to review
5. Read the new feedback, improve again, repeat

Keep going until the user says they're happy, the feedback is all empty, or you're not making meaningful progress.

---

## Advanced: Blind comparison

For situations where you want a more rigorous comparison between two versions of a skill, there's a blind comparison system. Read `references/comparison-subagent.md` and `references/analysis-subagent.md` for details. The basic idea: give two outputs to an independent agent without telling it which is which, and let it judge quality.

This is optional and most users won't need it. The human review loop is usually sufficient.

---

## Description Optimization

The `description` field determines whether an agent invokes a skill. After creating or improving a skill, offer to optimize it for better triggering accuracy.

### How skill triggering works

Agents use progressive disclosure. At startup, only `name` and `description` load. When a task matches, the full SKILL.md loads. The description carries the entire triggering burden.

Important nuance: agents typically only consult skills for tasks that require knowledge beyond what they can handle alone. Simple, one-step queries may not trigger a skill even if the description matches. Specialized-knowledge tasks are where a well-written description makes the difference.

**Read `references/optimizing-descriptions.md`** for the full trigger optimization guide (eval query design, the optimization loop, train/validation splits).

### Writing effective descriptions

- **Use imperative phrasing.** "Use this skill when..." rather than "This skill does..."
- **Focus on user intent, not implementation.** Describe what the user is trying to achieve.
- **Err on the side of being pushy.** Explicitly list contexts where the skill applies, including cases where the user doesn't name the domain directly.
- **Keep it concise.** A few sentences to a short paragraph. Hard limit: 1024 characters.

### Step 1: Generate trigger eval queries

Create ~20 eval queries — 8-10 that should trigger and 8-10 that shouldn't:

```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]
```

Queries must be realistic — file paths, personal context, column names, company names, casual speech, typos. Not abstract requests.

**Should-trigger queries**: vary phrasing (formal/casual), explicitness (naming the domain vs. describing the need), detail level, and complexity. The most useful ones are where the skill would help but the connection isn't obvious.

**Should-not-trigger queries**: the most valuable ones are **near-misses** — queries that share keywords but actually need something different. Don't use obviously irrelevant queries; they don't test anything.

### Step 2: Review with user

Present the eval set to the user for review using the HTML template:

1. Read the template from `assets/eval_review.html`
2. Replace placeholders:
   - `__EVAL_DATA_PLACEHOLDER__` → the JSON array
   - `__SKILL_NAME_PLACEHOLDER__` → the skill's name
   - `__SKILL_DESCRIPTION_PLACEHOLDER__` → the skill's current description
3. Write to a temp file and open it
4. The user edits queries, toggles should-trigger, adds/removes entries, then exports
5. The file downloads to `~/Downloads/eval_set.json`

This step matters — bad eval queries lead to bad descriptions.

### Step 3: Run the optimization loop

Tell the user: "This will take some time — I'll run the optimization loop in the background."

Save the eval set to the workspace, then run:

```bash
python -m scripts.run_loop \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id> \
  --max-iterations 5 \
  --verbose
```

Note: `run_loop.py` uses `pi -p` under the hood — this requires Pi installed and authenticated. Pass `--model provider/model` (e.g. `poe-responses/Claude-Sonnet-4.6`) since short names may not resolve in one-shot mode.

While it runs, periodically tail the output for updates.

The script splits into 60% train / 40% test, evaluates (3 runs per query), proposes improvements, re-evaluates, and iterates up to 5 times. It selects the best description by test score to avoid overfitting.

### Avoiding overfitting

If you optimize against all queries, you risk overfitting — crafting a description that works for specific phrasings but fails on new ones. Split queries:
- **Train set (~60%)**: use these to identify failures and guide improvements
- **Validation set (~40%)**: set aside, only use to check whether improvements generalize

Never let the optimization process see validation results — they're a held-out check on generalization.

### Step 4: Apply the result

Take the best description and update the skill's SKILL.md frontmatter. Show the user before/after and report the scores. Verify the description is under the 1024-character limit.

---

## Checklist: Before sharing a skill

Run through this before declaring a skill complete:

### Validation

- [ ] `skills-ref validate ./skill-name` passes

Install: `uv tool install git+https://github.com/agentskills/agentskills.git#subdirectory=skills-ref`

This catches broken YAML frontmatter (unquoted colons, invalid types, missing fields, name mismatches). Run it after any frontmatter edit — the `skills` CLI silently skips skills with invalid YAML.

### Core quality

- [ ] Description includes both what the skill does and when to use it
- [ ] SKILL.md body is under 500 lines
- [ ] Reference files have clear "when to read" triggers
- [ ] Examples are concrete (real file paths, real commands)
- [ ] Progressive disclosure used appropriately
- [ ] Skill contents are transparent — nothing that would surprise the user if they read the raw files

### Code and scripts

- [ ] Scripts solve problems rather than punt to the agent
- [ ] Error handling is explicit
- [ ] Required packages listed and verified available
- [ ] Validation steps included for critical operations

### Testing

- [ ] At least three test cases created
- [ ] Evaluated against real usage scenarios

---

## Packaging

Package the skill for distribution:

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

This creates a `.skill` file (zip format) that can be installed by any agent client supporting the Agent Skills format.

---

## Reference files

**When to read each reference:**

| Read when you need... | File |
|-----------------------|------|
| Complete SKILL.md format (all frontmatter fields, naming rules, validation) | `references/specification.md` |
| Your first end-to-end walkthrough | `references/quickstart.md` |
| Test case design, assertions, grading, workspace structure | `references/evaluating-skills.md` |
| Trigger optimization, train/validation splits | `references/optimizing-descriptions.md` |
| Making bundled scripts with inline dependencies | `references/using-scripts.md` |
| JSON schemas (evals.json, grading.json, benchmark.json) | `references/schemas.md` |
| Grading via subagent | `references/grading-subagent.md` |
| Blind A/B comparison between outputs | `references/comparison-subagent.md` |
| Analyzing why one version beat another | `references/analysis-subagent.md` |


