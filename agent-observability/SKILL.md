---
name: agent-observability
description: >
  Design and implement observability for AI agent systems — structured tracing
  (OpenTelemetry spans), eval scoring (LLM-as-judge and code-based), and
  quality loops that turn production failures into permanent regression tests.
  Use when: adding tracing to an agent, setting up evals for agent output
  quality, building a quality feedback loop, debugging an agent failure in
  production, instrumenting tool calls and sub-agent delegation with spans,
  or designing an agent architecture where you need to see what decisions
  the agent made and why. Also triggers when users ask about "agent
  observability," "agent tracing," "agent evals," "LLM-as-judge," "quality
  scoring," "debugging agent decisions," or "why did my agent do X."
---

# Agent Observability

Design and implement the three-layer quality infrastructure that makes agents
shippable: traces (decision narratives), evals (probabilistic CI), and the
quality loop (continuous feedback flywheel).

## The Core Insight

AI agents fail differently than deterministic software. Outputs can look
correct while decisions are wrong. System metrics (latency, error rate) can
be green while the agent silently does the wrong thing. You need infrastructure
that watches **the agent**, not just the server.

> System metrics watch the machine. Quality metrics watch the agent. If you're
> only watching system metrics, you're not watching the agent.

This is an architectural decision, not an afterthought. If your agent doesn't
emit structured traces, you can't evaluate trajectory. If it doesn't log tool
calls with parameters, you can't measure efficiency. If it doesn't expose
intermediate reasoning, you can't diagnose failures.

## The Three Pillars

### Logs: The Raw Record

Every event, tool call, model response — timestamped and stored. Logs tell
you **what** happened at a single moment. But a log entry is isolated: it
doesn't tell you why one step led to the next, what the agent was reasoning
about, or what context it was carrying.

**Logs alone are archaeology.** When an agent finalizes an invoice but never
sends it, every log line looks correct — `finalize_invoice` was called, no
errors were thrown. Finding the bug means scrolling a flat feed of tool calls,
noticing the *absence* of `send_invoice` (an event you'd have to already
know should exist), and piecing together why the agent misinterpreted
"open" as "completed." The logs have the data. They don't have the story.

### Traces: The Decision Tree

A trace is not a more detailed log — it's a different shape entirely: a
**tree**. The root is the top-level task. Every decision, tool call, and
sub-agent delegation becomes a node (a **span**) with its own inputs,
outputs, and status. The connections between spans show you **why**.

When something goes wrong, you walk down the tree:
- Root span: the user's request
- Child spans: decisions, tool calls, sub-agent delegations
- Each span: named, timed unit of work with inputs, outputs, and status
- The tree structure shows the reasoning chain

**The invoice failure, revisited:** In the trace tree, `ledger`'s subtree
shows `lookup_invoice` → `check_status` → `finalize_invoice`. Then the tree
stops. Walking back up to the root agent's span reveals the misinterpretation.
The trace tells the story the logs couldn't.

**Implementation:** Use OpenTelemetry spans — the same primitives that trace
requests through microservices trace decisions through agents. Tools like
Arize Phoenix, Langfuse, Braintrust, and Mastra all speak OpenTelemetry.
Read `references/opentelemetry-tracing.md` for span design patterns,
naming conventions, and instrumentation strategies.

### Metrics: Aggregate Patterns

Logs and traces answer questions about **one run**. Metrics answer questions
about **all of them**, aggregated across thousands of traces.

Two categories:
- **System metrics**: Latency, error rate, token costs, uptime. These watch
  the server.
- **Quality metrics**: Correctness, trajectory adherence, whether outputs
  match the task. These watch the agent. They're computed by running
  evals against trace data.

If you're only watching system metrics, agent failures get discovered
manually, after the fact, when someone happens to notice.

## Evals: CI for Probabilistic Systems

Traditional tests assume determinism: same input → same output. Agents reject
that assumption. Unit tests can't judge "helpfulness." Integration tests can't
assert against natural language. End-to-end tests can't handle variable step
counts.

