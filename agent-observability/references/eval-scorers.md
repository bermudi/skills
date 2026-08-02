# Eval Scorers

> Implementing LLM-as-judge and code-based scoring for agent output quality.

## When to Use Each Scorer Type

| Scorer Type | Use When | Example |
|-------------|----------|---------|
| **Code-based** | Criteria is deterministic, verifiable by program | JSON validity, required fields present, row count matches |
| **LLM-as-Judge** | Criteria is subjective, requires semantic understanding | Helpfulness, groundedness, tone, completeness |
| **Heuristic** | Criteria is structural, pattern-matchable | Response length, step count, token usage |

## Code-Based Scorers

Implement as pure functions: input → 0..1 score. Deterministic every time.

### Pattern: Structural Validation

```typescript
function scoreJsonValidity(output: string): number {
  try {
    JSON.parse(output);
    return 1.0;
  } catch {
    return 0.0;
  }
}

function scoreRequiredFields(
  output: Record<string, unknown>,
  requiredFields: string[]
): number {
  const missing = requiredFields.filter(f => !(f in output));
  return missing.length === 0 ? 1.0 : 0.0;
}
```

### Pattern: Statistical Check

```typescript
function scoreStepEfficiency(
  trace: Span[],
  expectedMaxSteps: number
): number {
  const actualSteps = trace.filter(s => s.name.startsWith("tool.")).length;
  return Math.max(0, 1 - (actualSteps - expectedMaxSteps) / expectedMaxSteps);
}
```

### Pattern: Reference Comparison

```typescript
function scoreExactMatch(output: string, reference: string): number {
  return output.trim().toLowerCase() === reference.trim().toLowerCase()
    ? 1.0
    : 0.0;
}
```

## LLM-as-Judge Scorers

### The Reliability Problem

Before implementing LLM-as-Judge, understand the evidence against its
reliability. Four independent sources challenge the assumption that an LLM can
fairly judge another LLM's output:

| Source | Finding |
|--------|---------|
| **RUBRICEVAL** (Pan et al., 2026) | GPT-4o: 55.97% balanced accuracy on hard rubric judgments. Claude-Sonnet-4.5: 55.65%. Judge selection alone shifts scores by up to 25 points. |
| **DELEGATE-52** (Laban et al., 2026) | GPT 5.4 as judge captures at most 25% of the variance of domain-specific parsing metrics. Generic rubrics miss nuanced semantic corruption. |
| **Bias in the Loop** (Zhao et al., 2026) | 12 prompt-induced biases produce 40+ point swings from candidate ordering and prompt framing. Biases are directional, not random. |
| **Practitioner consensus** | Dex Horthy: "models are optimized to tell you what you want to hear." Samuel Colvin: "the lunatics running the asylum." Both prefer deterministic checks. |

**Implication for implementation:** LLM-as-Judge is a noisy signal generator,
not a reliable gate. Use it for exploration and surfacing candidates for
review, but make deterministic checks the final disposition. When you must use
an LLM judge:

- **Rubric-level over checklist-level**: evaluate each rubric in a separate
  call (7–12 point accuracy gain over evaluating all rubrics in one pass).
- **Add reasoning (CoT)**: improves accuracy 6–9 points, at token cost.
- **Test for positional bias**: swap candidate order and re-score; if the
  result flips, the judge is responding to position, not quality.
- **Report measurement error**: don't present a single score as ground truth.
  Report the judge identity, paradigm, and bias-sensitivity range.

### The Rubric Design Pattern

A bad rubric: "Is the output helpful?" — too vague, the model can't apply
it consistently.

A good rubric defines precise pass/fail criteria:

```yaml
name: groundedness
description: >
  Every action item must be grounded in an explicit commitment from a
  participant named in the transcript.
scoring:
  - score: 1.0
    description: >
      The participant explicitly committed to a specific, concrete task.
      The transcript must contain a direct statement of commitment from
      the named owner (e.g., "I will," "I'll take that," "let me handle").
  - score: 0.0
    description: >
      The action item is: a conditional statement ("we might"), a discussion
      topic without commitment, a plausible inference from context, or
      something nobody in the transcript actually said.
```

### Implementation

