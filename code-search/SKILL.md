---
name: code-search
description: "Find real-world code examples from over a million public GitHub repositories using grep.app via mcporter. Use this skill whenever you need to see how other developers actually use an API, library, or pattern in production code — not documentation, but real working code. Triggers on: \"how do people use\", \"show me examples of\", \"find code that uses\", \"real-world usage of\", \"how is X implemented in the wild\", \"show me production code for\", \"grep for\", \"search GitHub for code\". This is a literal code search engine (like grep across GitHub), not a keyword search — you search for actual code patterns, not natural language queries."
---

# Code Search with grep.app

grep.app lets you search for literal code patterns across over a million public GitHub repositories. It's like running `grep` across the entire open-source world.

Access it through mcporter: `mcporter call grep.searchGitHub key=value`.

## The Key Insight

This tool searches for **literal code patterns** — actual code that would appear in source files — not natural language queries or keywords.

- ✅ Good: `useState(`, `import React from`, `async function`, `(?s)try {.*await`
- ❌ Bad: `react tutorial`, `best practices`, `how to use hooks`

If you wouldn't `grep` for it, you shouldn't search for it here.

## Calling Convention

```bash
mcporter call grep.searchGitHub query="your code pattern" [filters]
```

Output is JSON to stdout.

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `query` | ✅ | — | The literal code pattern to search for |
| `matchCase` | ❌ | false | Case-sensitive search |
| `matchWholeWords` | ❌ | false | Match whole words only |
| `useRegexp` | ❌ | false | Interpret query as regex |
| `repo` | ❌ | — | Filter by repo (e.g. `facebook/react`, or `vercel/` for org) |
| `path` | ❌ | — | Filter by file path (e.g. `src/components/`, `route.ts`) |
| `language` | ❌ | — | Filter by language array (e.g. `["TypeScript","TSX"]`) |

## Common Patterns

### Find how people use a specific API

```bash
mcporter call grep.searchGitHub query="createServer(" language='["TypeScript"]'
```

### Find imports of a library

```bash
mcporter call grep.searchGitHub query="import { createServer } from 'http'"
```

### Find usage in a specific repo

```bash
mcporter call grep.searchGitHub query="useEffect(" repo="facebook/react"
```

### Find code in specific file types

```bash
mcporter call grep.searchGitHub query="export async function GET" path="route.ts" language='["TypeScript"]'
```

### Regex for multi-line patterns

Use `(?s)` prefix to match across newlines:

```bash
mcporter call grep.searchGitHub query="(?s)useEffect\(\(\) => {.*removeEventListener" useRegexp=true language='["TSX"]'
```

### Find configuration patterns

```bash
mcporter call grep.searchGitHub query="cors({" matchCase=true language='["Python"]'
```

### Find error handling patterns

```bash
mcporter call grep.searchGitHub query="(?s)try {.*await.*catch" useRegexp=true language='["TypeScript"]'
```

## When to Use This Tool

Use code-search when you need to:
- See real usage of an unfamiliar API or library
- Understand correct syntax, parameters, or configuration
- Find production-ready examples and best practices
- See how different libraries/frameworks compose together
- Understand common patterns that documentation doesn't cover

## When NOT to Use This

- **Looking for documentation** → Use `tavily_skill` or `context7` instead
- **Searching by concept/keyword** → Use `tavily_search` instead — grep.app needs literal code
- **Understanding a specific repo's architecture** → Use `deepwiki` instead
- **Web search for information** → Use `tavily_search`

## Tips for Good Queries

1. **Start with the function/class name** — `useState(`, `Router(`, `app.get(`
2. **Add quotes for string literals** — `import { useRouter } from 'next/navigation'`
3. **Use regex for multi-line patterns** — prefix with `(?s)` and use `.*` between parts
4. **Filter by language** — dramatically improves signal-to-noise
5. **Filter by repo or org** — `repo="vercel/"` searches all Vercel repos
6. **Use path filters** — `path="test/"` to find test examples, `path="src/"` for implementation
