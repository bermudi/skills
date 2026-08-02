---
name: agent-observability
description: >
  Design and implement observability for AI agent systems — structured tracing
  (OpenTelemetry spans), eval scoring (LLM-as-judge and code-based), online
  evals, and quality loops that turn production failures into permanent
  regression tests. Covers adding tracing to an agent, setting up evals for
  agent output quality, building a quality feedback loop, debugging agent
  failures in production, instrumenting tool calls and sub-agent delegation,
  and architectures where you need to see what decisions the agent made and
  why. Invoked explicitly.
disable-model-invocation: true
---

# Agent Observability

Build the three-layer quality infrastructure that makes agents shippable:
traces (decision narratives), evals (probabilistic CI), and the quality loop
(continuous feedback flywheel).

System metrics watch the machine. Quality metrics watch the agent. Outputs can
look correct while decisions are wrong; latency and error-rate can be green
while the agent silently does the wrong thing. You need infrastructure that
watches **the agent**, not just the server.

## The Three Pillars

**Logs — the raw record.** Every event, tool call, model response, timestamped
and stored. A log entry is isolated: it tells you *what* happened at one
moment, not why one step led to the next. Logs alone are archaeology — a flat
feed where a *missing* tool call is invisible (the absence of a line).

**Traces — the decision tree.** A trace is a tree, not a more detailed log. The
root is the top-level task; every decision, tool call, and sub-agent delegation
is a node (a **span**) with inputs, outputs, and status. The tree structure
shows *why*. When something goes wrong, walk down the tree to find where it
diverged, then back up to see the misinterpretation that caused it. Implement
with OpenTelemetry spans — the same primitives that trace requests through
microservices. See `references/opentelemetry-tracing.md`.

**Metrics — aggregate patterns.** Logs and traces answer questions about one
run. Metrics answer questions about all of them. Two categories:
- **System metrics**: latency, error rate, token costs, uptime. Watch the server.
- **Quality metrics**: correctness, trajectory adherence, grounding. Watch the
  agent. Computed by running evals against trace data.

## Beyond Post-Execution: The Tracing Spectrum

The three pillars above are **post-execution** observability — what happened
after the code ran. Vaibhav Gupta (Boundary ML) argues this is only one-third
of the picture: in a world where agents write most of the code and humans
don't read every line, you also need **design-time tracing** (the shape of the
system before code is written) and **code-time tracing** (visualization of
structure without reading every line). Together the three layers close a
feedback loop that extends the quality loop — `design → code → execution →
agent feedback → improved design` — so you debug the *design assumptions* that
produced the code, not just the code. See
`references/opentelemetry-tracing.md` for the full spectrum, BAML's
compiler-level auto-instrumentation, and the OTEL type-system limitation that
makes rich agent tracing harder than it looks.

## Agents as Trace Consumers

Traces must be **queryable by agents**, not just visualizable for humans — the
agent becomes the primary consumer of its own traces, closing the feedback
loop between execution and design. This requires type-safe, schema-aware
queryability (e.g. `find everything where latency > 1s and the prompt
contained "generate image"`), which OTEL's wire format degrades to
unqueryable JSON strings. See `references/opentelemetry-tracing.md` for the
typed-layer solutions.

## Evals: CI for Probabilistic Systems

Agents reject determinism. Unit tests can't judge "helpfulness"; integration
tests can't assert against natural language; end-to-end tests can't handle
variable step counts. Evals replace binary assertions with spectrum scoring
(0–1) across benchmark sets.

### The Four Layers

Measure **outside in** — start with outcome, dig into trajectory when needed:

1. **Component** (deterministic): tools and functions. Unit-testable. Existing
   instincts work.
2. **Trajectory**: did the agent take the right steps, pick the right tools,
   build the right parameters? Right answer in 25 calls when 3 would do is a
   trajectory problem.