```typescript
interface EvalScore {
  name: string;
  score: number;  // 0.0 to 1.0
  reason: string;
}

async function llmJudge(
  output: string,
  input: string,
  rubric: string,
  model: string = "gpt-4o"
): Promise<EvalScore> {
  const prompt = `
You are an expert evaluator. Score the following agent output against
this rubric:

RUBRIC:
${rubric}

USER INPUT:
${input}

AGENT OUTPUT:
${output}

Return JSON: {"score": <0.0-1.0>, "reason": "<specific evidence>"}
`.trim();

  const response = await callLLM(model, prompt);
  return JSON.parse(response);
}
```

### The Judge Must Be Precise

**Bad:**
> Score whether the output is helpful.

**Good:**
> Score 1 if the output directly answers the user's question with specific,
> actionable information. Score 0 if it's vague, defers without providing
> value, answers a different question, or provides irrelevant context.

### Multiple Dimensions Per Run

Combine scorers for a composite view:

```typescript
async function evaluateRun(
  input: string,
  output: string,
  trace: Span[]
): Promise<RunEval> {
  const scores = await Promise.all([
    scoreGroundedness(output, input),
    scoreCompleteness(output, input),
    scoreStepEfficiency(trace, 10),
    scoreJsonValidity(output),
  ]);

  return {
    scores,
    composite: scores.reduce((sum, s) => sum + s.score, 0) / scores.length,
  };
}
```

## Sampling Strategy

```typescript
interface SamplingConfig {
  development: number;  // 1.0 = 100%
  production: number;   // 0.25 = 25%
}

function shouldEvaluate(samplingConfig: SamplingConfig): boolean {
  const rate = process.env.NODE_ENV === "production"
    ? samplingConfig.production
    : samplingConfig.development;
  return Math.random() < rate;
}
```

The trade-off:
- **100% in dev**: Tight feedback during iteration. Cost is acceptable because
  volume is low.
- **25% in prod**: Catches drift without full-cost evals on every run. You
  still get aggregate quality signals from the sample.

## Benchmark Set Management

A benchmark set is a curated collection of inputs with known-good outputs:

```typescript
interface BenchmarkCase {
  id: string;
  input: string;
  referenceOutput?: string;
  expectedTrajectory?: string[];  // Expected tool call sequence
  scorers: string[];              // Which scorers apply
  source: "manual" | "production-failure";
}

const benchmark: BenchmarkCase[] = [
  {
    id: "groundedness-001",
    input: "Extract action items from meeting-notes-2025-04-01.txt",
    referenceOutput: "...",
    scorers: ["groundedness", "completeness"],
    source: "production-failure",
  },
];
```

### Adding Production Failures to the Benchmark

When a production failure is discovered:

1. **Annotate the trace**: Mark the span where the failure occurred
2. **Extract inputs**: Save the user input that triggered the failure
3. **Define expected output**: What the agent *should* have done
4. **Add to benchmark**: This becomes a permanent regression test

```typescript
async function annotateFailure(
  traceId: string,
  spanId: string,
  expectedOutput: string,
  notes: string
): Promise<BenchmarkCase> {
  const trace = await loadTrace(traceId);
  const failingSpan = trace.findSpan(spanId);

  return {
    id: `prod-failure-${Date.now()}`,
    input: failingSpan.attributes["agent.task"],
    referenceOutput: expectedOutput,
    expectedTrajectory: extractToolSequence(trace),
    scorers: determineScorers(notes),
    source: "production-failure",
  };
}
```

## Scoring Pipeline

Run scorers as a pipeline — fast, deterministic checks first to fail early:

```
1. Code-based structural checks (JSON validity, required fields)
     ↓ pass
2. Heuristic checks (step count, token usage, response length)
     ↓ pass
3. LLM-as-Judge (groundedness, completeness, helpfulness)
     ↓
   Composite score
```

This avoids paying for LLM-as-Judge when the output is structurally broken.
This is the **deterministic-first principle** in action: "never send an AI to
do a linter's job." Anything that can be evaluated deterministically should be
— save LLM evaluation for the parts that genuinely need it. The deterministic
layer is the final gate; LLM-as-judge generates signal but does not make
disposition.

