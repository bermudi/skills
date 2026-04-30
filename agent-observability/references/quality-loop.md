# The Quality Loop

> The continuous feedback flywheel that turns production failures into
> permanent regression tests.

## The Flywheel

```
code → traces → evals → scorers → back to code
```

This isn't a one-time setup — it's the mechanism through which agents get
better over time. Not from one-off fixes, but from a growing corpus of
real failures turned into regression tests.

## Step 1: Code Produces Traces

The agent runs, emitting structured spans for every decision, tool call,
and sub-agent delegation. This is covered in `references/opentelemetry-tracing.md`.

Key requirement: traces must be **accessible for review**. If traces expire
after 24 hours or live in a system nobody checks, the loop breaks.

## Step 2: Traces Feed Evals

Scoring functions evaluate the agent's output against quality criteria.
This is covered in `references/eval-scorers.md`.

Key requirement: evals must run **automatically** on a sample of production
traces. If someone has to manually trigger evaluation, the loop doesn't spin.

## Step 3: Evals Produce Scores

Each run gets a 0–1 score per dimension. Track these over time:

```typescript
interface QualityTrend {
  dimension: string;
  scores: { timestamp: Date; score: number }[];
  trend: "improving" | "stable" | "degrading";
}
```

**The trend matters more than any individual score.** A single 0.83 on
groundedness is a data point. Groundedness trending from 0.83 to 0.72
to 0.64 over three weeks is a problem.

### Score Dashboard (Minimal)

```typescript
function computeTrend(scores: number[]): "improving" | "stable" | "degrading" {
  if (scores.length < 5) return "stable";

  const recent = scores.slice(-5);
  const older = scores.slice(0, -5);
  const delta = avg(recent) - avg(older);

  if (delta > 0.05) return "improving";
  if (delta < -0.05) return "degrading";
  return "stable";
}
```

## Step 4: Scores Send You Back to Code

Low scores reveal:
- **Prompt deficiencies**: The instructions are too vague (the groundedness
  example: V1 prompt scored 0.83, V2 prompt scored 1.0)
- **Tool design problems**: The tool's interface leads the agent to wrong
  choices
- **Model behavior changes**: A model upgrade changed how the agent interprets
  instructions

### Diagnosis Workflow

```
Low score on groundedness
  → Read the failing traces
  → Find the pattern: what do failures have in common?
  → Hypothesis: agent is inferring action items from discussion, not commitments
  → Fix: update prompt to distinguish discussion from commitment
  → Verify: rerun eval set, score should improve
```

## Step 5: Production Failures Become Eval Cases

This is the compounding value of the loop. Every fixed failure becomes
a permanent regression test:

```typescript
const benchmarkSet: BenchmarkCase[] = loadBenchmark();

// After fixing a prod failure
benchmarkSet.push({
  id: "prod-2025-04-27-invoice-not-sent",
  input: "Finalize and send invoice INV-2025-0427 for Acme Corp",
  expectedTrajectory: [
    "tool.lookup_invoice",
    "tool.check_status",
    "tool.finalize_invoice",
    "tool.send_invoice",  // ← this was the missing step
  ],
  scorers: ["trajectory-adherence"],
  source: "production-failure",
});

saveBenchmark(benchmarkSet);
```

The benchmark set becomes a living record of everything the agent has
struggled with — the most accurate picture of what it needs to handle.

## The Annotation Workflow

When someone discovers an agent failure in production:

1. **Find the trace**: Search by user ID, timestamp, or task description
2. **Mark the failing span**: Click the span where the decision went wrong
3. **Describe expected behavior**: What should the agent have done?
4. **Convert to eval case**: The system extracts inputs and creates a
   benchmark entry

```typescript
interface Annotation {
  traceId: string;
  spanId: string;
  expectedOutput: string;
  expectedTrajectory?: string[];
  notes: string;
  annotatedBy: string;
  annotatedAt: Date;
}

async function annotationToEvalCase(
  annotation: Annotation
): Promise<BenchmarkCase> {
  const trace = await loadTrace(annotation.traceId);

  return {
    id: `annotated-${annotation.traceId}-${annotation.spanId}`,
    input: trace.rootSpan.attributes["agent.task"],
    expectedTrajectory: annotation.expectedTrajectory,
    referenceOutput: annotation.expectedOutput,
    scorers: inferScorersFromAnnotation(annotation),
    source: "annotation",
    metadata: {
      annotatedBy: annotation.annotatedBy,
      annotatedAt: annotation.annotatedAt,
      notes: annotation.notes,
    },
  };
}
```

## Confidence to Ship

Without the quality loop:
- Model upgrades: ship on intuition
- Tool changes: ship on intuition
- Prompt changes: ship on intuition

With the quality loop:
- **Model upgrades**: Run the eval set against the new model. Score delta
  tells you whether it's safe.
- **Tool changes**: Validate against historical failure cases. Did any old
  regression come back?
- **Prompt changes**: The eval set is your test bench. Iterate until scores
  improve, then ship.

```typescript
async function validateModelUpgrade(
  newModel: string,
  benchmarkSet: BenchmarkCase[]
): Promise<ModelUpgradeReport> {
  const before = await scoreBenchmark(currentModel, benchmarkSet);
  const after = await scoreBenchmark(newModel, benchmarkSet);

  return {
    model: newModel,
    scoreDelta: avg(after) - avg(before),
    regressions: findRegressions(before, after),  // cases that got worse
    improvements: findImprovements(before, after), // cases that got better
    recommendation:
      avg(after) >= avg(before) ? "safe-to-upgrade" : "hold-and-investigate",
  };
}
```

## Implementation Pattern: Nightly Quality Run

Run the full eval set on a schedule:

```bash
#!/bin/bash
# nightly-quality.sh — Runs at 2am, reports to Slack

EVAL_SET="./evals/benchmark.json"
MODEL="${1:-claude-sonnet-4}"

echo "Running quality check with model: $MODEL"
result=$(agent-eval run --benchmark "$EVAL_SET" --model "$MODEL" --sample-rate 1.0)

# Parse scores and trend
composite=$(echo "$result" | jq '.composite_score')
trend=$(echo "$result" | jq -r '.trend')
regressions=$(echo "$result" | jq '.regressions | length')

if [ "$(echo "$composite < 0.80" | bc)" -eq 1 ] || [ "$regressions" -gt 0 ]; then
  # Alert on degradation
  curl -X POST "$SLACK_WEBHOOK" \
    -H "Content-Type: application/json" \
    -d "{
      \"text\": \"⚠️ Agent quality alert: composite=$composite, trend=$trend, regressions=$regressions\"
    }"
fi
```

## The Compounding Effect

Week 1: 3 eval cases (manually created)
Week 2: 5 eval cases (2 new from production)
Week 8: 23 eval cases (18 from production, 5 manual)
Week 26: 67 eval cases (59 from production, 8 manual)

The eval set grows with the agent. Every failure makes the agent harder to
break in the same way. This is the quality loop's real power: not the
individual scores, but the ever-growing safety net.
