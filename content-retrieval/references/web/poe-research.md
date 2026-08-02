# AI-Powered Research with Poe

The poe-research MCP server provides AI-powered research through Poe models with
built-in web search. Unlike regular search which returns links and snippets, this
returns synthesized, reasoned answers.

Access it through mcporter: `mcporter call poe-research.<tool> key=value`.

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| `research` | Quick research with a single query | Focused questions, quick answers |
| `deep_research` | Multi-step deep research | Complex topics, thorough analysis |

## research — Quick AI Research

Research a topic using Poe with built-in web search. Returns a comprehensive,
sourced answer in a single pass.

```bash
mcporter call poe-research.research query="your research question"
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `query` | ✅ | — | The research question or topic |
| `model` | ❌ | GPT-5.4 | Poe model to use |
| `reasoning` | ❌ | — | Reasoning effort: `low`, `medium`, `high` |

### Examples

```bash
mcporter call poe-research.research query="What are the key differences between SQLite and DuckDB for analytical workloads?"

mcporter call poe-research.research query="Analyze the tradeoffs between microservices and monolith architecture" reasoning=high

mcporter call poe-research.research query="What's new in Python 3.14?" model="Claude-Sonnet-4.6"
```

## deep_research — Multi-Step Deep Research

Perform multi-step deep research on a topic. Runs an initial search, then
follows up to synthesize and fill gaps. Slower but much more thorough.

**⚠️ Timeout warning:** `deep_research` often takes 90–300s+. There are **two
timeouts** you must coordinate — mcporter's inner timeout and pi's outer bash
timeout. See [Timeout Coordination](#timeout-coordination) below.

```bash
# When calling from pi's bash tool, set BOTH timeouts:
#   mcporter --timeout 600000 (milliseconds)
#   pi bash timeout: 660      (seconds, must be > mcporter's timeout in seconds)
mcporter call poe-research.deep_research topic="your topic" --timeout 600000
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `topic` | ✅ | — | The topic to deeply research |
| `model` | ❌ | GPT-5.4 | Poe model to use |

### Examples

```bash
mcporter call poe-research.deep_research topic="State of WebAssembly in 2025: adoption trends, performance benchmarks, and practical use cases beyond the browser" --timeout 600000

mcporter call poe-research.deep_research topic="Comparing Bun, Deno, and Node.js runtime performance, ecosystem maturity, and production readiness in 2025" --timeout 600000
```

## Decision Guide: research vs deep_research

```
Need AI-powered research?
├── Focused question, quick answer → research
├── Broad topic, need depth → deep_research
├── Simple factual lookup → research
└── Complex multi-faceted topic → deep_research
```

## Timeout Coordination

When calling mcporter from pi's `bash` tool, two independent timeouts apply.
You **must** coordinate both or the call will be killed prematurely.

| Timeout | Where | Unit | Who kills what |
|---------|-------|------|----------------|
| `--timeout <ms>` | mcporter CLI flag | **milliseconds** | Kills the tool call from inside mcporter (clean error message) |
| `timeout` param | pi's `bash` tool | **seconds** | Kills the entire mcporter process from outside (SIGKILL, messy) |

**The rule: pi's bash timeout (seconds) must be strictly greater than mcporter's
timeout (converted to seconds).** This lets mcporter handle timeout gracefully
with a clean error instead of being SIGKILL'd mid-stream.

### Recommended Values

| Tool | mcporter `--timeout` | pi bash `timeout` | Notes |
|------|---------------------|-------------------|-------|
| `research` (default) | omit (60s default is fine) | omit | Fast, single-pass |
| `research` with `reasoning=high` | `120000` (2 min) | `150` (2.5 min) | Can run longer |
| `deep_research` | `600000` (10 min) | `660` (11 min) | Often 90–300s+ |

### Example: deep_research from pi

When pi's agent calls deep_research, it should invoke the `bash` tool like:

```
bash(command="mcporter call poe-research.deep_research topic='your topic' --timeout 600000", timeout=660)
```

**Common mistake:** treating pi's bash `timeout` as milliseconds. It's **seconds**.
`timeout: 600000` means 600,000 seconds (7 days), not 600 seconds.

## Recommended Models

| Model | Role | Notes |
|-------|------|-------|
| **GPT-5.4** | Default (best overall) | Strong reasoning + web search |
| **GPT-5.4-Mini** | Cheaper alternative | Good balance of cost and quality |
| **GPT-5.4-Nano** | Fast exploration | Cheapest, good for quick probes |
| **Claude-Sonnet-4.6** | Second opinion | Different reasoning style, good for cross-checking |
| **Claude-Haiku-4.5** | Cheaper Claude option | Fast, still solid with web search |
| **Gemini-3.1-Pro** | Alternative perspective | Good source citations |
| **Gemini-3-Flash** | Fast/cheap Gemini | Good source citations, light option |

## Reasoning Support

The `reasoning` parameter maps to each model family's native mechanism. Not all
models support it — if the underlying API rejects it, you'll get an error back.
Works reliably on: GPT-5.4, GPT-5.4-Mini, Claude-Sonnet-4.6, Claude-Haiku-4.5.

## poe-research vs tavily_research

`poe-research` covers all AI research needs. `tavily_research` is currently
plan-limited and unavailable.

**Rule of thumb**: Use `poe-research.research` for quick AI-synthesized answers.
Use `poe-research.deep_research` for the most thorough analysis of a complex topic.