```typescript
async function scorePipeline(
  output: string,
  input: string,
  trace: Span[],
  benchmark: BenchmarkCase
): Promise<RunEval> {
  // Fast, deterministic first
  const structural = benchmark.scorers
    .filter(s => s.startsWith("code:"))
    .map(s => codeScorers[s](output));

  const structuralScore = avg(structural);
  if (structuralScore < 0.5) {
    // Don't bother with LLM-as-Judge for structurally broken outputs
    return { scores: structural, composite: structuralScore };
  }

  // Expensive, subjective second
  const qualitative = await Promise.all(
    benchmark.scorers
      .filter(s => s.startsWith("llm:"))
      .map(s => llmScorers[s](output, input))
  );

  return {
    scores: [...structural, ...qualitative],
    composite: avg([...structural, ...qualitative]),
  };
}
```

### Per-Step Scorers (Workflow-Graph Evaluation)

A refinement of trajectory eval: attach scorers directly to individual
workflow steps rather than only evaluating final output. Each step declares
what "correct" looks like for that step, and the system tracks conformance
automatically. The workflow graph becomes the eval scaffold.

```typescript
const classifyStep = workflow.defineStep({
  name: "classifyEmail",
  scorer: {
    name: "classifiedEmailScore",
    ratio: 1,  // fires on every execution
    evaluate: (input, output) => {
      return output.category === expectedCategory(input) ? 1.0 : 0.0;
    },
  },
});
```

Failed runs can be saved as dataset items for future regression testing — the
same flywheel as the quality loop, but triggered at the step level.

### Deterministic Guardrails Between LLM Steps

Between LLM-call steps, insert deterministic validation that checks the LLM's
output before passing it downstream. Neither the LLM's classification nor the
deterministic check is trusted alone — only their agreement produces the
routing decision.

```typescript
// After LLM classifies an email
const llmCategory = await llm.classify(email);
// Deterministic cross-check via keyword signals
const keywordSignals = detectSponsorKeywords(email);

if (llmCategory === "sponsor" && keywordSignals.length > 0) {
  return { route: "sponsor-pipeline", confidence: "high" };
}
// Disagreement → flag for review, don't auto-route
return { route: "review", reason: "llm-keyword-mismatch" };
```

This operationalizes "never send an AI to do a linter's job": the deterministic
checks are narrow, mechanical validations that don't consume model tokens or
reasoning budget. They act as output gates between LLM steps, catching
misclassifications before they cascade.

## Online Evals: Scoring Production Traces Without Ground Truth

All of the above are **offline** evals — curated inputs, known or judgeable
reference outputs, run on demand. **Online evals** score production traces
*without ground truth*, because real user interactions have no reference
answer.

### Perceived Error Detection

The concrete pattern (Harrison Chase, LangChain): a small purpose-trained
model scans transcripts for signals that the user believes the agent failed:

- Direct complaints: "you messed up," "that's wrong," "no, I meant..."
- Error pasting: user pastes back a code snippet with an error message
- Repetition: user re-asks the same question, implying the first answer failed

```typescript
interface OnlineEvalConfig {
  model: string;          // small, cheap classifier — not a frontier judge
  samplingRate: number;   // 1.0 in production (cost is per-call, not per-token-heavy)
  signals: string[];      // ["complaint", "error_paste", "repetition"];
}

async function perceivedErrorEval(
  transcript: Transcript,
  config: OnlineEvalConfig
): Promise<{ perceivedError: boolean; signals: string[] }> {
  // Small model classifier — runs at full production volume
  return classifyTranscript(transcript, config);
}
```

**Economics:** online evals run at full production volume, so the evaluator
model's per-call cost dominates. Use a cheap purpose-trained classifier, not a
frontier judge. This mirrors the small-model findings: the evaluator doesn't
need to be smart, it needs to be cheap and consistent.