3. **Outcome**: is the final answer correct, helpful, grounded, complete?
   Subjective — this is where **LLM-as-Judge** applies: humans define the
   rubric, a second model applies it at scale. But LLM-as-Judge is unreliable
   — see [The LLM-as-Judge Reliability Problem](#the-llm-as-judge-reliability-problem)
   below before relying on it.
4. **System monitoring**: watching for quality degrading in production at scale
   — patterns across real usage, not individual failures.

### The Four Quality Dimensions

| Dimension | Question | Depends On |
|-----------|----------|------------|
| **Effectiveness** | Did the agent achieve what the user wanted? | Full trace visibility |
| **Efficiency** | Did it do it well? (steps, time, tokens) | Step counting, tool call logging |
| **Robustness** | Does it hold up under pressure? | Error-level observability |
| **Safety & Alignment** | Does it stay within bounds? Refuse when it should? | Non-negotiable |

You can only measure what you can see. No structured traces → no trajectory
eval. No tool-call logging → no efficiency metric.

### The LLM-as-Judge Reliability Problem

LLM-as-Judge is the standard outcome-layer mechanism, but four independent
evidence streams challenge its reliability:

- **RUBRICEVAL** (Pan et al., 2026): GPT-4o achieves only **55.97% balanced
  accuracy** on hard rubric judgments — near chance for a judge widely used in
  instruction-following benchmarks. Judge selection alone shifts scores by up
  to 25 points.
- **DELEGATE-52** (Laban et al., 2026): even GPT 5.4 as judge captures **at
  most 25% of the variance** of domain-specific parsing metrics. Generic
  rubrics failed to detect nuanced semantic corruption.
- **Bias in the Loop** (Zhao et al., 2026): 12 prompt-induced biases produce
  **40+ point swings** from candidate ordering and prompt framing alone —
  directional, not random.
- **Practitioner consensus**: Dex Horthy ("models are optimized to tell you
  what you want to hear"), Samuel Colvin ("the lunatics running the asylum")
  both prefer deterministic checks.

**The synthesis: deterministic checks as the final gate, LLM-as-judge for
signal generation but not for disposition.** Run code-based scorers first
(structural validation, regex assertions, reference comparison); reserve
LLM-as-judge for the subjective residue those cannot cover. When you must use
an LLM judge, the paradigm matters: rubric-level evaluation (one call per
rubric, with reasoning) outperforms checklist-level direct scoring by 7–12
points. Report eval results with bias sensitivity analysis (swap candidate
order, test neutral vs. structured prompts), not just aggregate accuracy.

For scorer implementation, rubric design, sampling, and the deterministic-first
pipeline, see `references/eval-scorers.md`.

### Online Evals: The Production-Side Layer

The four layers above are **offline** evals — curated inputs, known or
judgeable reference outputs, run on demand. **Online evals** (Harrison Chase,
LangChain) score production traces *without ground truth*, because real user
interactions have no reference answer. The concrete pattern is **perceived
error**: a small purpose-trained model scans transcripts for signals that the
user believes the agent failed. Online evals run at full production volume, so
the evaluator's per-call cost dominates — use a cheap classifier, not a
frontier judge. They are complements to (not substitutes for) **guardrails**,
which run *before* the agent responds. See `references/eval-scorers.md` for
the full pattern, the guardrails-vs-online-evals distinction, and why
perceived-error classification is more reliable than open-ended rubric
judging.

## The Quality Loop

```
code → traces → evals → scorers → back to code
```

1. **Code produces traces** — the agent emits structured spans.
2. **Traces feed evals** — scorers evaluate output against criteria.
3. **Evals produce scores** — each run gets 0–1 per dimension.
4. **Scores send you back to code** — low scores reveal prompt deficiencies,
   tool design problems, or model behavior changes.
5. **Production failures become eval cases** — annotated failures join the
   benchmark set, a living record of everything the agent has struggled with.

The flywheel gives you a test bench for model upgrades, tool changes, and
prompt edits — ship on evidence, not intuition. Sampling controls cost:
100% in development for tight feedback, ~25% (or lower) in production to catch
drift. See `references/quality-loop.md` for the full implementation pattern.

## Implementation Checklist

### Tracing
- [ ] Every agent run creates a root span
- [ ] Tool calls are child spans with parameters and results
- [ ] Sub-agent delegations create nested span trees
- [ ] LLM calls are spans with token counts in attributes
- [ ] Spans carry trace IDs for correlation across services
- [ ] Span naming follows a consistent convention (action, not implementation)
- [ ] Traces are queryable by agents, not just visualizable for humans

### Logs
- [ ] Tool calls logged with parameters (not just "tool called")
- [ ] Model responses logged for audit
- [ ] Errors include trace ID for correlation
- [ ] Log levels distinguish agent decisions from system events

### Evals
- [ ] Code-based scorers exist for every deterministic check (structural validation, regex assertions, reference comparison)
- [ ] Code-based scorers run before LLM-as-Judge (fail early on structurally broken outputs)
- [ ] LLM-as-Judge rubrics precisely define scoring criteria, with rubric-level evaluation (one call per rubric) and reasoning
- [ ] Bias sensitivity analysis is run (swap candidate order, test neutral vs. structured prompts)
- [ ] Sampling rates configured per environment
- [ ] Online evals run over production traces (perceived-error detection or equivalent)
- [ ] Guardrails (pre-response) and online evals (post-response) are both in place

### Quality Loop
- [ ] Production traces are accessible for review
- [ ] Failure annotation workflow exists (trace → eval case)
- [ ] Eval set grows with production discoveries
- [ ] Scores are tracked over time (trend, not snapshot)
- [ ] Model-swap eval harness exists for model-replacement decisions

## Architecture Decisions

Make these first — they shape the rest of the implementation.

**OpenTelemetry vs. proprietary.** Use OpenTelemetry unless you have a strong
reason not to. Standard span/trace IDs across services, exporter flexibility
(Arize Phoenix, Langfuse, Braintrust, Datadog, generic OTLP), no vendor lock-in.
Proprietary formats isolate your traces from the rest of the observability
stack — you can't correlate agent decisions with database queries or user
sessions.

> **OTEL type-system caveat.** OTEL accepts only string, boolean, int, float,
> and sequences of each. Rich data gets JSON-serialized into string attributes,
> bloating wire size ~8x and producing unqueryable blobs. OTEL is necessary
> plumbing but not sufficient for rich agent tracing — you may need a typed
> layer on top (BAML's compiler-level approach is one solution). See
> `references/opentelemetry-tracing.md`.

**Embedded vs. external scorers.** Keep scorers alongside agent code, not in a
separate pipeline. When you change the agent's instructions, you want to see
the effect on scores immediately, without context-switching.

**Deterministic-first scoring.** Run code-based scorers (structural validation,
regex assertions, reference comparison) before LLM-as-judge. Fail early on
structurally broken outputs — don't pay for an LLM judge when the JSON doesn't
parse. The deterministic layer is the final gate; LLM-as-judge generates
signal but does not make disposition. This is the eval-layer analog of "never
send an AI to do a linter's job."

**Snapshot vs. trend.** Never evaluate agent quality as a snapshot. Single-run
scores are noisy. Track the trend — holding, improving, or degrading across
changes? The trend matters more than any individual score.

## Gotchas

- **Green system metrics mask agent failures.** System metrics can be entirely
  green while the agent silently does the wrong thing. Quality metrics must be
  separate from system metrics.

- **Absence of a tool call is invisible in logs.** In a flat log feed, a
  missing call is the absence of a line. In a trace tree, you can see
  everything the agent did — and exactly where it stopped.

- **LLM-as-Judge is not a rubber stamp.** "Is the output helpful?" is useless,
  but even precise rubrics are unreliable: GPT-4o gets 55.97% balanced
  accuracy on hard rubric judgments, and prompt framing alone swings scores
  by 40+ points. Give the judge concrete pass/fail criteria, run rubric-level
  (not checklist-level) evaluation with reasoning, swap candidate order to
  test for positional bias, and treat the score as a noisy signal — not a
  verdict. Use deterministic checks as the final gate.

- **Evals don't catch everything.** Regularly read production traces directly.
  The subtle failures no rubric anticipated are exactly the ones you need to
  find and add to the benchmark set.

- **The expectation gap widens with capability.** As your agent gets more
  capable, users build expectations faster than capability grows. The delta
  between expected and actual is the real problem — more capability means more
  "reds" (unmet expectations). Tracing isn't a cost you pay when things go
  wrong; it's an investment in understanding a system whose failure surface
  grows as it improves.

- **Instrument early, but retrofitting is not a rewrite.** Adding spans to an
  existing agent loop is usually a wrapper-and-attribute job, not a
  re-architecture — but it's still cheaper to instrument from day one, when
  the boundaries between decisions are fresh. Every tool call, model call, and
  sub-agent delegation should produce a span. Compiler-level auto-instrumentation
  (BAML) makes this automatic for LLM-calling functions — no opt-in required.

- **Context window is not a trace.** The conversation history shows what was
  *said*, not what was *decided*. A trace captures the decision structure —
  which tool was chosen, why, and what happened next — that the conversation
  history flattens.

- **Reward hacking exploits the verification layer.** When the eval scorer is
  the verifier, agent outputs can be optimized to satisfy the scorer's rubric
  without genuinely improving quality (timer deletion, cached results,
  fabricated tool usage). The defense is the same as the deterministic-first
  principle: separate the proposal (LLM, possibly unreliable) from the
  disposition (deterministic, verifiable).

## Reference Files

| When you need to... | Read |
|---------------------|------|
| Instrument spans, design span trees, choose exporters, understand the OTEL type-system limitation, the tracing spectrum, or the session→turn→model-request data model | `references/opentelemetry-tracing.md` |
| Build LLM-as-judge scorers, design rubrics, set up sampling, implement the deterministic-first pipeline, set up online evals or model-swap evals | `references/eval-scorers.md` |
| Set up the quality flywheel, manage benchmark sets, annotate failures | `references/quality-loop.md` |
| Choose an observability platform (Langfuse vs. Arize vs. Braintrust vs. Mastra vs. BAML) | `references/platforms.md` |
