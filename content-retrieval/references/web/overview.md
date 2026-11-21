# Web Retrieval, Search, and Research

Route by what you have and how much you need. Escalate by cost — free/local first, paid MCP tools only when cheaper tiers fail or don't fit.

## Decision Guide

```text
What do you need?
│
├── Content from a known URL
│   ├── Raw/plain-text file? → curl -sL <url>                          (Tier 1)
│   ├── HTML page? → try in order:
│   │   ├── curl -H "Accept: text/markdown" <url>                     (Tier 2)
│   │   ├── r.jina.ai/http://<url>                                    (Tier 3)
│   │   └── tavily.tavily_extract                                     (Tier 4)
│   └── Blocked or unclear? → extraction-strategies.md
│
├── Remote GitHub repository, path, or ref
│   ├── Browse a tree or read/compare exact files → gh repo read-dir/read-file
│   ├── Understand architecture or design → deepwiki.ask_wiki_question
│   ├── Find literal code patterns across repos → grep.searchGitHub
│   └── Search/traverse many files, build, or edit → clone and use local tools
│
├── Information, no URL yet
│   ├── Quick fact or current event → tavily.tavily_search
│   ├── Multi-source synthesized research → tavily.tavily_research (fallback: search + extract)
│   └── Library docs (raw chunks, version-specific) → context7
│
└── Content from a whole site
    ├── Discover URLs → tavily.tavily_map
    └── Pull multi-page content → tavily.tavily_crawl
```

## Quick Reference

| Tool | Server | Best For | Reference |
|------|--------|----------|-----------|
| `curl -sL` | — | Raw files, raw GitHub content | [extraction-strategies.md](extraction-strategies.md) |
| `curl -H "Accept: text/markdown"` | — | Docs sites that negotiate markdown | [extraction-strategies.md](extraction-strategies.md) |
| `r.jina.ai/http://...` | — | HTML → markdown, bypasses light challenges | [extraction-strategies.md](extraction-strategies.md) |
| `tavily_extract` | `tavily` | JS SPAs, auth walls, batch extraction | [mcp-gotchas.md](mcp-gotchas.md#tavily-tavily) |
| `tavily_search` | `tavily` | Quick facts, current events | [mcp-gotchas.md](mcp-gotchas.md#tavily-tavily) |
| `tavily_research` | `tavily` | Multi-source synthesized research | [mcp-gotchas.md](mcp-gotchas.md#tavily-tavily) |
| `tavily_map` / `tavily_crawl` | `tavily` | Site URL discovery / multi-page crawl | [mcp-gotchas.md](mcp-gotchas.md#tavily-tavily) |
| `gh repo read-dir` / `read-file` | GitHub CLI | Surgical repo inspection without cloning | [github-repo-read.md](github-repo-read.md) |
| `grep.searchGitHub` | `grep` | Literal code patterns across GitHub | [mcp-gotchas.md](mcp-gotchas.md#grepapp-grep--cross-repo-literal-code-search) |
| `context7` | `context7` | Current / versioned library docs | [mcp-gotchas.md](mcp-gotchas.md#context7-context7--library-documentation) |
| `deepwiki` | `deepwiki` | Repo architecture and Q&A | [mcp-gotchas.md](mcp-gotchas.md#deepwiki-deepwiki--github-repo-architecture) |

## Quick Calls

```bash
# Remote GitHub repo without cloning
gh repo read-dir --repo cli/cli
gh repo read-file go.mod --repo cli/cli --ref v2.94.0

# Web search / multi-source research
mcporter call tavily.tavily_search query="your search query"
mcporter call tavily.tavily_research input="your research topic" model=mini --timeout 300000

# Literal code search (grep-style patterns, NOT prose)
mcporter call grep.searchGitHub query="createServer(" language='["TypeScript"]'

# Library docs (two-step: resolve ID, then query)
mcporter call context7.resolve-library-id query="middleware setup" libraryName="Express.js"
mcporter call context7.query-docs libraryId="/expressjs/express" query="middleware setup" language="TypeScript"

# Repo architecture (note exact tool name: ask_wiki_question)
mcporter call deepwiki.ask_wiki_question repoName="vercel/next.js" question="How does the App Router work?"
```

## URL Extraction — Escalate by Cost

1. **Tier 1 — `curl -sL`:** raw files (`text/plain`, `application/json`, raw GitHub). Quick check: `curl -sL -o /dev/null -w '%{content_type}' <url>`.
2. **Tier 2 — `curl -sL -H "Accept: text/markdown"`:** docs sites that negotiate markdown directly.
3. **Tier 3 — Jina AI Reader:** `curl -sL "https://r.jina.ai/http://example.com/page"` — free HTML → markdown.
4. **Tier 4 — `tavily.tavily_extract`:** JS SPAs, auth walls (`extract_depth=advanced`), batch extraction.

## References

- [extraction-strategies.md](extraction-strategies.md) — URL classification, UA blocking before escalation, per-tier failure signals.
- [mcp-gotchas.md](mcp-gotchas.md) — gotchas, rate limits, fallbacks, and timeouts for `tavily`, `context7`, `deepwiki`, and `grep` (use `mcporter list <server>` for full parameter schemas).
- [github-repo-read.md](github-repo-read.md) — `gh repo read-dir`/`read-file` flags, jq patterns, escape-sequence guard, and clone cutoff.
