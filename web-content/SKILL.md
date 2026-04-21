---
name: web-content
description: "Fetch, extract, search, crawl, and research online content using the best available tool for each job. Covers raw file downloads (curl), HTML-to-markdown extraction (Jina AI Reader), web search (Tavily), site crawling and mapping (Tavily), deep multi-source research (Tavily, Poe), and library documentation lookup (Tavily, Context7). Triggers on: \"search the web\", \"look this up\", \"what's the latest on\", \"scrape this page\", \"extract content from\", \"crawl this site\", \"map this website\", \"research this topic\", \"find information about\", \"what does the web say about\", \"fetch this URL\", \"get the content of\", \"pull down this page\"."
---

# Web Content

Get information from the internet — the right way, with the right tool.

This skill covers everything from fetching a single raw file to synthesizing deep multi-source research. The key is matching the job to the tool instead of routing everything through one API.

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
│   └── Still failed? → see Extraction Strategies reference
│
├── Information, but no URL yet
│   ├── Quick fact or current event → tavily_search
│   ├── Library docs, synthesized answer → tavily_skill (one call, AI-generated)
│   ├── Library docs, specific version or raw text → context7 (two calls, raw chunks)
│   └── Understand a GitHub repo's architecture → deepwiki skill
│
├── Content from a whole site
│   ├── See what URLs exist → tavily_map
│   └── Get actual page content → tavily_crawl
│
├── Deep synthesis on a topic
│   ├── Multi-source research → tavily_research
│   └── Most thorough analysis → poe-research.deep_research
│
└── Real code examples in production repos → code-search skill (grep.app)
```

## Extraction Hierarchy — Content from a Known URL

When you have a URL and need its content, escalate through these tiers. Always start at the lowest tier that could work — each step up costs more (latency, API calls, or both).

### Tier 1: `curl -sL` — Raw Files

If the URL serves content directly (no HTML wrapper), just curl it. Exact bytes, zero cost, zero transformation.

```bash
curl -sL https://raw.githubusercontent.com/user/repo/main/README.md
```

Works for: raw GitHub content, `.txt`, `.md`, `.json`, `.yaml`, source code files, pastebin raw, any static file. Avoid for html content.

Quick test: `curl -sL -o /dev/null -w '%{content_type}' <url>` — if it's `text/plain`, `application/json`, etc., you're done.

### Tier 2: `curl -H "Accept: text/markdown"` — Markdown Negotiation

Many docs sites (especially Cloudflare-proxied ones) can return markdown directly if you ask for it. No external service, no API, just a different `Accept` header.

```bash
curl -sL -H "Accept: text/markdown" "https://example.com/docs/page"
```

If the response is clean markdown, you're done. If it returns HTML or a challenge page, move to Tier 3.

**Why try this before Jina?** No external dependency, no rate limits, instant.

### Tier 3: Jina AI Reader — HTML to Markdown

Free, no auth needed. Extracts clean markdown from HTML, often bypassing bot challenges and cookie walls.

```bash
curl -sL "https://r.jina.ai/http://example.com/some-article/"
```

If the output is garbage or a challenge page, move to Tier 4.

### Tier 4: `tavily_extract` — The Heavy Lifters

When the free options above fail or don't apply — JS-rendered SPAs, auth-walled pages, batch extraction of multiple URLs, or complex layouts with tables/embedded content.

```bash
mcporter call tavily.tavily_extract urls='["https://example.com/page"]'
```

For JS-heavy or auth-walled sites, add `extract_depth=advanced`. For batch extraction, pass multiple URLs. For relevance filtering, add a `query` parameter.

→ Full details in [Extraction Strategies](references/extraction-strategies.md) and [Extract](references/extract.md).

## Other Web Tools

### Tavily — Search, Crawl, Map, Research

AI-native search API, accessed via mcporter: `mcporter call tavily.<tool> key=value`.

| Tool | Job | When to use |
|------|-----|-------------|
| `tavily_search` | Web search | No URL known, need current info |
| `tavily_crawl` | Multi-page extraction | Crawl a docs site or multi-page resource |
| `tavily_map` | Discover URLs | See what pages exist on a site |
| `tavily_research` | Deep multi-source research | Synthesize a topic across many sources |
| `tavily_skill` | Library docs lookup | AI-synthesized answer about a library/API |

### Other Tools

| Tool | Job |
|------|-----|
| `context7` (via mcporter) | Library docs with version pinning, returns raw doc chunks |
| `poe-research.deep_research` | Most thorough research available |
| `deepwiki` skill | Understand a GitHub repo's architecture |
| `code-search` skill | Find real code examples across GitHub |



## References

- [Extraction Strategies](references/extraction-strategies.md) — detailed 4-tier breakdown with validation and fallback logic
- [Search](references/search.md) — `tavily_search` parameters, depth options, examples
- [Extract](references/extract.md) — `tavily_extract` parameters, batch extraction, depth guidance
- [Crawl & Map](references/crawl-and-map.md) — `tavily_crawl` and `tavily_map` parameters and tuning
- [Research & Skill](references/research-and-skill.md) — `tavily_research` and `tavily_skill` parameters, when to use each