**Why perceived error is viable despite the LLM-as-Judge crisis:** perceived
error is a *classification* task (does this transcript contain an error
signal?) rather than an open-ended quality judgment. This is structurally
closer to MAST (Multi-Agent System Failure Taxonomy, Cemri et al. 2025 —
human inter-annotator agreement κ=0.88, with an LLM-as-judge pipeline that
matches human labels) than to rubric-level quality scoring (RUBRICEVAL:
55.97%). The distinction matters: LLM-as-judge works better on structured
classification than on open-ended rubric evaluation, but it's still
LLM-judged (probabilistic,
not deterministic) — so it's more reliable than outcome-layer rubric judging,
but not a substitute for deterministic checks where those are possible.

### Guardrails vs. Online Evals

The timing distinction matters:

| | Guardrails | Online Evals |
|---|---|---|
| **When** | Before the agent responds | After the agent responds |
| **Effect** | Slows the agent, blocks bad outputs | Doesn't slow the agent, surfaces failures |
| **Cost** | Latency on every call | Compute on every call (async) |
| **Use for** | Preventing known failure modes | Discovering unknown failure modes |

They are complements, not substitutes. Guardrails catch what you already know
to block; online evals catch what you didn't anticipate.

## Model-Swap Evals: The Diff Shortcut

A specialized eval pattern for answering "can I swap in a new model?" when a
deprecation is announced, a new model drops, or a cheaper/faster tier might
suffice (Kevin Gregory, EvolutionIQ).

### The Diff Shortcut

Run the incumbent and candidate models on the same test cases and **diff the
outputs**. If they agree, no labeling is needed — the candidate matches a model
already in production. Only the **disagreement cases** need human labeling, and
those become the most valuable additions to the golden set.

```typescript
async function modelSwapEval(
  incumbent: string,
  candidate: string,
  benchmark: BenchmarkCase[]
): Promise<SwapReport> {
  const incumbentOutputs = await runBatch(incumbent, benchmark);
  const candidateOutputs = await runBatch(candidate, benchmark);

  const agreements = [];
  const disagreements = [];

  for (let i = 0; i < benchmark.length; i++) {
    if (incumbentOutputs[i] === candidateOutputs[i]) {
      agreements.push(benchmark[i]);
    } else {
      disagreements.push({
        case: benchmark[i],
        incumbent: incumbentOutputs[i],
        candidate: candidateOutputs[i],
        // These get human-labeled and added to the golden set
      });
    }
  }

  return {
    agreementRate: agreements.length / benchmark.length,
    disagreements,  // → label these, add to golden set
    recommendation: disagreements.length === 0 ? "safe-to-swap" : "review-disagreements",
  };
}
```

### Three-Dimension Budget

The harness measures three dimensions against configurable threshold gates:

```typescript
interface SwapBudget {
  accuracyFloor: number;   // minimum acceptable accuracy delta (e.g., -0.02)
  costCeiling: number;     // maximum acceptable cost increase (e.g., 1.5x)
  latencyCeiling: number;  // maximum acceptable latency increase (e.g., 1.2x)
}
```

The hardest part is defining what "good enough" looks like; the thresholds
should be the easiest thing to change. For unstructured outputs (summaries),
use either LLM-as-judge or a second extraction layer that pulls structured
facts from the free text and checks those deterministically.

### Saturated vs. Unsaturated Benchmarks

For model builders, unsaturated benchmarks (10–20% scores, room to improve)
are valuable. For your own evals, you want **saturated** benchmarks — your
goal is 99–99.9% accuracy, and a saturated private eval tells you whether
you're there. Public benchmarks have limited purchase not just because of
contamination, but because the saturation level useful for model builders is
the opposite of what you need for production evals.

## Custom Score Definition (Mastra-style)

For frameworks that attach scorers to agent definitions:

```typescript
const groundednessScore = {
  name: "Groundedness",
  description: "Measures whether action items are backed by explicit commitments",
  judge: "gpt-4o",
  instructions: `
Score each action item in the agent's output:

Score 1: The participant explicitly committed to a specific task.
  Evidence: "I will...", "I'll take that...", "Let me handle..."
Score 0: Conditional ("we might"), discussion topic, inference, or
  something nobody said.

Return { score: <0-1>, items: [{ text, score, reason }] }
  `.trim(),
};

const agent = mastra.defineAgent({
  name: "action-item-extractor",
  instructions: "...",
  scorers: [groundednessScore],
});
```
