---
name: skill-creator
description: Create new Agent Skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.
---

# Skill Creator

A skill for creating new Agent Skills and iteratively improving them.

At a high level, the process of creating a skill goes like this:

- Decide what you want the skill to do and roughly how it should do it
- Write a draft of the skill
- Create a few test prompts and run the skill on them
- Help the user evaluate the results both qualitatively and quantitatively
  - While the runs happen in the background, draft quantitative evals if there aren't any
  - Use the eval viewer to show the user the results and quantitative metrics
- Rewrite the skill based on feedback from the user's evaluation
- Repeat until satisfied
- Expand the test set and try again at larger scale

Your job is to figure out where the user is in this process and help them progress. If they say "I want to make a skill for X", you can help narrow down what they mean, write a draft, write test cases, figure out how they want to evaluate, run all the prompts, and repeat. If they already have a draft, go straight to the eval/iterate loop. And if they say "I don't need evaluations, just vibe with me", do that instead.

After the skill is done, you can also run the description optimizer to improve triggering accuracy.

## Communicating with the user

The skill creator may be used by people across a wide range of coding familiarity. Pay attention to context cues to understand how to phrase your communication. In the default case:

- "evaluation" and "benchmark" are borderline but OK
- for "JSON" and "assertion", check if the user knows these terms before using them without explanation

It's fine to briefly explain terms if you're in doubt.

---

## Best practices

Effective skills are grounded in real expertise. Extract from hands-on tasks (what worked, what you corrected, what context you had to provide) or synthesize from existing artifacts (runbooks, API specs, code review history, failure cases). The first draft usually needs refinement — run it, read the execution traces (not just outputs), and iterate.

Read `references/best-practices.md` for detailed guidance on starting from real expertise, spending context wisely, calibrating control, and effective instruction patterns (gotchas, templates, checklists, validation loops, plan-validate-execute).

---

## Creating a skill

### Capture Intent

Start by understanding the user's intent. The current conversation might already contain a workflow the user wants to capture. If so, extract answers from the conversation history first — the tools used, the sequence of steps, corrections the user made, input/output formats observed. The user may need to fill gaps, and should confirm before proceeding.

1. What should this skill enable the agent to do?
2. When should this skill trigger? (what user phrases/contexts)
3. What's the expected output format?
4. Should we set up test cases to verify the skill works? Skills with objectively verifiable outputs (file transforms, data extraction, code generation, fixed workflow steps) benefit from test cases. Skills with subjective outputs (writing style, art) often don't need them. Suggest the appropriate default based on the skill type, but let the user decide.

### Interview and Research

Proactively ask questions about edge cases, input/output formats, example files, success criteria, and dependencies. Wait to write test prompts until you've got this part ironed out.

Check available MCPs and tools — if useful for research (searching docs, finding similar skills, looking up best practices), research in parallel via subagents if available, otherwise inline. Come prepared with context to reduce burden on the user.

### Write the SKILL.md

Based on the user interview, fill in these components:

- **name**: Skill identifier (kebab-case, max 64 chars, must match directory name)
- **description**: When to trigger, what it does. This is the primary triggering mechanism — include both what the skill does AND specific contexts for when to use it. All "when to use" info goes here. Make descriptions a little "pushy" — e.g., "Use this skill whenever the user mentions dashboards, data visualization, or internal metrics, even if they don't explicitly ask for a 'dashboard.'"
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

Read `references/specification.md` for the complete format reference including all frontmatter fields, naming constraints, and validation tooling.

#### Progressive Disclosure

Skills use a three-level loading system:
1. **Metadata** (name + description) - Always in context (~100 words)
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** - As needed (unlimited, scripts can execute without loading)

**Key patterns:**
- Keep SKILL.md under 500 lines; if approaching this limit, add hierarchy with clear pointers to follow-up resources
- Reference files clearly from SKILL.md with guidance on when to read them
- For large reference files (>300 lines), include a table of contents

**Domain organization**: When a skill supports multiple domains/frameworks, organize by variant:
```
cloud-deploy/
├── SKILL.md (workflow + selection)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

#### Writing Style

Explain *why* things are important rather than heavy-handed MUSTs. Use theory of mind and make the skill general. If you find yourself writing ALWAYS or NEVER in all caps, that's a yellow flag — try to reframe and explain the reasoning so the model understands *why* something matters.

For a complete end-to-end example of creating a skill from scratch, read `references/quickstart.md`.

#### Principle of Lack of Surprise

Skills must not contain malware, exploit code, or any content that could compromise system security. A skill's contents should not surprise the user in their intent if described.

#### Writing Patterns

**Defining output formats:**
```markdown
## Report structure
ALWAYS use this exact template:
# [Title]
## Executive summary
## Key findings
## Recommendations
```

**Examples pattern:**
```markdown
## Commit message format
**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

### Test Cases

After writing the skill draft, come up with 2-3 realistic test prompts — the kind of thing a real user would actually say. Share them with the user: "Here are a few test cases I'd like to try. Do these look right, or do you want to add more?" Then run them.

