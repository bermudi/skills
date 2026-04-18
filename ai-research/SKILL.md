---
name: ai-research
description: "Perform AI-powered research on any topic using Poe models with built-in web search via mcporter. Use this skill when you need a comprehensive, synthesized answer to a research question — not just search results, but actual analysis and reasoning. Triggers on: \"research this topic\", \"deep dive into\", \"comprehensive analysis of\", \"investigate\", \"what's the state of\", \"compare X and Y\", \"give me a thorough overview\", \"I need to understand\", \"write a research brief on\". This is different from web search (tavily_search) — it uses AI models that can reason, synthesize multiple sources, and provide structured analysis."
---

# AI-Powered Research with Poe

The poe-research MCP server provides AI-powered research through Poe models with built-in web search. Unlike regular search which returns links and snippets, this returns synthesized, reasoned answers.

Access it through mcporter: `mcporter call poe-research.<tool> key=value`.

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| `research` | Quick research with a single query | Focused questions, quick answers |
| `deep_research` | Multi-step deep research | Complex topics, thorough analysis |

## Calling Convention

```bash
mcporter call poe-research.<tool_name> key=value
```

Output is a comprehensive text response with sources.

---

## research — Quick AI Research

Research a topic using Poe with built-in web search. Returns a comprehensive, sourced answer in a single pass.

### Basic Usage
```bash
mcporter call poe-research.research query="your research question"
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `query` | ✅ | — | The research question or topic |
| `model` | ❌ | GPT-5.4 | Poe model to use (e.g. `GPT-5.4`, `Claude-Sonnet-4.6`) |
| `reasoning` | ❌ | — | Reasoning effort: `low`, `medium`, `high` (only for reasoning-capable models) |

### Examples

**Quick factual research:**
```bash
mcporter call poe-research.research query="What are the key differences between SQLite and DuckDB for analytical workloads?"
```

**With reasoning effort:**
```bash
mcporter call poe-research.research query="Analyze the tradeoffs between microservices and monolith architecture for a 10-person startup" reasoning=high
```

**Using a specific model:**
```bash
mcporter call poe-research.research query="What's new in Python 3.14?" model="Claude-Sonnet-4.6"
```

---

## deep_research — Multi-Step Deep Research

Perform multi-step deep research on a topic. Runs an initial search, then follows up to synthesize and fill gaps. Slower but much more thorough.

### Basic Usage
```bash
mcporter call poe-research.deep_research topic="your topic"
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `topic` | ✅ | — | The topic to deeply research |
| `model` | ❌ | GPT-5.4 | Poe model to use |

### Examples

**Comprehensive topic analysis:**
```bash
mcporter call poe-research.deep_research topic="State of WebAssembly in 2025: adoption trends, performance benchmarks, and practical use cases beyond the browser"
```

**Technical comparison:**
```bash
mcporter call poe-research.deep_research topic="Comparing Bun, Deno, and Node.js runtime performance, ecosystem maturity, and production readiness in 2025"
```

**Investigation:**
```bash
mcporter call poe-research.deep_research topic="How are major tech companies implementing RAG (Retrieval-Augmented Generation) in production? Architecture patterns, challenges, and lessons learned."
```

---

## Decision Guide: research vs deep_research

```
Need AI-powered research?
├── Focused question, quick answer → research
├── Broad topic, need depth → deep_research
├── Simple factual lookup → research
└── Complex multi-faceted topic → deep_research
```

- `research` is faster (single pass). Good for focused questions where you need a synthesized answer.
- `deep_research` is slower (multi-pass). It follows up on gaps from the initial research. Good for complex topics where coverage matters more than speed.

## When to Use AI Research vs Other Tools

| Need | Tool | Why |
|------|------|-----|
| Synthesized analysis of a topic | **ai-research** (this) | AI reasoning + web search combined |
| Quick web search for facts | **tavily_search** | Faster, raw search results |
| Deep multi-source research with full control | **tavily_research** | Structured research pipeline |
| Code examples from real repos | **code-search** | Actual code, not analysis |
| Library documentation | **context7** or **tavily_skill** | Reference docs, not research |

AI research is the best choice when you need the AI to **think** about the answer — compare options, analyze tradeoffs, synthesize from multiple sources — not just retrieve information.
