# tavily_extract — Extract Page Content

Extract content from specific URLs. Returns raw page content in markdown or text format.

## Basic Usage

```bash
mcporter call tavily.tavily_extract urls='["https://example.com/page"]'
```

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `urls` | (required) | List of URLs to extract from |
| `extract_depth` | `basic` | Use `advanced` for LinkedIn, protected sites, tables, embedded content |
| `format` | `markdown` | `markdown` or `text` |
| `include_images` | false | Include images from pages |
| `query` | "" | Query to rerank content chunks by relevance |

## Examples

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

## When to Use extract_depth=advanced

- LinkedIn or other auth-walled sites
- Pages with lots of tables or embedded content
- JS-rendered content that basic extraction misses
