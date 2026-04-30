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
