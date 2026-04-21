---
name: web-search
description: "Search the web, extract page content, crawl websites, map site structure, and perform deep multi-source research using Tavily via mcporter. Use this skill whenever you need current information from the internet — web search, scraping/extracting content from URLs, crawling a site, understanding a site's structure, or doing comprehensive research on a topic. Triggers on: \"search the web\", \"look this up\", \"what's the latest on\", \"scrape this page\", \"extract content from\", \"crawl this site\", \"map this website\", \"research this topic\", \"find information about\", \"what does the web say about\". Also use when you need library docs via tavily_skill (search documentation for any library/API/tool)."
---

# Web Search & Research with Tavily

Tavily is an AI-native search and extraction API. You access it through mcporter, which acts as the MCP client. All calls go through `mcporter call tavily.<tool> key=value`.

## Use the Right Tool for the Job

**Not everything that touches the internet should go through Tavily.** Tavily is for searching, extracting web pages as markdown, crawling sites, and deep research. It is NOT a general-purpose internet Swiss army knife.

### Use native CLI tools instead of Tavily for:

| Task | Tool | Why
|------|------|----
| Clone a git repo | `git clone` | Tavily can't do this
| Fetch a raw text/code/markdown file | `curl -sL <url>` | Faster, cheaper, exact bytes (see Curl-First Policy below)
| Download a file | `curl -O` or `wget` | Tavily isn't a download manager
| Interact with an API | `curl` / `httpie` | Tavily isn't an HTTP client
| Install a package | `bun add`, `uv add`, etc. | Tavily isn't a package manager
| Run a command on a remote host | `ssh` | Tavily isn't SSH

### When Tavily IS the right choice:

- **Search** the web for information you don't have a URL for
- **Extract** JS-rendered SPAs, auth-walled pages, or complex layouts that Jina AI Reader failed to capture
- **Batch extract** multiple URLs in one call
- **Crawl** a multi-page documentation site
- **Research** a topic comprehensively across many sources
- **Look up** library/framework documentation

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| `tavily_search` | Web search | Quick facts, current events, finding sources |
| `tavily_extract` | Extract page content | Scraping specific URLs for their content |
| `tavily_crawl` | Crawl a site | Multi-page extraction from a domain |
| `tavily_map` | Map site structure | Discover URLs on a site without extracting |
| `tavily_research` | Deep research | Comprehensive multi-source research on a topic |
| `tavily_skill` | Library docs search | Find documentation for a specific library/API |

## Calling Convention

All tools are invoked via:
```bash
mcporter call tavily.<tool_name> key=value key2=value2
```

The output is JSON to stdout. Parse it with `jq` or process inline.

## Extraction Hierarchy: Get the Content, Not the Chrome

For extracting content from a single URL, prefer the cheapest tool that actually returns the *article body*, not the footer, ads, cookie banners, or bot-challenge pages.

### Tier 1: `curl -sL` for raw files

If the URL serves the content directly (no HTML wrapper), just curl it. You get exact bytes, zero cost, zero transformation.

Use `curl -sL <url>` directly when:

- **Raw GitHub content**: `raw.githubusercontent.com`, `gist.githubusercontent.com`
- **Plain-text files**: `.txt`, `.md`, `.json`, `.yaml`, `.toml`, `.csv`, `.xml`
- **Source code URLs**: `.py`, `.js`, `.ts`, `.rs`, `.go`, `.java`, `.c`, `.h`, etc.
- **Static file hosting**: gist.github.com (raw), pastebin.com/raw/, dpaste.org/

```bash
# Raw GitHub file — just curl it
curl -sL https://raw.githubusercontent.com/user/repo/main/README.md

# Pastebin raw
curl -sL https://pastebin.com/raw/abc123
```

Quick test: `curl -sL -o /dev/null -w '%{content_type}' <url>` — if it's `text/plain`, `application/json`, etc., you're done.

### Tier 2: Jina AI Reader for HTML pages

