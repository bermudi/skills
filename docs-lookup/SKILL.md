---
name: docs-lookup
description: "Look up up-to-date documentation and code examples for any programming library or framework using Context7 via mcporter. Use this skill whenever you need current docs for a library, framework, or package — how to use an API, configuration options, migration guides, or code examples. Triggers on: \"how to use X library\", \"X framework docs\", \"look up docs for\", \"find documentation for\", \"what's the API for\", \"how do I configure X\", \"X library reference\", \"show me the docs\", \"latest docs for\", \"check the documentation\". Prefer this over relying on potentially outdated built-in knowledge."
---

# Library Documentation Lookup with Context7

Context7 provides up-to-date documentation and code examples for any programming library or framework. It always returns current docs, so you don't have to rely on potentially outdated training data.

Access it through mcporter. **Important**: Context7 requires a two-step process — first resolve the library ID, then query the docs.

## Two-Step Workflow

### Step 1: Resolve Library ID

Before you can query docs, you need the Context7-compatible library ID. Always resolve first unless the user provides an ID in `/org/project` format.

```bash
mcporter call context7.resolve-library-id query="what you're trying to do" libraryName="LibraryName"
```

- `query` — your specific question or task. Used to rank results by relevance.
- `libraryName` — the official library name with proper punctuation (e.g. `Next.js` not `nextjs`, `Three.js` not `threejs`)

The response returns matching libraries with IDs like `/vercel/next.js`, scores, and available versions.

**Example:**
```bash
mcporter call context7.resolve-library-id query="how to set up middleware in Next.js App Router" libraryName="Next.js"
```

### Step 2: Query Documentation

Use the library ID from step 1 to get actual documentation.

```bash
mcporter call context7.query-docs libraryId="/vercel/next.js" query="how to set up middleware in App Router"
```

- `libraryId` — the exact ID from step 1 (e.g. `/mongodb/docs`, `/vercel/next.js`)
- `query` — specific question. Good: "How to set up JWT authentication in Express.js". Bad: "auth".

**Example:**
```bash
mcporter call context7.query-docs libraryId="/supabase/supabase" query="how to set up row-level security policies"
```

## Guidelines

### Write Good Queries
The query parameter matters a lot. Be specific about what you're trying to accomplish:

| Bad Query | Good Query |
|-----------|------------|
| `auth` | `How to set up authentication with JWT in Express.js` |
| `hooks` | `React useEffect cleanup function examples` |
| `routing` | `How to create dynamic routes with App Router` |

### Version-Specific Docs
If the resolve step returns versions, you can use them:
```bash
mcporter call context7.query-docs libraryId="/vercel/next.js/v14.3.0-canary.87" query="server actions"
```

### Rate Limiting
Don't call either tool more than 3 times per question. If you can't find what you need after 3 calls, use the best result you have and supplement with other tools.

## Examples

### Look up a specific API
```bash
# Step 1
mcporter call context7.resolve-library-id query="upsert operation with conflict handling" libraryName="Drizzle ORM"
# Step 2 (using the returned ID)
mcporter call context7.query-docs libraryId="/drizzle-team/drizzle-orm" query="how to do upsert with on conflict do update"
```

### Migration guide
```bash
mcporter call context7.resolve-library-id query="migrating from Pages Router to App Router" libraryName="Next.js"
# Then query with the resolved ID
mcporter call context7.query-docs libraryId="/vercel/next.js" query="migration from Pages Router to App Router"
```

### Configuration reference
```bash
mcporter call context7.resolve-library-id query=" configuring ESLint flat config" libraryName="ESLint"
mcporter call context7.query-docs libraryId="/eslint/eslint" query="how to configure flat config with custom rules"
```

## Context7 vs tavily_skill vs deepwiki

| Need | Tool | Why |
|------|------|-----|
| Current docs for a specific library version | **context7** | Structured, version-aware, high quality |
| Quick doc lookup without knowing the library ID | **tavily_skill** | One-step, broader but less precise |
| Understand a GitHub repo's architecture | **deepwiki** | Repo-level understanding, not just docs |
| Find real code examples in the wild | **code-search** | Actual production code, not documentation |

Context7 is the best choice when you know exactly which library you need docs for and want structured, version-specific results. Use `tavily_skill` for quick one-shot lookups where the extra precision isn't needed.