Read `references/evaluating-skills.md` for detailed guidance on designing test cases, writing assertions, grading outputs, and structuring eval workspaces.

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

This section is one continuous sequence — don't stop partway through.

Put results in `<skill-name>-workspace/` as a sibling to the skill directory. Within the workspace, organize results by iteration (`iteration-1/`, `iteration-2/`, etc.) and within that, each test case gets a directory (`eval-0/`, `eval-1/`, etc.). Don't create all of this upfront — just create directories as you go.

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

3. **Do an analyst pass** — read the benchmark data and surface patterns the aggregate stats might hide. See `references/analysis-subagent.md` for what to look for.

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

1. **Generalize from the feedback.** The skill will be used many times across many different prompts. Rather than put in fiddly overfitty changes, if there's some stubborn issue, try branching out and using different metaphors or recommending different patterns.

2. **Keep the prompt lean.** Remove things that aren't pulling their weight. Read the transcripts, not just the final outputs — if the skill makes the model waste time on unproductive steps, cut the parts causing that.

3. **Explain the why.** Explain the **why** behind everything you're asking the model to do. Even if the feedback is terse, understand the task and transmit this understanding into the instructions. If you find yourself writing ALWAYS or NEVER in all caps, reframe and explain the reasoning.

4. **Look for repeated work across test cases.** If all test cases resulted in the agent writing similar helper scripts, that's a signal the skill should bundle that script. Write it once, put it in `scripts/`, and tell the skill to use it. Read `references/using-scripts.md` for details on making scripts self-contained with inline dependency declarations.

Take your time and really mull things over. Write a draft revision and then look at it anew and make improvements.

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

The description field in SKILL.md frontmatter is the primary mechanism that determines whether an agent invokes a skill. After creating or improving a skill, offer to optimize the description for better triggering accuracy.

### How skill triggering works

Agents use progressive disclosure to manage context. At startup, they load only the `name` and `description` of each available skill. When a user's task matches a description, the agent reads the full `SKILL.md` into context. The description carries the entire burden of triggering.

Important nuance: agents typically only consult skills for tasks that require knowledge beyond what they can handle alone. Simple, one-step queries may not trigger a skill even if the description matches. Tasks that involve specialized knowledge are where a well-written description makes the difference.

Read `references/optimizing-descriptions.md` for the full guide on designing trigger eval queries, running the optimization loop, and avoiding overfitting.

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

## Checklist for effective Skills

Before sharing a Skill, verify:

### Core quality

- [ ] Description is specific and includes key terms
- [ ] Description includes both what the Skill does and when to use it
- [ ] SKILL.md body is under 500 lines
- [ ] Additional details are in separate files (if needed)
- [ ] No time-sensitive information (or in "old patterns" section)
- [ ] Consistent terminology throughout
- [ ] Examples are concrete, not abstract
- [ ] File references are one level deep
- [ ] Progressive disclosure used appropriately
- [ ] Workflows have clear steps

### Code and scripts

- [ ] Scripts solve problems rather than punt to the agent
- [ ] Error handling is explicit and helpful
- [ ] No "voodoo constants" (all values justified)
- [ ] Required packages listed in instructions and verified as available
- [ ] Scripts have clear documentation
- [ ] No Windows-style paths (all forward slashes)
- [ ] Validation/verification steps for critical operations
- [ ] Feedback loops included for quality-critical tasks

### Testing

- [ ] At least three evaluations created
- [ ] Tested across multiple models
- [ ] Tested with real usage scenarios
- [ ] Team feedback incorporated (if applicable)

---

## Packaging

Package the skill for distribution:

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

This creates a `.skill` file (zip format) that can be installed by any agent client supporting the Agent Skills format.

---

## Reference files

### Skill reference docs (`references/`)

- `references/best-practices.md` — Writing well-scoped, calibrated skills (expertise sourcing, context management, instruction patterns)
- `references/specification.md` — Complete format reference for SKILL.md (frontmatter fields, naming rules, validation)
- `references/evaluating-skills.md` — Test case design, assertions, grading, workspace structure, iteration
- `references/optimizing-descriptions.md` — Trigger eval queries, optimization loop, train/validation splits
- `references/using-scripts.md` — Bundling self-contained scripts with inline dependency declarations
- `references/quickstart.md` — End-to-end example of creating a skill from scratch
- `references/schemas.md` — JSON structures for evals.json, grading.json, benchmark.json, etc.
- `references/grading-subagent.md` — How to evaluate assertions against outputs (for subagent spawning)
- `references/comparison-subagent.md` — How to do blind A/B comparison between two outputs
- `references/analysis-subagent.md` — How to analyze why one version beat another

---

The core loop, stated once more for emphasis:

- Figure out what the skill is about
- Draft or edit the skill
- Run the skill on test prompts
- With the user, evaluate the outputs:
  - Create benchmark.json and run `eval-viewer/generate_review.py` to help the user review them
  - Run quantitative evals
- Repeat until you and the user are satisfied
- Optimize the description for triggering accuracy
- Package the final skill and return it to the user
