# tavily_search — Web Search

Search the web for current information. Returns snippets and source URLs.

## Basic Usage

```bash
mcporter call tavily.tavily_search query="your search query"
```

## Key Parameters

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

## Examples

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

## When to Choose search_depth

- `basic` — general purpose, good balance of speed and quality
- `advanced` — when you need thorough, comprehensive results and latency doesn't matter
- `fast` — quick lookups where relevance matters more than completeness
- `ultra-fast` — absolute minimum latency
