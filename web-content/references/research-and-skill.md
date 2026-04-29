# tavily_research — Deep Research

**Plan-limited and unavailable.** Use `poe-research.research` for quick answers
or `poe-research.deep_research` for thorough multi-pass research.

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
