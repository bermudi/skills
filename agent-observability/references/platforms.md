# Observability Platforms

> Choosing and integrating observability infrastructure for agent systems.

## Platform Comparison

| Platform | Strength | Trade-off |
|----------|----------|-----------|
| **Mastra** | Built-in tracing + evals + studio; TypeScript-native | Framework lock-in; must use Mastra |
| **Langfuse** | Open-source; trace + eval + prompt management; OTEL-native | Self-host or paid cloud |
| **Arize Phoenix** | Open-source; agent-specific span visualization; local or cloud | Eval features less mature |
| **Braintrust** | Experiment tracking; eval-focused; good for comparison | Less agent-specific tooling |
| **Datadog** | Existing infra integration; no new service to manage | Expensive at scale; generic (not agent-aware) |
| **Honeycomb** | Excellent query language for trace inspection | Generic; no eval features |

## Mastra (TypeScript Agent Framework)

Mastra is the most integrated option — it's both an agent framework and an
observability platform. If you're building a TypeScript agent, it gives you
tracing, evals, and a local studio out of the box.

**Architecture:**
- **Agents**: Defined with scorers, tools, and instructions
- **Tools**: Schema-typed input/output, can delegate to sub-agents
- **Observability**: Traces structured as spans (agent runs, tool calls, LLM
  calls, memory, workspace)
- **Evals**: Built-in scores (answer relevancy, faithfulness, hallucination,
  completeness, tool trajectory, prompt alignment, context quality) plus
  custom scores
- **Sampling**: Per-scorer sampling rates (100% dev, 25% prod)

**Export options**: default (local storage for Mastra Studio), cloud (hosted
Studio), or external (Arize Phoenix, Braintrust, Datadog, generic OTLP).

**Best for**: TypeScript projects that want observability built into the
framework rather than bolted on.

## Langfuse (Open-Source Observability)

Langfuse provides tracing, evals, and prompt management as an open-source
platform. Install self-hosted or use the cloud version.

**Integration** (OpenTelemetry):

```typescript
import { LangfuseSpanProcessor } from "@langfuse/otel";

const provider = new BasicTracerProvider();
provider.addSpanProcessor(
  new LangfuseSpanProcessor({
    publicKey: process.env.LANGFUSE_PUBLIC_KEY,
    secretKey: process.env.LANGFUSE_SECRET_KEY,
    baseUrl: process.env.LANGFUSE_BASE_URL,
  })
);
provider.register();
```

**Best for**: Teams that want open-source observability with eval scoring
and don't want framework lock-in.

## Arize Phoenix (Agent-Specific Visualization)

Phoenix specializes in visualizing agent decision trees. Its span viewer
is designed for the tree structure of agent traces rather than the linear
structure of request traces.

**Local mode** for development:

```bash
pip install arize-phoenix
phoenix serve
```

Then send OTLP traces to `http://localhost:6006/v1/traces`.

**Best for**: Teams that want specialized agent trace visualization and
already have their own eval infrastructure.

## Decision Framework

```
Are you building a new TypeScript agent from scratch?
  → Use Mastra. You get the full stack integrated.

Are you adding observability to an existing agent (any language)?
  → Use OpenTelemetry + Arize Phoenix (local dev) or Langfuse (production).

Are you already on Datadog/Honeycomb?
  → Send OTLP traces there. Add evals as a separate concern.

Do you need experiment tracking (A/B testing prompts/models)?
  → Use Braintrust for the eval/experiment layer + OTEL for tracing.
```

## Self-Hosted vs. Cloud

| | Self-Hosted | Cloud |
|---|---|---|
| **Cost** | Infrastructure + maintenance | Per-event pricing |
| **Setup** | Days | Minutes |
| **Data control** | Full | Shared responsibility |
| **Updates** | Manual | Automatic |

Start with cloud for speed. Move to self-hosted when data volume makes
per-event pricing painful or you have compliance requirements.
