# AMP Subagents

> Sources: https://ampcode.com/manual , https://ampcode.com/manual/plugin-api , https://ampcode.com/news/custom-agents

AMP is the odd one out: custom subagents are defined **programmatically in a TypeScript plugin**, not via a markdown manifest. Subagents are created with `amp.createAgent(...)` and exposed to the main agent by registering a tool that calls `agent.run(...)`.

Amp also spawns subagents **automatically** for suitable tasks (mostly in `smart` mode). You can encourage it by mentioning subagents or suggesting parallel work ("use 3 subagents to convert these CSS files to Tailwind").

## How AMP subagents behave

- Each subagent has its own context window and tool access (file editing, terminal commands).
- Subagents work in **isolation**: they can't communicate with each other, you can't guide them mid-task, they start fresh without your conversation's accumulated context, and the main agent only receives their final summary.
- Most useful for: multi-step tasks broken into independent parts, operations with extensive output not needed later, parallel work across code areas, keeping the main thread's context clean.

## Defining a custom subagent (plugin)

Create an Amp plugin. Use `amp.experimental.createAgent` (experimental API) and register a tool that invokes it. The `parentThreadID` option keeps the subagent run connected to the thread that invoked the tool.

```typescript
import type { PluginAPI } from '@ampcode/plugin'

export default function (amp: PluginAPI) {
  if (!amp.experimental) {
    throw new Error('This plugin requires the experimental plugin API.')
  }

  const reviewer = amp.experimental.createAgent({
    name: 'focused-reviewer',
    model: 'openai/gpt-5.5',
    instructions: [
      'You are a focused code-review subagent.',
      'Inspect only the files and concerns named by the caller.',
      'Return concise findings with severity, evidence, and suggested fixes.',
    ].join(' '),
    tools: 'all',
    reasoningEffort: 'medium',
  })

  amp.registerTool({
    name: 'focused_review_subagent',
    description: 'Run a focused code-review subagent for a specific review request.',
    inputSchema: {
      type: 'object',
      properties: {
        request: {
          type: 'string',
          description: 'The files, diff, or concern the subagent should review.',
        },
      },
      required: ['request'],
    },
    async execute(input, ctx) {
      const request = typeof input.request === 'string' ? input.request : ''
      if (!request.trim()) {
        return 'Missing review request.'
      }

      const result = await reviewer.run(request, {
        parentThreadID: ctx.thread.id,
        timeoutMs: 10 * 60 * 1000,
      })

      return result.text
    },
  })
}
```

### `createAgent` config fields

| Field | Description |
|---|---|
| `name` | Agent name |
| `model` | Model id, e.g. `openai/gpt-5.5`. Run `amp plugins show-agent-options` (or `--json`) to discover public model IDs and built-in tool names. |
| `instructions` | System prompt (string) |
| `tools` | Tool access, e.g. `'all'` or a restricted set |
| `reasoningEffort` | Reasoning level, e.g. `'medium'` |
| `display` | `{ label, color }` for the orb color and label |

### Registering as a selectable main-thread mode (optional)

You can also expose the same agent as a top-level mode the user picks directly:

```typescript
amp.registerAgentMode({
  key: 'focused-reviewer',
  description: 'Code Review Expert',
  agent: reviewer.definition,
})
```

## Built-in agent modes

Amp has three built-in modes you can also get handles to via `amp.getBuiltinAgent(mode)`:

| Mode | Description |
|---|---|
| `smart` | State-of-the-art models, unconstrained (default) |
| `deep` | Deep reasoning with extended thinking, GPT-5.5 |
| `rush` | Fast, low-token GPT-5.5, no reasoning — small well-defined tasks |

## Other built-in subagents (automatic)

- **Oracle** — a "second opinion" model (Claude Fable 5, reasoning high) the main agent consults for complex reasoning/review. Invoked via the `oracle` tool; the main agent decides when. Higher cost, slower.
- **Librarian** — searches remote codebases.
- **Code Review** — Amp spawns a separate subagent per check during code review.

## Notes

- The plugin API is **experimental** and may change. Guard with `if (!amp.experimental)`.
- Discover valid model IDs and tool names with `amp plugins show-agent-options`.
- Custom agents can be used as the main Amp agent, as subagents, in a tool pipeline invoked with `amp -x`, or spawned in parallel (e.g. 25 worker agents).
