# OpenTelemetry Tracing for Agents

> How to instrument agent decision chains with OpenTelemetry spans.

## Why OpenTelemetry

The same primitives that trace requests through microservices trace decisions
through agents: spans, trace IDs, parent-child relationships. What's new isn't
the infrastructure — it's what you're looking at: a decision chain instead of
a request path.

Using OpenTelemetry gives you:
- Standard span/trace IDs for correlation across services
- Exporter flexibility (no vendor lock-in)
- Existing ecosystem for visualization and analysis
- The ability to correlate agent decisions with database queries, API calls,
  and user sessions

## The OTEL Type-System Limitation

OTEL is necessary plumbing, but its type system is insufficient for rich agent
tracing. OTEL accepts only: string, boolean, int, float, and sequences of
each. The consequences (Vaibhav Gupta, Boundary ML):

- People JSON-serialize rich data into string attributes
- This bloats wire size by approximately **8x** (100 bytes of real data → 800
  bytes on the wire)
- The JSON strings can't be queried — you can't write SQL-like queries against
  serialized JSON
- Performance suffers, forcing tradeoffs about what to trace and what to skip

OTEL is plumbing, not semantics. Even when you have rich tracing data, the
transport layer degrades it to unqueryable strings. Solutions:

- **BAML's compiler-level approach**: the compiler knows the shape of data
  flowing through functions, so traces carry typed, queryable data — not
  JSON-serialized blobs. This is the code-time tracing layer made concrete.
- **A typed layer on top of OTEL**: wrap span attributes in a schema-aware
  layer that preserves types for querying, even if the wire format degrades
  them.

The broader lesson: tracing infrastructure needs richer type systems than OTEL
currently provides. Use OTEL for the plumbing, but don't assume it's
sufficient for agent-specific queryability.

## The Tracing Spectrum: Three Layers, One Loop

Post-execution tracing (spans, flame graphs, waterfalls) is only one-third of
the picture. In a world where agents write most of the code and humans don't
read every line, you need tracing at three layers:

### Design-Time Tracing

Before code is written, you need to understand the **shape** of the system:
type signatures, function call graphs, sequence diagrams, architecture
overviews. This is tracing in the sense of "tracing the outline" — sketching
the structure before filling it in.

Mermaid diagrams, sequence diagrams, and architecture docs serve this purpose.
The workflow: "Show me the call stack" — understand the type signatures, the
objects being created, and how they fit together without reading every line.

This connects to the human's role: the human owns the design layer, and
design-time tracing is the tool that makes design authority practical. You
can't own the interfaces if you can't see them.

### Code-Time Tracing

Once code is written, you need to understand its structure without reading
every line. This is the "visualization" layer — dynamically rendering what the
code does, showing call stacks, function relationships, and data flow at a
glance.

The pattern: generate an HTML file per folder that explains changes at a high
level, allowing the developer to digest 2,000 lines of code in a minute. If
you want to drill in, you can — but first you get the overview.

This is the grey box in action: you don't read the internals, but you can see
the boundaries and relationships. BAML's compiler contributes here by knowing
which functions call LLMs and automatically capturing their I/O — the tracing
is embedded in the code structure, not bolted on after.

### Post-Execution Tracing

The traditional observability layer: flame graphs, waterfall diagrams, span
trees. After the code runs, you can see exactly what happened — which
functions were called, where time was spent, where errors occurred.

This is what the rest of this document covers: OpenTelemetry spans, trace IDs,
parent-child relationships. The difference from traditional distributed-systems
tracing is the object being traced: a decision chain (agent) rather than a
request path (service).

### The Closed Loop

The three layers form a feedback loop:

```
design → code → execution → agent feedback → improved design
```

The critical insight: post-execution tracing feeds back into design. When an
agent runs and produces unexpected behavior, you can ask: "What's missing in
the design that made the actual trace differ from the call site you drew me?"
The agent can then refine the design — not just fix the code, but fix the
*understanding* that produced the code.

This extends the quality loop (`code → traces → evals → scorers → back to
code`) to include the design layer:

```
design → code → traces → evals → scorers → back to design
```

You're not just debugging code — you're debugging the design assumptions that
produced the code. Each iteration aligns what you expected with what actually
happened.

## Agents as Trace Consumers

A critical requirement: traces must be queryable by **agents**, not just
visualizable for humans. The next evolution of agent observability is not "can
a human see what the agent did?" but "can the agent see what it did?" The
agent becomes the primary consumer of its own traces, using them to close the
feedback loop between execution and design.

This requires type-safe, schema-aware queryability — the ability to write
queries like:

```
find everything where latency > 1s and the prompt contained "generate image"
```

with full type safety on the query. The BAML compiler knows the shape of data
flowing through functions, so queries against traces can reference function
names, parameter types, and return types. This turns traces from
human-readable artifacts into machine-queryable data — the agent can
introspect its own execution history.