[Jina AI Reader](https://r.jina.ai/) (`r.jina.ai/http://<url>`) is a free service that extracts clean markdown from HTML pages. It handles many Cloudflare-gated and soft-paywall sites that `curl` and Tavily both fail on.

**Why it's the default for HTML extraction:**
- Free, no API key, no mcporter cost
- Often bypasses bot challenges and cookie walls
- Returns clean markdown with article body intact
- Faster than Tavily for single-page extraction

```bash
# Default extraction for any HTML URL
curl -sL "https://r.jina.ai/http://example.com/some-article/"
```

**Validate the response before using it:**
- Body should be non-trivial (>1KB for most articles)
- Should not contain "Just a moment...", "Performing security verification", or similar challenge text
- Should contain actual content, not just navigation/footer chrome

```bash
# Quick validation pipeline
curl -sL "https://r.jina.ai/http://example.com/page/" -o /tmp/jina.md
wc -c /tmp/jina.md              # Should be > 1KB
grep -c "^#" /tmp/jina.md       # Should have markdown headings
```

### Tier 3: Markdown negotiation (Cloudflare docs)

Some Cloudflare-proxied sites (especially docs and blogs) support `Accept: text/markdown`. It's a 1-second pre-check worth trying on suspected Cloudflare zones before falling back to Tavily.

```bash
curl -sL -H "Accept: text/markdown" \
  -o /tmp/page.md -w "%{content_type}\n" \
  "https://example.com/some-page/"
```

Use directly if `Content-Type` is `text/markdown` and body is substantial. Skip if it returns `text/html` or a challenge page.

### Tier 4: `tavily_extract` as fallback

Use Tavily when Jina and markdown negotiation both fail, or when you need features only Tavily provides:

- **JS-rendered SPAs** (client-side routing, heavy React/Vue apps)
- **Auth-walled sites** (LinkedIn, etc.) — use `extract_depth=advanced`
- **Multiple URLs at once** — Tavily can batch extract
- **Relevance filtering** — Tavily's `query` parameter reranks content chunks
- **Tables, embedded content, complex layouts** that simple extractors miss

```bash
# JS-heavy SPA or auth-walled site
mcporter call tavily.tavily_extract urls='["https://www.linkedin.com/pulse/some-article"]' extract_depth=advanced

# Batch extraction with relevance filtering
mcporter call tavily.tavily_extract urls='["https://long-article-url.com","https://another-article.com"]' query="authentication JWT implementation"
```

---

## tavily_search — Web Search

Search the web for current information. Returns snippets and source URLs.

### Basic Usage
```bash
mcporter call tavily.tavily_search query="your search query"
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `query` | (required) | Search query |
| `max_results` | 5 | Number of results (1-10) |
| `search_depth` | `basic` | `basic`, `advanced` (more thorough), `fast` (low latency), `ultra-fast` (prioritize speed) |
| `topic` | `general` | Search category |
| `time_range` | null | `day`, `week`, `month`, `year` — restrict to recent results |
| `include_domains` | [] | Restrict to specific domains, e.g. `["github.com", "stackoverflow.com"]` |
| `exclude_domains` | [] | Exclude specific domains |
| `country` | "" | Boost results from a country (full name, e.g. "United States") |
| `include_raw_content` | false | Include cleaned HTML of each result |
| `include_images` | false | Include related images |
| `start_date` | "" | Results after date (YYYY-MM-DD) |
| `end_date` | "" | Results before date (YYYY-MM-DD) |

### Examples

**Quick search:**
```bash
mcporter call tavily.tavily_search query="Rust 1.85 release notes"
```

**Thorough search with date filter:**
```bash
mcporter call tavily.tavily_search query="Next.js 16 migration guide" search_depth=advanced max_results=10 time_range=month
```

**Search specific sites only:**
```bash
mcporter call tavily.tavily_search query="useEffect cleanup function" include_domains='["react.dev","stackoverflow.com"]'
```

**Get raw page content alongside results:**
```bash
mcporter call tavily.tavily_search query="Python GIL removal PEP 703" include_raw_content=true max_results=3
```

### When to choose search_depth
- `basic` — general purpose, good balance of speed and quality
- `advanced` — when you need thorough, comprehensive results and latency doesn't matter
- `fast` — quick lookups where relevance matters more than completeness
- `ultra-fast` — absolute minimum latency

---

## tavily_extract — Extract Page Content

Extract content from specific URLs. Returns raw page content in markdown or text format.

### Basic Usage
```bash
mcporter call tavily.tavily_extract urls='["https://example.com/page"]'
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `urls` | (required) | List of URLs to extract from |
| `extract_depth` | `basic` | Use `advanced` for LinkedIn, protected sites, tables, embedded content |
| `format` | `markdown` | `markdown` or `text` |
| `include_images` | false | Include images from pages |
| `query` | "" | Query to rerank content chunks by relevance |

### Examples

**Extract a single page:**
```bash
mcporter call tavily.tavily_extract urls='["https://docs.python.org/3/whatsnew/3.13.html"]'
```

**Extract multiple pages at once:**
```bash
mcporter call tavily.tavily_extract urls='["https://blog.rust-lang.org/2025/02/20/Rust-1.85.0.html","https://blog.rust-lang.org/2025/03/20/Rust-1.86.0.html"]'
```

**Scrape a protected/JS-heavy site:**
```bash
mcporter call tavily.tavily_extract urls='["https://www.linkedin.com/pulse/some-article"]' extract_depth=advanced
```

**Extract and filter by relevance:**
```bash
mcporter call tavily.tavily_extract urls='["https://long-article-url.com"]' query="authentication JWT implementation"
```

### When to use extract_depth=advanced
- LinkedIn or other auth-walled sites
- Pages with lots of tables or embedded content
- JS-rendered content that basic extraction misses

---

## tavily_crawl — Crawl a Website

Crawl a website starting from a URL. Extracts content from multiple pages with configurable depth and breadth.

### Basic Usage
```bash
mcporter call tavily.tavily_crawl url="https://docs.example.com"
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `url` | (required) | Root URL to start crawling |
| `max_depth` | 1 | How far from the base URL to explore |
| `max_breadth` | 20 | Max links to follow per page |
| `limit` | 50 | Total pages to process before stopping |
| `instructions` | "" | Natural language filter — which pages to return |
| `select_paths` | [] | Regex patterns for URL paths (e.g. `["/docs/.*"]`) |
| `select_domains` | [] | Regex patterns to restrict to domains |
| `extract_depth` | `basic` | `basic` or `advanced` |
| `format` | `markdown` | Output format |

### Examples

**Crawl documentation site:**
```bash
mcporter call tavily.tavily_crawl url="https://docs.myframework.com" max_depth=2 limit=20 instructions="API reference pages"
```

**Crawl only specific paths:**
```bash
mcporter call tavily.tavily_crawl url="https://example.com/docs" select_paths='["/docs/api/.*"]' max_depth=3
```

**Targeted crawl with instructions:**
```bash
mcporter call tavily.tavily_crawl url="https://nextjs.org" instructions="pages about App Router routing and layouts" max_depth=2 limit=10
```

### How to tune crawl parameters
- `max_depth=1` — just the starting page and its direct links. Good for a quick scan.
- `max_depth=2-3` — deeper exploration. Use with `limit` to cap total pages.
- `instructions` is powerful — use it to tell the crawler what you're looking for rather than crawling everything.
- `select_paths` with regex is precise — use it when you know the URL structure.

---

## tavily_map — Map Site Structure

Discover URLs on a site without extracting content. Returns a list of URLs found starting from the base URL.

### Basic Usage
```bash
mcporter call tavily.tavily_map url="https://example.com"
```

### Key Parameters

Same as crawl but no extraction — just URL discovery. Parameters: `url`, `max_depth`, `max_breadth`, `limit`, `instructions`, `select_paths`, `select_domains`, `allow_external`.

### Examples

**Map a documentation site:**
```bash
mcporter call tavily.tavily_map url="https://docs.python.org/3/" max_depth=2 limit=100
```

**Find API endpoints:**
```bash
mcporter call tavily.tavily_map url="https://api.example.com" select_paths='["/api/v[0-9]+/.*"]'
```

### When to use map vs crawl
- Use **map** when you want to see what's there before committing to extraction. Good for planning a crawl.
- Use **crawl** when you want the actual content.
- A common pattern: map first, then extract or crawl specific URLs.

---

## tavily_research — Deep Research

Comprehensive multi-source research on a topic. Rate limit: 20 requests/minute.

### Basic Usage
```bash
mcporter call tavily.tavily_research input="Comprehensive description of what you want to research"
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `input` | (required) | Detailed description of the research task |
| `model` | `auto` | `mini` (narrow, few subtopics), `pro` (broad, many subtopics), `auto` |

### Examples

**Quick focused research:**
```bash
mcporter call tavily.tavily_research input="What are the main differences between Python's asyncio and trio libraries for async programming?" model=mini
```

**Broad deep research:**
```bash
mcporter call tavily.tavily_research input="State of the art in LLM reasoning: chain-of-thought, tree-of-thought, and other approaches. Include recent papers from 2025, key benchmarks, and practical recommendations." model=pro
```

### When to use research vs search
- Use **search** when you need quick answers, facts, or a few sources.
- Use **research** when you need a comprehensive, synthesized answer from multiple sources with analysis.
- Research is slower but much more thorough — it runs multiple searches and synthesizes the results.

---

## tavily_skill — AI-Synthesized Library Documentation

Search documentation for any library, API, or tool. Unlike Context7 (which returns raw doc chunks), `tavily_skill` uses AI to synthesize a structured response — it searches a doc index, then generates a coherent answer with setup guides, code examples, gotchas, and version notes. The output follows a consistent template (`What it is`, `When to use`, `Correct setup`, `Critical gotchas`) that is clearly AI-generated, not raw scraped content.


### Basic Usage
```bash
mcporter call tavily.tavily_skill query="how to use middleware in Express.js" library="express"
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `query` | (required) | Natural language query about a library |
| `library` | "" | Library/package name (e.g. `nextjs`, `celery`, `httpx`) |
| `language` | "" | Programming language to boost results |
| `task` | null | `integrate`, `configure`, `debug`, `migrate`, `understand` |
| `context` | "" | Brief description of your project/stack |
| `max_tokens` | 8000 | Maximum tokens in response |

### Examples

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

### When to use tavily_skill vs context7

| | `tavily_skill` | `context7` |
|---|---|---|
| **AI synthesis** | ✅ Yes — generates structured response | ❌ No — returns raw doc chunks |
| **Steps** | One call | Two calls (resolve ID, then query) |
| **Version targeting** | No | Yes — can pin to specific version |
| **Best for** | Quick "how do I..." lookups | When you need exact doc text or a specific version |

Use `tavily_skill` when you want a quick, synthesized answer. Use `context7` when you need the raw documentation text (e.g., to verify exact API signatures) or need a specific library version.

---

## Decision Guide

```
Need info from the web?
├── URL to a raw/plain-text file? → curl -sL <url> (exact bytes, zero cost)
├── HTML page (article, docs, blog)? → r.jina.ai/http://<url> (free, clean markdown)
├── Jina failed / JS-heavy SPA / auth wall? → tavily_extract
├── Cloudflare docs zone? → curl -H "Accept: text/markdown" (1-sec pre-check)
├── Quick fact or current event → tavily_search
├── Multi-page content from a site → tavily_crawl
├── Just see what URLs exist on a site → tavily_map
├── Library docs, quick synthesized answer → tavily_skill (AI-synthesized, one-step)
├── Library docs, specific version or raw text → context7 (raw chunks, two-step)
├── Understand a GitHub repo's architecture → deepwiki
├── Research a topic (general) → tavily_research or poe-research.research
├── Deep research (most thorough) → poe-research.deep_research
└── Real code examples in production repos → code-search (grep.app)
```
