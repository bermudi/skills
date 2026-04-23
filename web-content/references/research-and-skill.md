# tavily_research — Deep Research

Comprehensive multi-source research on a topic. Rate limit: 20 requests/minute.

**⚠️ Timeout note:** `model=pro` runs many subtopic queries and can exceed mcporter's 60s default. Use `--timeout 120000` or higher for broad topics.

## Basic Usage

```bash
mcporter call tavily.tavily_research input="Comprehensive description of what you want to research"
```

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `input` | (required) | Detailed description of the research task |
| `model` | `auto` | `mini` (narrow, few subtopics), `pro` (broad, many subtopics), `auto` |

## Examples

**Quick focused research:**
```bash
mcporter call tavily.tavily_research input="What are the main differences between Python's asyncio and trio libraries for async programming?" model=mini
```

**Broad deep research:**
```bash
mcporter call tavily.tavily_research input="State of the art in LLM reasoning: chain-of-thought, tree-of-thought, and other approaches. Include recent papers from 2025, key benchmarks, and practical recommendations." model=pro --timeout 120000
```

## When to Use Research vs Search

- Use **search** when you need quick answers, facts, or a few sources.
- Use **research** when you need a comprehensive, synthesized answer from multiple sources with analysis.
- Research is slower but much more thorough — it runs multiple searches and synthesizes the results.

---

# tavily_skill — AI-Synthesized Library Documentation

Search documentation for any library, API, or tool. Unlike Context7 (which returns raw doc chunks), `tavily_skill` uses AI to synthesize a structured response — it searches a doc index, then generates a coherent answer with setup guides, code examples, gotchas, and version notes. The output follows a consistent template (`What it is`, `When to use`, `Correct setup`, `Critical gotchas`) that is clearly AI-generated, not raw scraped content.

## Basic Usage

```bash
mcporter call tavily.tavily_skill query="how to use middleware in Express.js" library="express"
```

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `query` | (required) | Natural language query about a library |
| `library` | "" | Library/package name (e.g. `nextjs`, `celery`, `httpx`) |
| `language` | "" | Programming language to boost results |
| `task` | null | `integrate`, `configure`, `debug`, `migrate`, `understand` |
| `context` | "" | Brief description of your project/stack |
| `max_tokens` | 8000 | Maximum tokens in response |

## Examples

**Look up how to do something specific:**
```bash
mcporter call tavily.tavily_skill query="how to set up periodic tasks with celery beat" library="celery" language="python"
```

**Debug a library issue:**
```bash
mcporter call tavily.tavily_skill query="hydration mismatch error in server components" library="nextjs" task=debug language="typescript"
```

**With project context:**
```bash
mcporter call tavily.tavily_skill query="setting up WebSocket connections" library="fastapi" language="python" context="FastAPI app with Redis backend and JWT auth"
```

## tavily_skill vs context7

| | `tavily_skill` | `context7` |
|---|---|---|
| **AI synthesis** | ✅ Yes — generates structured response | ❌ No — returns raw doc chunks |
| **Steps** | One call | Two calls (resolve ID, then query) |
| **Version targeting** | No | Yes — can pin to specific version |
| **Best for** | Quick "how do I..." lookups | When you need exact doc text or a specific version |

Use `tavily_skill` when you want a quick, synthesized answer. Use `context7` when you need the raw documentation text (e.g., to verify exact API signatures) or need a specific library version.