This is the OTEL type-system limitation made actionable: OTEL alone can't
support this kind of querying because rich data is JSON-serialized into
strings. A typed layer (compiler-level or schema-aware wrapper) is required
for agents to consume their own traces.

## Span Design

### The Root Span

Every agent run starts with a root span representing the user's task:

```
Trace: abc123
└── Span: "agent.run" (root)
    ├── attributes:
    │   ├── task: "Extract action items from meeting notes"
    │   ├── agent.id: "action-item-extractor"
    │   ├── agent.version: "1.2.0"
    │   └── model: "claude-sonnet-4-20250514"
    └── status: ok
```

### Child Spans: Tool Calls

Every tool invocation is a child span:

```
Span: "agent.run"
└── Span: "tool.read_file"
    ├── attributes:
    │   ├── tool.path: "/data/meeting-notes.txt"
    │   └── tool.bytes_read: 4096
    ├── duration_ms: 23
    └── status: ok
```

### Child Spans: LLM Calls

Every model inference is a span with token accounting:

```
Span: "agent.run"
└── Span: "llm.generate"
    ├── attributes:
    │   ├── llm.model: "claude-sonnet-4-20250514"
    │   ├── llm.input_tokens: 4521
    │   ├── llm.output_tokens: 847
    │   ├── llm.tool_calls: 2
    │   └── llm.temperature: 0.0
    ├── duration_ms: 2340
    └── status: ok
```

### Nested Sub-Agent Delegation

Sub-agents create nested span trees:

```
Span: "agent.run" (root agent)
└── Span: "agent.delegate" (handoff to ledger agent)
    ├── Span: "tool.lookup_invoice"
    ├── Span: "tool.check_status"
    ├── Span: "tool.finalize_invoice"
    └── Span: "llm.generate" (ledger agent's decision)
        └── status: ok  ← but send_invoice was never called
```

The tree stops at `finalize_invoice`. A log feed would hide the missing
`send_invoice` call. The trace tree makes the omission structurally visible.

## Span Naming Convention

Name spans by **what happened**, not how it was implemented:

| Good (action-oriented) | Bad (implementation-oriented) |
|------------------------|-------------------------------|
| `tool.read_file` | `fs.readFileSync` |
| `agent.delegate` | `subprocess.spawn` |
| `llm.generate` | `anthropic.messages.create` |
| `eval.score_groundedness` | `openai.chat.completions.create` |

This keeps traces readable when you're investigating a failure — you want to
see **what** the agent did, not which SDK method it used.

## Instrumentation Patterns

### TypeScript (OpenTelemetry JS)

```typescript
import { trace, SpanStatusCode } from "@opentelemetry/api";

const tracer = trace.getTracer("my-agent");

async function runAgent(task: string): Promise<AgentResult> {
  return tracer.startActiveSpan("agent.run", async (span) => {
    span.setAttribute("agent.task", task);

    try {
      // ... agent loop ...
      span.setStatus({ code: SpanStatusCode.OK });
      return result;
    } catch (error) {
      span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
      span.recordException(error);
      throw error;
    } finally {
      span.end();
    }
  });
}

async function callTool(name: string, params: Record<string, unknown>) {
  return tracer.startActiveSpan(`tool.${name}`, async (span) => {
    span.setAttribute("tool.name", name);
    span.setAttribute("tool.params", JSON.stringify(params));

    try {
      const result = await executeTool(name, params);
      span.setStatus({ code: SpanStatusCode.OK });
      return result;
    } finally {
      span.end();
    }
  });
}
```

### Python (OpenTelemetry Python)

```python
from opentelemetry import trace

tracer = trace.get_tracer("my-agent")

async def run_agent(task: str) -> AgentResult:
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("agent.task", task)
        # ... agent loop ...
        return result

def call_tool(name: str, params: dict) -> ToolResult:
    with tracer.start_as_current_span(f"tool.{name}") as span:
        span.set_attribute("tool.name", name)
        span.set_attribute("tool.params", json.dumps(params))
        return execute_tool(name, params)
```

### Python (with decorator, for frameworks)

```python
from functools import wraps
from opentelemetry import trace

def traced(name: str):
    """Decorator that wraps a function in a span."""
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name) as span:
                return await fn(*args, **kwargs)
        return wrapper
    return decorator

@traced("tool.search_docs")
async def search_docs(query: str) -> list[Document]:
    ...
```

### Compiler-Level Auto-Instrumentation (BAML)

The fundamental flaw in most tracing systems: users have to opt in. If agents
are writing code, they won't consistently add tracing — you'll get partial
coverage with gaps that are invisible until you need them.

BAML takes a different approach: the compiler knows which functions call LLMs
and automatically captures their inputs and outputs. No manual `@trace`
decorators, no opt-in span creation. Security-sensitive data (environment
variables, HTTP headers) is redacted by default, and repeated values are
deduplicated.

