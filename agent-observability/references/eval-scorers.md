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
