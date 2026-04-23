# AI-Powered Research with Poe

The poe-research MCP server provides AI-powered research through Poe models with
built-in web search. Unlike regular search which returns links and snippets, this
returns synthesized, reasoned answers.

Access it through mcporter: `mcporter call poe-research.<tool> key=value`. Use
`--timeout <ms>` for long-running calls (e.g. `--timeout 180000` for 180s).

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

**⚠️ Timeout warning:** `deep_research` often takes 90–150s+. mcporter's default
timeout is 60s, so you **must** override it with `--timeout <milliseconds>`.

```bash
mcporter call poe-research.deep_research topic="your topic" --timeout 180000
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `topic` | ✅ | — | The topic to deeply research |
| `model` | ❌ | GPT-5.4 | Poe model to use |

### Examples

```bash
mcporter call poe-research.deep_research topic="State of WebAssembly in 2025: adoption trends, performance benchmarks, and practical use cases beyond the browser" --timeout 180000

mcporter call poe-research.deep_research topic="Comparing Bun, Deno, and Node.js runtime performance, ecosystem maturity, and production readiness in 2025" --timeout 180000
```

## Decision Guide: research vs deep_research

```
Need AI-powered research?
├── Focused question, quick answer → research
├── Broad topic, need depth → deep_research
├── Simple factual lookup → research
└── Complex multi-faceted topic → deep_research
```

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

Both do AI-powered multi-source research. The difference is the engine:

| | `poe-research.research` | `tavily_research` |
|---|---|---|
| **Engine** | Poe models with built-in web search | Tavily's own research pipeline |
| **Speed** | Fast (single-pass) or slow (deep_research) | Medium |
| **Configurability** | Choose model + reasoning effort | Choose depth model (mini/pro/auto) |
| **Best for** | Quick synthesized answers with strong reasoning | Structured research where Tavily's pipeline control matters |

**Rule of thumb**: Use `poe-research.research` for quick AI-synthesized answers.
Use `tavily_research` for structured multi-source pipelines. Use
`poe-research.deep_research` for the most thorough analysis of a complex topic.
