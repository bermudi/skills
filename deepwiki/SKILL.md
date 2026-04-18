---
name: deepwiki
description: "Understand GitHub repositories through AI-powered documentation and Q&A using DeepWiki via mcporter. Use this skill whenever you need to understand how a GitHub repo works, what its architecture looks like, how to use it, or have questions about its codebase. Triggers on: \"how does X repo work\", \"explain this GitHub repo\", \"what does this library do\", \"how is X implemented in repo Y\", \"understand the architecture of\", \"show me the docs for this repo\", \"ask about a GitHub repository\". Also use when you need a quick overview of an open-source project without reading the entire source."
---

# GitHub Repo Documentation with DeepWiki

DeepWiki provides AI-generated documentation and Q&A for GitHub repositories. It's like having a knowledgeable maintainer explain the codebase to you.

Access it through mcporter: `mcporter call deepwiki.<tool> key=value`.

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| `read_wiki_structure` | List documentation topics | See what's documented about a repo |
| `read_wiki_contents` | Read the full wiki | Get a comprehensive overview |
| `ask_question` | Ask a specific question | Targeted queries about the repo |

## Calling Convention

```bash
mcporter call deepwiki.<tool_name> key=value
```

All tools take a `repoName` in `owner/repo` format (e.g. `facebook/react`).

---

## read_wiki_structure — List Documentation Topics

See what documentation topics are available for a repo. Good as a first step to understand the breadth of what's documented.

```bash
mcporter call deepwiki.read_wiki_structure repoName="vercel/next.js"
```

Use this when you want to:
- Get an overview of what aspects of a repo are documented
- Find the right section to dive into
- Understand the high-level architecture before asking specific questions

---

## read_wiki_contents — Read Full Wiki

Get the complete AI-generated documentation for a repo. This is comprehensive but can be large.

```bash
mcporter call deepwiki.read_wiki_contents repoName="denoland/deno"
```

Use this when you want to:
- Get a full overview of a project you're unfamiliar with
- Read comprehensive documentation before diving into source code
- Understand architecture, design decisions, and patterns

**Tip**: For large repos, `read_wiki_structure` first, then `ask_question` for specific topics is more efficient than reading the full wiki.

---

## ask_question — Ask Specific Questions

Ask any question about a repository and get an AI-powered, context-grounded response. This is the most useful tool — it combines understanding of the codebase with your specific question.

### Single Repo
```bash
mcporter call deepwiki.ask_question repoName="tailwindlabs/tailwindcss" question="How does the JIT compiler work internally?"
```

### Multi-Repo Query
You can ask about up to 10 repos at once by passing an array:
```bash
mcporter call deepwiki.ask_question repoName='["vercel/next.js","remix-run/remix"]' question="How do each of these frameworks handle server-side rendering?"
```

### Examples

**Understand architecture:**
```bash
mcporter call deepwiki.ask_question repoName="tokio-rs/tokio" question="What is the runtime architecture? How do tasks get scheduled?"
```

**Find implementation details:**
```bash
mcporter call deepwiki.ask_question repoName="python/cpython" question="How does the GIL work and what changes were made in Python 3.13?"
```

**Compare approaches:**
```bash
mcporter call deepwiki.ask_question repoName='["pnpm/pnpm","npm/cli"]' question="How do the dependency resolution algorithms differ?"
```

**Usage patterns:**
```bash
mcporter call deepwiki.ask_question repoName="redis/redis" question="What are the recommended patterns for using Redis as a message queue?"
```

---

## Workflow Guide

### Quick Answer
Just `ask_question` directly — it's the fastest path.

### Deep Understanding
1. `read_wiki_structure` — see what's covered
2. `ask_question` — targeted questions about areas you care about
3. Optionally `read_wiki_contents` if you want the full picture

### Comparing Repos
Use `ask_question` with an array of repos and a comparative question.

## When to Use DeepWiki vs Other Tools

| Need | Tool |
|------|------|
| Understand a GitHub repo's architecture | **deepwiki** |
| Find real code examples of an API | **code-search** (grep.app) |
| Look up library documentation | **context7** or **tavily_skill** |
| Search the web for information | **tavily_search** |
