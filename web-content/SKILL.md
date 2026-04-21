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
│   ├── Raw/plain-text file? → curl -sL <url>
│   ├── HTML page (article, docs, blog)? → r.jina.ai/http://<url>
│   ├── Cloudflare docs where Jina failed? → curl -H "Accept: text/markdown"
│   └── JS SPA / auth wall / batch URLs / all else failed? → tavily_extract
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

## Tools Overview

### curl — Raw Files

Free, instant, no transformation. For any URL that serves content directly (no HTML wrapper).

```bash
curl -sL https://raw.githubusercontent.com/user/repo/main/README.md
```

Works for: raw GitHub content, `.txt`, `.md`, `.json`, `.yaml`, source code files, pastebin raw, static hosting.

Quick test: `curl -sL -o /dev/null -w '%{content_type}' <url>` — if it's `text/plain` or `application/json`, you're done.

### Jina AI Reader — HTML to Markdown

Free, no auth needed. Extracts clean markdown from HTML pages, often bypassing bot challenges that other tools hit.

```bash
curl -sL "https://r.jina.ai/http://example.com/some-article/"
```

**Validate the response** — body should be >1KB for most articles, contain actual headings, and not show "Just a moment..." or similar challenge text.

### Tavily — Search, Extract, Crawl, Map, Research

AI-native search API, accessed via mcporter: `mcporter call tavily.<tool> key=value`. Use when you need something curl and Jina can't provide.

| Tool | Job | When to use |
|------|-----|-------------|
| `tavily_search` | Web search | No URL known, need current info |
| `tavily_extract` | Extract page content | Jina failed, JS SPAs, auth walls, batch URLs |
| `tavily_crawl` | Multi-page extraction | Crawl a docs site or multi-page resource |
| `tavily_map` | Discover URLs | See what pages exist on a site |
| `tavily_research` | Deep multi-source research | Synthesize a topic across many sources |
| `tavily_skill` | Library docs lookup | AI-synthesized answer about a library/API |

### Other Tools

| Tool | Job |
|------|-----|
| `curl -H "Accept: text/markdown"` | Cloudflare docs that support markdown negotiation |
| `context7` (via mcporter) | Library docs with version pinning, returns raw doc chunks |
| `poe-research.deep_research` | Most thorough research available |
| `deepwiki` skill | Understand a GitHub repo's architecture |
| `code-search` skill | Find real code examples across GitHub |

## Extraction Hierarchy

For getting content from a single URL, escalate through these tiers — use the cheapest tool that returns the actual content:

| Tier | Tool | Best for |
|------|------|----------|
| 1 | `curl -sL` | Raw files, plain text, code |
| 2 | `r.jina.ai/http://<url>` | HTML pages (default, free) |
| 3 | `curl -H "Accept: text/markdown"` | Cloudflare docs when Jina fails |
| 4 | `tavily_extract` | Everything else: JS SPAs, auth walls, batch, complex layouts |

Always validate what you got back — check size, look for challenge text, confirm it's the article body and not nav chrome.

## References

- [Extraction Strategies](references/extraction-strategies.md) — detailed 4-tier breakdown with validation and fallback logic
- [Search](references/search.md) — `tavily_search` parameters, depth options, examples
- [Extract](references/extract.md) — `tavily_extract` parameters, batch extraction, depth guidance
- [Crawl & Map](references/crawl-and-map.md) — `tavily_crawl` and `tavily_map` parameters and tuning
- [Research & Skill](references/research-and-skill.md) — `tavily_research` and `tavily_skill` parameters, when to use each