Evals replace binary assertions with spectrum scoring (0–1). They measure
quality across benchmark sets, scoring trajectory and outcomes.

### The Four Layers

Measure from the **outside in** — start with outcome, dig into trajectory when
needed:

1. **Component Layer** (deterministic): Tools and functions. Unit-testable.
   A JSON parser either parses or it doesn't. Your existing testing instincts
   work here.

2. **Trajectory**: Did the agent take the right steps? Select the right tools?
   Construct the right parameters? An agent that gets the right answer in 25
   tool calls when 3 would do has a trajectory problem. An agent that calls
   the wrong tool but happens to get the right answer also has a trajectory
   problem — one that will likely become an outcome problem.

3. **Outcome**: Is the final answer correct, helpful, grounded, and complete?
   This is the hardest layer because those questions are subjective. You can't
   write an assertion for "helpful." This is where **LLM-as-Judge** comes in:
   a second language model evaluates the agent's output against a rubric.
   Humans define what "good" means; the model applies that definition at scale.

4. **System Monitoring**: Watching for quality degrading in production at
   scale — not individual failures, but patterns across real usage over time.

### The Four Quality Dimensions

| Dimension | Question | Depends On |
|-----------|----------|------------|
| **Effectiveness** | Did the agent achieve what the user wanted? | Full trace visibility |
| **Efficiency** | Did it do it well? (steps, time, tokens) | Step counting, tool call logging |
| **Robustness** | Does it hold up under pressure? | Error-level observability |
| **Safety & Alignment** | Does it stay within bounds? Refuse when it should? | Non-negotiable |

**You can only measure what you can see.** If your agent doesn't emit structured
traces, you can't evaluate trajectory. If it doesn't log tool calls with
parameters, you can't measure efficiency.

### LLM-as-Judge

For subjective criteria, use a second LLM call with a precise rubric. The
division of labor: humans define the criteria, models apply them at volume.

