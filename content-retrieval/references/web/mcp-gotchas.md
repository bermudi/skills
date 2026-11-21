# Web MCP Tools — Routing & Gotchas

All web MCP servers below run through `mcporter call <server>.<tool> key=value`. Run `mcporter list <server>` for live tool signatures and optional parameters instead of memorizing flags.

For outer shell timeout coordination, follow the `mcporter` skill: outer shell timeout (seconds in Pi, ms in Claude/Devin) must exceed `--timeout`.

## Tavily (`tavily`)

Tools: `tavily_search`, `tavily_extract`, `tavily_crawl`, `tavily_map`, `tavily_research`.

- **Search (`tavily_search`):** Keep queries short and specific (one idea per query). `include_domains` takes full domains (`"en.wikipedia.org"`), not TLDs (`"edu"`), and acts as a hard filter — drop it if results come back thin. `time_range`, `start_date`, and `end_date` filter by *publish date*, not when an event happened. Avoid `include_raw_content=true` for whole pages — use `tavily_extract` with a `query=` instead.
- **Extract (`tavily_extract`):** Use only after Tiers 1–3 fail, or for batching/JS SPAs/auth walls (`extract_depth=advanced`). Pass `query=` to rerank chunks on long articles/PDFs, **but omit `query=` for tables, lists, data files, or API responses** (chunking can truncate them). Check `failed_results`; retry a timeout once, then switch source.
- **Map & Crawl (`tavily_map`, `tavily_crawl`):** Map first (`tavily_map`) to inspect URL structure before crawling. Pass `instructions` or `select_paths` regexes so crawls stay bounded. Large crawls (`limit > 30`, `max_depth > 2`, or `extract_depth=advanced`) exceed mcporter's 60s default — set `--timeout 180000`+.
- **Research (`tavily_research`):** Multi-source synthesis (`input=`, `model="mini"|"pro"|"auto"`, optional base64 `files=`). Set `--timeout 300000`+ (`pro` can take minutes). Note: some Tavily plans gate `tavily_research` — if it returns a plan/quota error, fall back to `tavily_search` + `tavily_extract` and synthesize locally.

```bash
mcporter call tavily.tavily_search query="Rust 1.85 release notes" max_results=10
mcporter call tavily.tavily_extract urls='["https://example.com/page"]' extract_depth=advanced
mcporter call tavily.tavily_map url="https://docs.example.com" max_depth=2 limit=100
mcporter call tavily.tavily_research input="Compare Bun and Deno HTTP servers" model=mini --timeout 300000
```

## Context7 (`context7`) — Library Documentation

Two-step flow: resolve the library ID first (unless the user gave `/org/project` or `/org/project/version`), then query docs. Returns raw, unsynthesized doc chunks.

```bash
mcporter call context7.resolve-library-id query="middleware setup" libraryName="Express.js"
mcporter call context7.query-docs libraryId="/expressjs/express" query="how to set up JWT middleware" language="TypeScript"
```

- **Official punctuation matters:** `"Next.js"` not `"nextjs"`, `"Three.js"` not `"threejs"`.
- **Scope each query to one specific concept** (`"React useEffect cleanup"`, not `"hooks"` or `"routing and auth and caching"`). Pass `language=` when known to rank matching code examples first.
- **Version pinning:** If `resolve-library-id` returns versions, pass `/org/project/version` as `libraryId`.
- **Rate limit:** At most 3 resolve/query calls per question. Do not send secrets or proprietary code in queries.

## DeepWiki (`deepwiki`) — GitHub Repo Architecture

Tools: `read_wiki_structure`, `read_wiki_contents`, `ask_wiki_question` (note the exact name: **`ask_wiki_question`**, not `ask_question`).

```bash
mcporter call deepwiki.ask_wiki_question repoName="vercel/next.js" question="How does the App Router work?"
mcporter call deepwiki.ask_wiki_question repoName='["pnpm/pnpm","npm/cli"]' question="How do dependency resolution algorithms differ?"
```

- **Only `ask_wiki_question` does AI reasoning** (accepts a single `owner/repo` string or up to 10 in an array). `read_wiki_structure` and `read_wiki_contents` return pre-generated text.
- **False "not indexed" fallback:** `ask_wiki_question` occasionally reports "repo not indexed" even when the wiki exists — fall back to `read_wiki_contents` (or `read_wiki_structure` first on large repos) and reason over it yourself.

## grep.app (`grep`) — Cross-Repo Literal Code Search

Single tool: `grep.searchGitHub`. Searches **literal source code**, not prose or tutorials. If you wouldn't `rg` for it in a codebase, use `tavily_search` instead.

```bash
mcporter call grep.searchGitHub query="createServer(" language='["TypeScript"]'
mcporter call grep.searchGitHub query="(?s)useEffect\(\(\) => {.*removeEventListener" useRegexp=true language='["TSX"]'
```

- **Regex across lines:** Set `useRegexp=true` and prefix with `(?s)` so `.` matches newlines.
- **High-signal filters:** `language='["TypeScript","TSX"]'`, `repo="vercel/"` (trailing slash matches an org), `path="route.ts"`, `matchCase=true`, `matchWholeWords=true`.
