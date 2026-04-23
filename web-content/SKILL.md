---
name: web-content
description: >
  Fetch, extract, search, crawl, and research online content using the best
  available tool for each job. Covers raw file downloads (curl),
  HTML-to-markdown extraction (Jina AI Reader), web search (Tavily), site
  crawling and mapping (Tavily), deep multi-source research (Tavily, Poe),
  library documentation lookup (Tavily, Context7), GitHub repo understanding
  (DeepWiki), and code search across public repositories (grep.app). Triggers
  on: "search the web", "look this up", "what's the latest on", "scrape this
  page", "extract content from", "crawl this site", "map this website",
  "research this topic", "deep dive into", "find information about", "what does
  the web say about", "fetch this URL", "get the content of", "pull down this
  page", "how do people use", "show me examples of", "find code that uses",
  "how does X repo work", "explain this GitHub repo", "what's the API for",
  "how to use X library".
---

# Web Content

Get information from the internet — the right way, with the right tool.

This skill covers everything from fetching a single raw file to synthesizing
deep multi-source research, finding production code examples, understanding
GitHub repos, and looking up library docs. The key is matching the job to the
tool instead of routing everything through one API.

## Decision Guide

```
What do you need?
│
├── Content from a known URL
│   ├── Raw/plain-text file? → curl -sL <url>                          (Tier 1)
│   ├── HTML page? → try in order:
│   │   ├── curl -H "Accept: text/markdown" <url>                     (Tier 2)
│   │   ├── r.jina.ai/http://<url>                                    (Tier 3)
│   │   └── tavily_extract                                            (Tier 4)
│   └── Still failed? → see references/extraction-strategies.md
│
├── Information, but no URL yet
│   ├── Quick fact or current event → tavily_search
│   ├── Synthesized analysis / research on a topic
│   │   ├── Quick answer → poe-research.research
│   │   ├── Thorough multi-pass → poe-research.deep_research
│   │   └── Structured pipeline → tavily_research
│   ├── Library docs, synthesized answer → tavily_skill
│   ├── Library docs, specific version or raw text → context7
│   ├── Understand a GitHub repo's architecture → deepwiki
│   └── Real code examples in production repos → grep.app
│
├── Content from a whole site
│   ├── See what URLs exist → tavily_map
│   └── Get actual page content → tavily_crawl
│
└── See references/ for detailed param guides on each tool.
```

## Quick Reference

| Tool | Server | Returns | Best For | Reference |
|------|--------|---------|----------|-----------|
| `curl -sL` | — | Raw bytes | Static files, raw GitHub content | Inline below |
| `curl -H "Accept: text/markdown"` | — | Markdown | Docs sites that negotiate | Inline below |
| `r.jina.ai/http://...` | — | Clean markdown | HTML extraction, bypasses challenges | Inline below |
| `tavily_extract` | `tavily` | Extracted content | JS SPAs, auth walls, batch extraction | references/extract.md |
| `tavily_search` | `tavily` | Snippets + URLs | Quick facts, current events | references/search.md |
| `tavily_research` | `tavily` | Synthesized report | Structured multi-source research | references/research-and-skill.md |
| `tavily_skill` | `tavily` | AI-synthesized docs | Quick "how do I..." lookups | references/research-and-skill.md |
| `poe-research.research` | `poe-research` | Synthesized answer | Focused AI research | references/poe-research.md |
| `poe-research.deep_research` | `poe-research` | Thorough report | Complex multi-pass analysis | references/poe-research.md |
| `grep.searchGitHub` | `grep` | Code snippets | Literal code patterns in the wild | references/code-search.md |
| `context7` | `context7` | Raw doc chunks | Exact API text, versioned docs | references/context7-docs.md |
| `deepwiki` | `deepwiki` | Repo docs + Q&A | Repo architecture, design decisions | references/deepwiki.md |
| `tavily_map` | `tavily` | URL list | Discover site structure | references/crawl-and-map.md |
| `tavily_crawl` | `tavily` | Multi-page content | Crawl docs sites | references/crawl-and-map.md |

## Quick Calls

### AI Research (Poe)

```bash
# Quick synthesized answer
mcporter call poe-research.research query="your question"

# Thorough multi-step (override timeout!)
mcporter call poe-research.deep_research topic="your topic" --timeout 180000
```

See `references/poe-research.md` for model selection, reasoning params, and the
full research-vs-research comparison.

### Code Search (grep.app)

Searches **literal code patterns**, not natural language. Good: `useState(`.
Bad: `react tutorial`.

```bash
mcporter call grep.searchGitHub query="createServer(" language='["TypeScript"]'
```

See `references/code-search.md` for regex patterns, repo/org filters, and query
crafting.

### Library Docs (Context7)

Two-step process: resolve library ID, then query.

```bash
mcporter call context7.resolve-library-id query="middleware setup" libraryName="Express.js"
mcporter call context7.query-docs libraryId="/expressjs/express" query="middleware setup"
```

See `references/context7-docs.md` for writing good queries, version-specific
docs, and rate-limiting guidance.

### Repo Understanding (DeepWiki)

```bash
mcporter call deepwiki.ask_question repoName="vercel/next.js" question="How does the App Router work?"
```

