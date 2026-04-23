# tavily_crawl — Crawl a Website

Crawl a website starting from a URL. Extracts content from multiple pages with configurable depth and breadth.

**⚠️ Timeout note:** Large crawls (`limit > 30`, `max_depth > 2`, or `extract_depth=advanced`) can exceed mcporter's 60s default. Add `--timeout <ms>` as needed.

## Basic Usage

```bash
mcporter call tavily.tavily_crawl url="https://docs.example.com"
```

## Key Parameters

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

## Examples

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

## How to Tune Crawl Parameters

- `max_depth=1` — just the starting page and its direct links. Good for a quick scan.
- `max_depth=2-3` — deeper exploration. Use with `limit` to cap total pages.
- `instructions` is powerful — use it to tell the crawler what you're looking for rather than crawling everything.
- `select_paths` with regex is precise — use it when you know the URL structure.

---

# tavily_map — Map Site Structure

Discover URLs on a site without extracting content. Returns a list of URLs found starting from the base URL.

## Basic Usage

```bash
mcporter call tavily.tavily_map url="https://example.com"
```

## Key Parameters

Same parameters as crawl but without extraction: `url`, `max_depth`, `max_breadth`, `limit`, `instructions`, `select_paths`, `select_domains`, `allow_external`.

## Examples

**Map a documentation site:**
```bash
mcporter call tavily.tavily_map url="https://docs.python.org/3/" max_depth=2 limit=100
```

**Find API endpoints:**
```bash
mcporter call tavily.tavily_map url="https://api.example.com" select_paths='["/api/v[0-9]+/.*"]'
```

## When to Use Map vs Crawl

- Use **map** when you want to see what's there before committing to extraction. Good for planning a crawl.
- Use **crawl** when you want the actual content.
- A common pattern: map first, then extract or crawl specific URLs.
