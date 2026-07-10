# Extraction Strategies

For extracting content from a single URL, escalate through the tiers. Start at the lowest tier that could work — each step up costs more (latency, API calls, or both). The goal is the article body, not the footer, ads, cookie banners, or bot-challenge pages.

## How to decide which tier

Before reaching for any tool, classify the URL:

1. **Inspect the content type**: `curl -sL -o /dev/null -w '%{content_type}' <url>`
   - `text/plain`, `application/json`, `text/csv`, etc. → **Tier 1** (raw). Done.
   - `text/html` → a rendered page; start at **Tier 2**.
2. **If `text/html`**, does the site look docs-shaped (mdx, docusaurus, cloudflare-proxied)? → try **Tier 2** (Accept negotiation) first.
3. **Tier 2 returns HTML or a challenge page** → **Tier 3** (Jina).
4. **Tier 3 returns garbage, or the page needs JS rendering / auth** → **Tier 4** (Tavily).

## Failure signals per tier

Don't escalate blindly — confirm the failure before moving up, so you don't pay Tier 4 cost for a Tier 1 problem.

- **Tier 1 failure**: `curl` returns `text/html` (or the content type isn't a raw/text type) → the URL is a rendered page, not a raw file. Escalate to Tier 2.
- **Tier 2 failure**: the response body is HTML (look for `<html` or `<body`), or it's a challenge/interstitial page ("Just a moment...", "Checking your browser") rather than clean markdown. Escalate to Tier 3.
- **Tier 3 failure**: output is empty, garbled mojibake, or a login/challenge page. The page likely needs real browser rendering or auth. Escalate to Tier 4 with `extract_depth=advanced`.
- **Tier 4 failure**: the content is genuinely unreachable. Fall back to `tavily_search` for a cached/summarized version, or tell the user the page can't be extracted.

## Decision criteria

| Situation | Tier | Notes |
|---|---|---|
| Raw file, GitHub raw, gist, pastebin | 1 | Cheapest; always try first |
| Docs site, blog, plain article | 2 → 3 | Negotiate markdown; fall back to Jina |
| JS SPA (React/Vue router), auth wall (LinkedIn) | 4 | Use `extract_depth=advanced` |
| Batch of URLs | 4 | Tavily batches; curl/Jina don't |
| Need relevance filtering (long page, specific topic) | 4 | Pass `query=` to rerank chunks |
| Unknown / not sure | 1 → 2 → 3 → 4 | Escalate on confirmed failure |

## Tier 1: `curl -sL` — Raw Files

If the URL serves content directly (no HTML wrapper), just curl it. Exact bytes, zero cost, zero transformation.

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

## Tier 2: `curl -H "Accept: text/markdown"` — Markdown Negotiation

Many docs sites (especially Cloudflare-proxied ones) can return markdown directly if you ask for it. No external service, no API, just a different `Accept` header.

```bash
curl -sL -H "Accept: text/markdown" "https://example.com/some-page/"
```

If the response is clean markdown, you're done. If it returns HTML or a challenge page, move to Tier 3.

**Why try this before Jina?** No external dependency, no rate limits, instant.

## Tier 3: Jina AI Reader — HTML to Markdown

[Jina AI Reader](https://r.jina.ai/) (`r.jina.ai/http://<url>`) is a free service that extracts clean markdown from HTML pages. It handles many Cloudflare-gated and soft-paywall sites that `curl` and Tavily both fail on.

```bash
curl -sL "https://r.jina.ai/http://example.com/some-article/"
```

If the output is garbage or a challenge page, move to Tier 4.

## Tier 4: `tavily_extract` — The Heavy Lifters

Use Tavily when the free options above fail or don't apply:

- **JS-rendered SPAs** (client-side routing, heavy React/Vue apps)
- **Auth-walled sites** (LinkedIn, etc.) — use `extract_depth=advanced`
- **Multiple URLs at once** — Tavily can batch extract
- **Relevance filtering** — Tavily's `query` parameter reranks content chunks
- **Tables, embedded content, complex layouts** that simpler extractors miss

```bash
# JS-heavy SPA or auth-walled site
mcporter call tavily.tavily_extract urls='["https://www.linkedin.com/pulse/some-article"]' extract_depth=advanced

# Batch extraction with relevance filtering
mcporter call tavily.tavily_extract urls='["https://long-article-url.com","https://another-article.com"]' query="authentication JWT implementation"
```

See [Extract](extract.md) for the full parameter reference and additional examples.