See `references/deepwiki.md` for wiki structure vs contents, multi-repo queries,
and the "not indexed" fallback pattern.

## Extraction Hierarchy — Content from a Known URL

When you have a URL and need its content, escalate through these tiers. Always
start at the lowest tier that could work — each step up costs more (latency,
API calls, or both).

### Tier 1: `curl -sL` — Raw Files

If the URL serves content directly (no HTML wrapper), just curl it. Exact bytes,
zero cost, zero transformation.

```bash
curl -sL https://raw.githubusercontent.com/user/repo/main/README.md
```

Works for: raw GitHub content, `.txt`, `.md`, `.json`, `.yaml`, source code
files, pastebin raw, any static file. Avoid for html content.

Quick test: `curl -sL -o /dev/null -w '%{content_type}' <url>` — if it's
`text/plain`, `application/json`, etc., you're done.

### Tier 2: `curl -H "Accept: text/markdown"` — Markdown Negotiation

Many docs sites (especially Cloudflare-proxied ones) can return markdown
directly if you ask for it. No external service, no API, just a different
`Accept` header.

```bash
curl -sL -H "Accept: text/markdown" "https://example.com/docs/page"
```

If the response is clean markdown, you're done. If it returns HTML or a
challenge page, move to Tier 3.

**Why try this before Jina?** No external dependency, no rate limits, instant.

### Tier 3: Jina AI Reader — HTML to Markdown

Free, no auth needed. Extracts clean markdown from HTML, often bypassing bot
challenges and cookie walls.

```bash
curl -sL "https://r.jina.ai/http://example.com/some-article/"
```

If the output is garbage or a challenge page, move to Tier 4.

### Tier 4: `tavily_extract` — The Heavy Lifters

When the free options above fail or don't apply — JS-rendered SPAs, auth-walled
pages, batch extraction of multiple URLs, or complex layouts with tables/embedded
content.

```bash
mcporter call tavily.tavily_extract urls='["https://example.com/page"]'
```

For JS-heavy or auth-walled sites, add `extract_depth=advanced`. For batch
extraction, pass multiple URLs. For relevance filtering, add a `query`
parameter.

→ Full details in [Extraction Strategies](references/extraction-strategies.md)
and [Extract](references/extract.md).

## Tavily Tools

AI-native search API, accessed via mcporter: `mcporter call tavily.<tool> key=value`.

| Tool | Job | When to use | Reference |
|------|-----|-------------|-----------|
| `tavily_search` | Web search | No URL known, need current info | references/search.md |
| `tavily_crawl` | Multi-page extraction | Crawl a docs site or multi-page resource | references/crawl-and-map.md |
| `tavily_map` | Discover URLs | See what pages exist on a site | references/crawl-and-map.md |
| `tavily_research` | Deep multi-source research | Synthesize a topic across many sources | references/research-and-skill.md |
| `tavily_skill` | Library docs lookup | AI-synthesized answer about a library/API | references/research-and-skill.md |

## When to Use What

| Need | Tool | Why |
|------|------|-----|
| Synthesized analysis of a topic | **poe-research** | AI reasons + web search combined |
| Quick web search for facts | **tavily_search** | Fast, raw search results |
| Deep structured multi-source research | **tavily_research** | Tavily pipeline control |
| Real code examples from repos | **grep.app** | Actual production code |
| Quick "how do I use X" | **tavily_skill** | One call, synthesized answer |
| Exact doc text, specific version | **context7** | Raw chunks, version pinning |
| Repo architecture & design | **deepwiki** | Repo-level understanding |
| Content from a specific URL | **curl / jina / tavily_extract** | Escalating tiers by cost |

## Gotchas

- **`deep_research` timeouts:** Always override with `--timeout 180000`. It can
take 90–150s+.
- **context7 rate limit:** Don't call resolve + query more than 3 times per
question. Supplement with other tools if needed.
- **grep.app is literal:** If you wouldn't `grep` for it in your own codebase,
don't search for it here. Use `tavily_search` for conceptual queries.
- **DeepWiki `ask_question` flakiness:** If it returns "repo not indexed", fall
back to `read_wiki_contents` and reason over the text yourself.

## References

- [Extraction Strategies](references/extraction-strategies.md) — detailed 4-tier
  breakdown with validation and fallback logic
- [Search](references/search.md) — `tavily_search` parameters, depth options,
  examples
- [Extract](references/extract.md) — `tavily_extract` parameters, batch
  extraction, depth guidance
- [Crawl & Map](references/crawl-and-map.md) — `tavily_crawl` and `tavily_map`
  parameters and tuning
- [Research & Skill](references/research-and-skill.md) — `tavily_research` and
  `tavily_skill` parameters, when to use each
- [Poe Research](references/poe-research.md) — `poe-research.research` and
  `poe-research.deep_research` models, reasoning, timeouts
- [Code Search](references/code-search.md) — `grep.searchGitHub` patterns,
  filters, regex tips
- [Context7 Docs](references/context7-docs.md) — two-step workflow, query tips,
  version pinning
- [DeepWiki](references/deepwiki.md) — repo docs, Q&A, fallback patterns