This is the code-time tracing layer made concrete: the tracing is embedded in
the code structure, not bolted on after. The compiler's knowledge of the
code's shape becomes the tracing's knowledge of the execution's shape.

When to use this approach:
- You're starting a new project and can adopt a compiler-aware framework
- You want complete coverage without relying on developers (human or agent)
  to remember instrumentation
- You need type-safe querying of trace data (the compiler preserves types
  that OTEL's wire format would degrade)

## What to Record in Spans

### Always Include
- Tool name and parameters
- Token counts (input, output) for LLM calls
- Duration
- Status (ok/error)
- Error details when status is error

### Consider Including
- Tool output size (bytes, result count)
- Agent version
- Model identifier
- User/session ID for correlation
- Eval scores when available

### Don't Include
- Full tool output bodies (reference by ID instead)
- Sensitive data (PII, secrets, API keys)
- Entire conversation history (link to session storage)

## Event-Based Instrumentation

For agents with tool call events, instrument at the event boundary:

```typescript
agent.on("tool:start", ({ name, params, runId }) => {
  const span = tracer.startSpan(`tool.${name}`, {
    attributes: {
      "tool.name": name,
      "tool.params": JSON.stringify(params),
      "run.id": runId,
    },
  });
  activeSpans.set(runId, span);
});

agent.on("tool:end", ({ runId, result, error }) => {
  const span = activeSpans.get(runId);
  if (!span) return;

  if (error) {
    span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
    span.recordException(error);
  } else {
    span.setStatus({ code: SpanStatusCode.OK });
  }
  span.end();
  activeSpans.delete(runId);
});
```

## Exporters

Choose based on your observability stack:

| Exporter | Use When |
|----------|----------|
| OTLP (gRPC/HTTP) | You have an OTEL collector (Datadog, Honeycomb, self-hosted) |
| Console | Local development and debugging |
| Arize Phoenix | You want agent-specific trace visualization |
| Langfuse | You need eval scoring alongside traces |
| Braintrust | You need experiment tracking with evals |
| Mastra (built-in) | You're using Mastra as your agent framework |

## Performance Considerations

- Batch span exports (don't export per-span)
- Sample aggressively in production (1-10% for high-throughput agents)
- Use span processors that export asynchronously
- Keep span attributes small (don't embed full tool outputs)

## Local Trace Inspection

For development, use console export or visualize locally:

```typescript
import { SimpleSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { ConsoleSpanExporter } from "@opentelemetry/sdk-trace-base";

const provider = new BasicTracerProvider();
provider.addSpanProcessor(
  new SimpleSpanProcessor(new ConsoleSpanExporter())
);
provider.register();
```

Or use Arize Phoenix's local mode for span tree visualization during
development: `phoenix serve` loads traces into an interactive tree view.

## Concrete Architecture: Session → Turn → Model Request

A concrete data model for agent observability (Matt Pocock's Slop Watch
ideation). Observability data is not flat — it has three nested levels:

1. **Session**: One logical run of a coding agent, attached to one developer,
   one working directory, one agent version. The top-level unit of
   observability.
2. **Turn**: One user message plus the full assistant response. Each turn may
   trigger multiple model requests (e.g., an agent that makes tool calls
   between reasoning steps).
3. **Model Request**: One HTTP call to the model provider. The atomic cost
   unit.

Sessions contain a **directed acyclic graph (DAG)** of turns, not a linear
list. This accounts for branching and rewinding — when an agent rewinds to
try a different approach, the abandoned branch is still part of the session's
DAG, with real costs and artifacts.

### Listener/Sidecar Pattern

The capture component is a **per-session listener** (subprocess spawned by a
hook), not a machine-wide daemon. Each listener:
- Captures events via the agent's hook payloads (where available)
- Tails the agent's JSONL output on disk
- Normalizes into the internal schema
- Posts events to the server
- Is cheap and independent — multiple can run concurrently

### Per-Agent Adapters

Different coding agents expose observability data differently. No single
OpenTelemetry-based ingestion path exists across agents. Per-agent adapters
are unavoidable:

| Agent | Hook surface | JSONL on disk |
|-------|-------------|---------------|
| Claude Code | Hooks exist but payloads don't include message content | Yes, must also read JSONL |
| Pi | Hook surface via extension/skill API | Yes |
| Codex | Hooks flag-gated, Windows excluded | Yes |
| Copilot CLI | Thin hooks | Yes |
| Open Code | Plugin system | — |

### Development Identity

Observability events must be attributable to a person. Git config is
trivially spoofable and insufficient. Use admin-minted tokens: the org admin
creates a user record and provides a one-time token; the developer
authenticates with it.

### Team UX

For a team/org context (not solo developers), the primary consumer is the DRI
(Directly Responsible Individual) who reviews team sessions. Features:
- Session listing per developer
- Live spectate (polling-based, ~5s refresh)
- Session cost breakdown by turn and model request
- Child session tracking for sub-agent delegations
- Admin plane for user management