**The groundedness example** (from Damian Galarza's quality series):

V1 prompt: "Extract action items from this meeting transcript."
- Result: 6 action items, one hallucinated ("create a CLAUDE.md" — suggested
  by a participant, never committed to)
- Score: 0.83 (5/6 grounded)

LLM-as-Judge rubric defines "grounded" precisely:
- Score 1: participant explicitly committed to a specific task
- Score 0: conditional ("we might"), discussion topic without commitment,
  plausible inference, or something nobody actually said

V2 prompt: Incorporates the groundedness criteria *in the tool instructions*
— "do not include advice or suggestions never committed to," "must contain
an explicit commitment from the owner."
- Result: 5 action items, all grounded
- Score: 1.0

**The loop worked:** vague prompt → eval caught the problem → specific prompt
→ perfect score.

> [!warning] Limitation
> Automated evals don't catch everything. Regularly reading production traces
> directly surfaces the subtle failures no rubric anticipated.

Read `references/eval-scorers.md` for implementing LLM-as-judge and code-based
scorers, rubric design patterns, and sampling strategies.

## The Quality Loop

The flywheel that ties traces and evals into continuous improvement:

```
code → traces → evals → scorers → back to code
```

1. **Code produces traces**: The agent runs, emitting structured spans.
2. **Traces feed evals**: Scoring functions evaluate the agent's output.
3. **Evals produce scores**: Each run gets a 0–1 score.
4. **Scores send you back to code**: Low scores reveal prompt deficiencies,
   tool design problems, or model behavior changes.
5. **Production failures become eval cases**: Annotated failures join the
   benchmark set, which becomes a living record of everything the agent
   has struggled with.

### Why the Flywheel Matters

- **Model upgrades**: Every model change can alter agent behavior. The eval
  set gives you a test bench to measure before shipping.
- **Tool changes**: New tools or refactored tool interfaces can be validated
  against historical failures.
- **Regression prevention**: The eval set grows with every failure, making it
  harder to regress on edge cases you've already encountered.
- **Confidence to ship**: Without evals, you ship on intuition. With evals,
  you ship on evidence.

### Sampling Strategy

Not every production run needs full LLM-as-judge evals. Sampling controls cost:
- **Development**: 100% sampling for tight feedback
- **Production**: 25% (or lower) to catch drift without full-cost evals

Read `references/quality-loop.md` for the full implementation pattern:
benchmark set management, scoring pipeline design, and the production-
failure-to-eval-case workflow.

## Implementation Checklist

When adding observability to an agent system, work through this checklist:

### Tracing
- [ ] Every agent run creates a root span
- [ ] Tool calls are child spans with parameters and results
- [ ] Sub-agent delegations create nested span trees
- [ ] LLM calls are spans with token counts in attributes
- [ ] Spans carry trace IDs for correlation across services
- [ ] Span naming follows a consistent convention (action, not implementation)

### Logs
- [ ] Tool calls logged with parameters (not just "tool called")
- [ ] Model responses logged for audit
- [ ] Errors include trace ID for correlation
- [ ] Log levels distinguish agent decisions from system events

### Evals
- [ ] Benchmark set exists with known-good reference outputs
- [ ] LLM-as-Judge rubrics precisely define scoring criteria
- [ ] Code-based scorers exist for deterministic checks
- [ ] Sampling rates configured per environment

### Quality Loop
- [ ] Production traces are accessible for review
- [ ] Failure annotation workflow exists (trace → eval case)
- [ ] Eval set grows with production discoveries
- [ ] Scores are tracked over time (trend, not snapshot)

## Architecture Decisions

These decisions shape the rest of the implementation. Make them first.

### OpenTelemetry vs. Proprietary

Use OpenTelemetry unless you have a strong reason not to. It gives you:
- Standard span/trace IDs across services
- Exporter flexibility (Arize Phoenix, Langfuse, Braintrust, Datadog, generic OTLP)
- No vendor lock-in
- Existing ecosystem for visualization and analysis

Proprietary formats isolate your traces from the rest of your observability
stack. You can't correlate agent decisions with database queries, API calls,
or user sessions.

### Embedded vs. External Scorers

Scorers can live alongside agent code (attached to agent definitions) or in
a separate pipeline. Keep them alongside the agent — when you change the
agent's instructions, you want to immediately see the effect on scores
without context-switching to a separate system.

### Snapshot vs. Trend

Never evaluate agent quality as a snapshot. Single-run scores are noisy.
Track scores over time — is quality holding, improving, or degrading across
changes? The trend matters more than any individual score.

## Gotchas

- **Green system metrics mask agent failures.** The Emma/invoice case: every
  system metric was green while the agent silently failed. Quality metrics
  must be separate from system metrics.

- **Absence of a tool call is invisible in logs.** In a flat log feed, a
  missing call is invisible (the absence of a line). In a trace tree, you
  can see everything the agent did — and exactly where it stopped.

- **LLM-as-Judge requires precise rubrics.** "Is the output helpful?" is
  useless. "Score 1 if the output directly answers the user's question with
  specific, actionable information. Score 0 if it's vague, defers without
  providing value, or answers a different question." Give the judge concrete
  pass/fail criteria.

- **Evals don't catch everything.** Regularly read production traces directly.
  The subtle failures no rubric anticipated are exactly the ones you need to
  find and add to the benchmark set.

- **Observability must be designed in.** Retroactively adding spans to an
  existing agent means re-architecting the agent loop. Instrument from day
  one. Every tool call, every model call, every sub-agent delegation should
  produce a span.

- **Context window is not a trace.** The agent's conversation history shows
  what was *said*, not what was *decided*. A trace captures the decision
  structure — which tool was chosen, why, and what happened next — that the
  conversation history flattens.

## Reference Files

Read when implementing specific parts of the observability stack:

| When you need to... | Read |
|---------------------|------|
| Instrument spans, design span trees, choose exporters | `references/opentelemetry-tracing.md` |
| Build LLM-as-judge scorers, design rubrics, set up sampling | `references/eval-scorers.md` |
| Set up the quality flywheel, manage benchmark sets, annotate failures | `references/quality-loop.md` |
| Choose an observability platform (Langfuse vs. Arize vs. Braintrust vs. Mastra) | `references/platforms.md` |
