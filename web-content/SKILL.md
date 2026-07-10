---
name: web-content
description: >
  Fetch, extract, search, crawl, and research online content using the best
  available tool for each job. Covers: web search, URL extraction/crawling,
  AI research synthesis (poe-research), library docs lookup (context7 /
  tavily_skill), repo architecture understanding (deepwiki), and real
  production-code search (grep.app). Triggers on: "search the web", "look this
  up", "what's the latest on", "scrape ...", "extract ...", "crawl ...",
  "find examples of X in real code", "explain this GitHub repo", etc. If you're
  about to use curl, read this first.
---

# Web Content

Get information from the internet — the right way, with the right tool.

This skill covers everything from fetching a single raw file to synthesizing
deep multi-source research, finding production code examples, understanding
GitHub repos, and looking up library docs.

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
│   │   └── Thorough multi-pass → poe-research.deep_research
│   ├── Library docs, synthesized answer → tavily_skill
│   ├── Library docs, specific version or raw text → context7
│   ├── Understand a GitHub repo's architecture → deepwiki
│   └── Real code examples in production repos → grep.app
│
├── Content from a whole site
│   ├── See what URLs exist → tavily_map
│   └── Get actual page content → tavily_crawl
│
└── See the Quick Reference table for mcporter call shapes and reference guides.
```

## Quick Reference

| Tool | Server | Returns | Best For | Reference |
|------|--------|---------|----------|-----------|
| `curl -sL` | — | Raw bytes | Static files, raw GitHub content | Inline below |
| `curl -H "Accept: text/markdown"` | — | Markdown | Docs sites that negotiate | Inline below |
| `r.jina.ai/http://...` | — | Clean markdown | HTML extraction, bypasses challenges | Inline below |
| `tavily_extract` | `tavily` | Extracted content | JS SPAs, auth walls, batch extraction | references/extract.md |
| `tavily_search` | `tavily` | Snippets + URLs | Quick facts, current events | references/search.md |
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

# Thorough multi-step (set BOTH timeouts when calling from pi!)
# mcporter --timeout 600000 (milliseconds)
# pi bash timeout: 660      (seconds, must be > 600)
mcporter call poe-research.deep_research topic="your topic" --timeout 600000
```

See `references/poe-research.md` for model selection, reasoning params, timeout
coordination details, and the full research-vs-deep_research comparison.

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

## URL Extraction — Escalate by Cost

When you have a URL, escalate through four tiers. Always start at the lowest
tier that could work — each step up costs more (latency, API calls, or both).
For how to classify a URL, the failure signal at each tier, and when to escalate
vs. stop, read [Extraction Strategies](references/extraction-strategies.md).
Quick form:

1. **Tier 1 — `curl -sL`**: raw files, no HTML wrapper. Zero cost.
   ```bash
   curl -sL https://raw.githubusercontent.com/user/repo/main/README.md
   ```
   Quick test: `curl -sL -o /dev/null -w '%{content_type}' <url>` — if it's
   `text/plain` or `application/json`, you're done.

2. **Tier 2 — `curl -H "Accept: text/markdown"`**: docs sites that negotiate.
   No external dependency, no rate limits, instant.
   ```bash
   curl -sL -H "Accept: text/markdown" "https://example.com/docs/page"
   ```
   If it returns HTML or a challenge page, move on.

3. **Tier 3 — Jina AI Reader**: free, no auth; extracts clean markdown from
   HTML, often bypassing bot challenges and cookie walls.
   ```bash
   curl -sL "https://r.jina.ai/http://example.com/some-article/"
   ```

4. **Tier 4 — `tavily_extract`**: JS-rendered SPAs, auth-walled pages, batch
   extraction. Add `extract_depth=advanced` for JS-heavy/auth-walled sites.
   ```bash
   mcporter call tavily.tavily_extract urls='["https://example.com/page"]'
   ```
   → Details in [Extract](references/extract.md).

## Gotchas

- **`tavily_research` is plan-limited** and will error. Use `poe-research.research`
  or `poe-research.deep_research` instead.
- **Research timeouts:** When calling `deep_research` from pi, you must
  coordinate two timeouts — mcporter's inner `--timeout` (ms) and pi's outer
  bash `timeout` (seconds). Bash timeout must be > mcporter timeout in seconds.
  See `references/poe-research.md` → Timeout Coordination.
- **context7 rate limit:** Don't call resolve + query more than 3 times per
  question. Supplement with other tools if needed.
- **grep.app is literal:** If you wouldn't `grep` for it in your own codebase,
  don't search for it here. Use `tavily_search` for conceptual queries.
- **DeepWiki `ask_question` flakiness:** If it returns "repo not indexed", fall
  back to `read_wiki_contents` and reason over the text yourself.

## References

Each reference carries a trigger — read it when you reach for that tool.

- [Extraction Strategies](references/extraction-strategies.md) — read when you
  need to classify a URL, identify a tier's failure signal, or decide when to
  escalate vs. stop
- [Search](references/search.md) — read before tuning `tavily_search` params
- [Extract](references/extract.md) — read when using `tavily_extract` (batch,
  depth, relevance filtering)
- [Crawl & Map](references/crawl-and-map.md) — read when crawling or mapping a
  site
- [Research & Skill](references/research-and-skill.md) — read when choosing
  between `tavily_skill` and `tavily_research`
- [Poe Research](references/poe-research.md) — read when picking a model or
  coordinating research timeouts
- [Code Search](references/code-search.md) — read when crafting grep.app queries
- [Context7 Docs](references/context7-docs.md) — read when doing library doc
  lookups
- [DeepWiki](references/deepwiki.md) — read when querying repo architecture
