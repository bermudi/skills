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
- **Extract** a web page's content as markdown (JS-rendered, HTML-heavy)
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

## Curl-First Policy

**Always prefer `curl` over `tavily_extract` when the URL serves plain-text content.** If the response body is already the content you want (no JS rendering, no auth wall, no paywall), just curl it — it's faster, cheaper, and gives you the exact bytes.

### When to `curl` instead of `tavily_extract`

Use `curl -sL <url>` directly when:

- **Raw GitHub content**: `raw.githubusercontent.com`, `gist.githubusercontent.com`
- **Plain-text files**: `.txt`, `.md`, `.json`, `.yaml`, `.toml`, `.csv`, `.xml`
- **Source code URLs**: `.py`, `.js`, `.ts`, `.rs`, `.go`, `.java`, `.c`, `.h`, etc.
- **Static file hosting**: gist.github.com (raw), pastebin.com/raw/, dpaste.org/
- **Any URL where `curl` returns the content directly** (test it — if the response is the content you need, you're done)

```bash
# Raw GitHub file — just curl it
curl -sL https://raw.githubusercontent.com/user/repo/main/README.md

# Gist raw content
curl -sL https://gist.githubusercontent.com/user/hash/raw/file.md

# Pastebin raw
curl -sL https://pastebin.com/raw/abc123
```

### When you still need `tavily_extract`

- JS-rendered pages (SPAs, docs sites with client-side routing)
- Auth-walled or paywalled sites
- Pages with heavy HTML that needs cleaning/extracting
- When you need structured markdown from a complex webpage

Quick test: `curl -sL -o /dev/null -w '%{content_type}' <url>` — if it's `text/plain` or `application/json` or similar raw content, just curl. If it's `text/html` and needs parsing, use `tavily_extract`.

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

## tavily_skill — Library Documentation Search

Search documentation for any library, API, or tool. Returns structured documentation chunks relevant to your query.

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
- `tavily_skill` is broader and doesn't require resolving a library ID first. Good for quick lookups.
- `context7` (separate MCP server) gives more structured, version-specific docs but requires a two-step call (resolve library ID, then query).

---

## Decision Guide

```
Need info from the web?
├── URL to a raw/plain-text file? → curl -sL <url> (skip Tavily entirely)
├── Quick fact or current event → tavily_search
├── Content from specific HTML URLs → tavily_extract
├── Multi-page content from a site → tavily_crawl
├── Just see what URLs exist on a site → tavily_map
├── Comprehensive research on a topic → tavily_research
└── Library/framework documentation → tavily_skill
```
