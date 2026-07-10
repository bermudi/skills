---
name: agent-memory-management
description: Framework for building stateful AI agents using Sessions (short-term history) and Memory (long-term persistence) — memory filesystem design, versioned storage, progressive disclosure, multi-agent memory coordination, and the full lifecycle from extraction through retrieval. Invoked explicitly.
license: Apache-2.0
metadata:
  version: "3.1"
  topic: context-engineering
disable-model-invocation: true
---

# Agent Memory & Session Management

A framework for **Context Engineering** — dynamically assembling information within an LLM's context window to create stateful, personalized AI experiences.

> **Validated against 9 production agent implementations** (IronClaw, MicroClaw, Nanobot, NanoClaw, OpenClaw, OpenFang, PicoClaw, CoPaw, LobsterAI). Patterns below reflect what actually works in practice, not just theory.

## Architecture Selection Guide

Choose your memory architecture based on your constraints, not your ambitions.

| Constraint | Architecture | Storage | Retrieval | Proven Examples |
|:---|:---|:---|:---|:---|
| **Personal agent, human-readability matters** | File-first + optional vector index | JSONL + Markdown | File scan → hybrid search when needed | Nanobot, PicoClaw, CoPaw |
| **Single-agent production, structured queries needed** | SQLite-backed | SQLite (WAL) + optional sqlite-vec | Hybrid (vector + FTS/BM25) | MicroClaw, OpenClaw, OpenFang |
| **Multi-agent production, high concurrency** | Database-backed | PostgreSQL + pgvector | Hybrid (RRF) | IronClaw |
| **Multi-tenant, security-critical** | Container-isolated | SQLite per container + hierarchical MD | SDK-native + tool-based | NanoClaw |
| **Desktop app, cost-sensitive** | SQLite + prompt-prefix injection | SQLite + MEMORY.md compatibility | Load all memories into prompt | LobsterAI |
| **Multi-channel deployment (WhatsApp, Discord, etc.)** | File-first + pluggable search | Markdown + ReMeLight (ChromaDB/SQLite) | Dual-channel (always-loaded + on-demand) | CoPaw |

**Rule of thumb**: Start with file-based (JSONL + Markdown). Scale to SQLite when you need structured queries. Reserve PostgreSQL for multi-agent workloads. The ETL pipeline quality matters more than the storage backend. **Version your memory store** — whether you use git, a changelog table, or event sourcing, every mutation should be traceable. This enables rollback, audit, and concurrent write coordination (critical for multi-agent systems).

## Core Concepts

```
┌─────────────────────────────────────────────────────────┐
│                    Context Window                        │
│                                                          │
│  ┌──────────────────┐   ┌────────────────────────────┐  │
│  │   Session ("Now")│   │  Memory ("Always")         │  │
│  │                  │   │                             │  │
│  │  Events (log)    │   │  Extraction                 │  │
│  │  State (scratch) │──▶│  Consolidation              │  │
│  │  Compaction      │   │  Provenance                 │  │
│  └──────────────────┘   └──────────────┬──────────────┘  │
│                                         │                │
│                          ┌──────────────▼──────────────┐ │
│                          │  Retrieval ("Inference")    │ │
│                          │                             │ │
│                          │  Relevance (semantic sim)   │ │
│                          │  Recency (time decay)       │ │
│                          │  Importance (significance)  │ │
│                          └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Memory Taxonomy

Separate two fundamentally different kinds of memory. Mixing them causes behavior drift:

- **Instruction memory**: Human-written rules that tell the agent how to work — coding standards, directory conventions, build commands, naming conventions, safety rules. These are stable, version-controlled, and loaded at session start. Equivalent to `AGENTS.md` / `CLAUDE.md` / `.cursorrules`.
- **Learning memory**: Accumulated by the agent over time from corrections, preferences, failed attempts, common commands, and project habits. These evolve and may be stale.

**Rule**: Write rules, policies, and behavioral constraints into instruction memory. Write experience, preferences, temporary discoveries, and retrospective takeaways into learning memory.

**Memory scopes** — define who owns it, who shares it, and who it applies to:

| Scope | Storage | Examples | Commit to Git? |
|:---|:---|:---|:---|
| **Organization** | System-level path (`/etc/system.md`, MDM, Ansible) | Security requirements, compliance, baseline code review standards | No — distributed centrally |
| **Project** | Repo root (`AGENTS.md`, `.claude/rules/`) | Architecture docs, build/test commands, naming conventions, API layout | Yes |
| **User** | Home dir (`~/.config/devin/`, `~/.claude/`) | Personal coding style, preferred debugging sequence, output format | No — personal |
| **Local** | Working copy (`local.md`) | Test accounts, dev ports, mock endpoints, machine-specific notes | No — `.gitignore` |
| **Role / Subagent** | Per-agent memory dir | Testing agent remembers CI behavior; refactoring agent remembers module boundaries | Optional |

Keep the main instruction file under 200 lines. Split specialized rules into modular files (`testing.md`, `api-design.md`, `security.md`) and scope them to specific subdirectories or file types so they load only when needed.

## Memory Filesystem Design

When you choose a file-based memory architecture, the filesystem structure is your primary design lever. Getting this right determines how efficiently agents can store, discover, and update knowledge.

### Three-Tier Memory Layout

Organize memory into three tiers based on access frequency and cost:

| Tier | Location | When to Load | Content |
|:---|:---|:---|:---|
| **System** | `system/` | Every turn, pinned in system prompt | Identity, persona, project conventions, critical facts. Reserve for durable, high-signal knowledge that helps across sessions. |
| **Progressive** | Outside `system/` | On demand — descriptions always visible, content loaded when relevant | Historical records, large reference material, transient notes. The agent sees file descriptions (from frontmatter) and loads full content only when needed. |
| **Recall** | Session logs / message history | Searchable via tools | Full conversation history. Even after messages leave the context window, they should be searchable by a recall tool or subagent. |

The key insight: **descriptions are cheap, content is expensive**. A tree of file descriptions costs ~50 tokens per file. Loading the full content of every file every turn costs thousands. Progressive disclosure lets the agent know *what exists* without paying for *everything*.

### Structured File Format

Use Markdown with YAML frontmatter for every memory file:

```yaml
---
description: One-line summary used for progressive disclosure (always visible)
limit: 5000          # max characters — prevents unbounded growth
read_only: false     # set by system; agents cannot modify read_only files
---

Memory content in markdown. Keep focused — one concept per file.
```

- **`description`** is the progressive disclosure hook. Write it so an agent can decide whether to load the full file based on the description alone.
- **`limit`** enforces a size cap. When a file exceeds its limit, split it or extract the less-critical content to a progressive-tier file.
- **`read_only`** protects files that shouldn't be modified by the agent (e.g., system-level configuration, user-authored identity files). Only the orchestrator or human should set this.

### Hierarchical Organization

Structure memory files into a focused hierarchy, not a flat pile:

- **15–25 files** at steady state — enough to cover distinct concerns without overwhelming discovery.
- **2–3 levels of nesting** using path separators (e.g., `project/tooling/testing.md`).
- **~40 lines max per file** — split aggressively when a file covers 2+ concepts.
- **Descriptive paths** — the filename alone should signal what's inside.

Example target structure:
```
system/
├── human/
│   ├── identity.md
│   ├── preferences/
│   │   ├── communication.md
│   │   └── coding_style.md
│   └── context.md
├── project/
│   ├── overview.md
│   ├── gotchas.md
│   ├── architecture.md
│   └── tooling/
│       ├── testing.md
│       └── linting.md
└── persona/
    ├── role.md
    └── behavior.md
reference/              ← progressive tier (not pinned)
├── api-conventions.md
└── deployment-history.md
```

### Versioned Storage

Track every change to memory with a version control system (git is the natural choice for file-based memory):

- **Informative commit messages**: Every write should describe *what* changed and *why* (e.g., `"feat: add user deployment preferences"`, `"fix: correct API base URL after migration"`).
- **Auditability**: You can inspect the history of any fact — when it was added, modified, or removed.
- **Rollback**: If a bad extraction poisons memory, revert to a known-good state.
- **Diff-based sync**: When memory is synced between processes or machines, diffs are smaller and more efficient than full copies.

This is especially critical for multi-agent systems where concurrent writes need coordination (see Multi-Agent Memory Coordination below).

## Context Failure Modes

Long-running agents degrade when context is mismanaged. Four failure modes to monitor and mitigate: **Context Burst**, **Context Conflict**, **Context Poisoning**, and **Context Noise**. For the full failure-mode/mitigation table, read `references/SESSIONS.md` ("Context Failure Modes to Monitor").

**Prevention**: Set context thresholds at 40–80% of the window limit — do not wait until the hard limit. Track token allocation across system instructions, tool definitions, retrieved knowledge, and conversation history.

## Implementation Workflow

### 1. Manage the Session (The "Now")

> **Implementing session compaction?** Read `references/SESSIONS.md` first — it owns the full tiered-compaction table (70/75/85/95% escalation), tool-armed summarization, summary-prompt templates, crash recovery, and fallback chains.

- **Capture Events**: Record every user input, model response, tool call, and tool output.
- **Tiered Compaction**: Escalate through four tiers as context pressure rises — truncate old tool outputs (70–75%), move facts to long-term memory (75–85%), summarize (85–95%), then truncate oldest messages (95%+, last resort). For the full tier-escalation table and rationale, read `references/SESSIONS.md` ("Tiered Compaction").
- **Tool-Armed Summarization**: Give the summarizer `read_file`/`write_file`/`edit_file` tools so it actively persists important information during compaction — not just compresses. This turns compaction into a memory-persistence step.
- **User-Turn Boundaries**: Only compact at user-turn boundaries to avoid splitting tool-call/tool-result pairs.
- **Fallback Strategy**: Always have a degradation path (raw-archive after N summarization failures).

### 2. Generate Memory (The "Always")

Memory generation is an **ETL pipeline** — the quality of this pipeline differentiates good systems from great ones more than the storage backend.

#### Extraction (Three-Stage Pipeline)

The most cost-efficient approach processes most memories without any LLM call:

```
Stage 1: Regex/Pattern Extraction (near-zero cost, real-time)
    ↓ candidates
Stage 2: Rule-Based Scoring (fast, no LLM)
    ↓ borderline cases only
Stage 3: LLM Judge (expensive, optional escalation)
    ↓ validated memories → persist
```

- **Background Reflector**: Dedicated loop (e.g., every 60 minutes) extracts facts from recent conversations without blocking the user. Best for always-on fact extraction.
- **Auto-Capture**: Pattern matching extracts structured memories (preferences, facts, decisions) without LLM calls — lower cost, always-on.
- **Explicit Command**: User says "remember that X" — bypasses pipeline, stored at high confidence (0.95+).
- **Categories**: Tag memories with types (`PROFILE`, `KNOWLEDGE`, `EVENT`) to enable targeted retrieval.

#### Consolidation

- **Near-Duplicate Detection**: Use multi-signal similarity without requiring vector embeddings:
    - Token overlap (min-normalized word frequency)
    - Character bigram Dice coefficient
    - Substring containment ratio
    - Threshold: 0.82 — above this, merge candidates.
- **Conflict Resolution**: When a new memory contradicts an existing one, prefer the newer one if its confidence is higher. If confidence is similar, prefer explicit user input over inferred knowledge.
- **Confidence Scoring**: Assign a confidence score (0–1) to each memory. Decay confidence for memories not accessed in 7+ days.

#### Memory Defragmentation

Over long-horizon use, memory files inevitably become disorganized — files grow too large, hierarchies flatten, related facts end up scattered across files. Periodic defragmentation restructures memory back to a clean state:

- **Trigger**: Run when file count exceeds 25, any single file exceeds ~40 lines, or on a fixed schedule (e.g., weekly for long-running agents).
- **Split oversized files**: If a file covers multiple concepts, extract each into its own file with a descriptive path.
- **Merge scattered facts**: If related information is spread across multiple files, consolidate into a single focused file.
- **Restructure hierarchy**: Reorganize paths when the current structure no longer reflects the agent's working patterns.
- **Backup first**: Always snapshot the memory directory before defragmentation (e.g., copy to `memory-backup-<timestamp>/`).
- **Background execution**: Run defragmentation in an isolated workspace (a separate git branch or directory) so the main agent is not blocked. Merge changes back when complete.

This is distinct from consolidation (which handles duplicates and conflicts at the record level). Defragmentation operates at the *file structure* level — it's about the shape of your memory filesystem, not the content of individual records.

#### Anti-Poisoning

> **Defining rejection rules or guard levels?** Read `references/MEMORY.md` ("Anti-Poisoning Guards" and "Guard Levels") — it owns the full reject list and the strict/standard/relaxed threshold table.

Filter aggressively before information becomes "fact": reject small talk, greetings, hedged statements, contradictions of high-confidence memories, sub-minimum-length content, agent-directed remarks, and procedural text. Offer configurable guard levels (`strict` / `standard` / `relaxed`) to control the false-positive vs. false-negative tradeoff.

#### Provenance

Track where every memory came from — and detect when the source disappears:

- **Source Tracking**: Link each memory to its originating session and message (session_id, message_id, role).
- **Orphan Detection**: When sessions are deleted, mark orphaned implicit memories as stale. Prevents dead facts from persisting indefinitely.
- **Self-Healing**: At startup, auto-purge procedural commands and workflow instructions that were accidentally stored.

See [Memory Lifecycle Deep-Dive](references/MEMORY.md) for extraction and consolidation logic.

### 3. Retrieve and Inject (The "Inference")

Retrieval strategy depends on your memory corpus size. The scoring triad (Relevance + Recency + Importance) is the frontier — projects implementing all three deliver noticeably better recall.

| Corpus Size | Strategy | When to Use |
|:---|:---|:---|
| **Small** (< 50 memories, < 2KB) | **Prompt-prefix injection** | Inject all memories into every prompt. Zero latency, enables prompt caching. |
| **Medium** (50–500) | **Hybrid search + system prompt injection** | Inject top-K relevant memories into system prompt. Hybrid (vector + keyword) retrieval. |
| **Large** (500+) | **Hybrid search + memory-as-a-tool** | Agent calls `memory_search` on demand. Hybrid + MMR for diversity. |

#### Dual-Channel Retrieval (Production Pattern)

Don't choose between proactive and reactive — use both:

1. **Channel A (Always)**: Identity and persona files (SOUL.md, PROFILE.md, AGENTS.md) always in system prompt. Hot-reloaded from disk on session reconnect.
2. **Channel B (On-Demand)**: `memory_search` tool for specific queries. Hybrid search with weighted fusion.
3. **Channel C (Proactive, optional)**: Force memory search on every turn with timeout (1s). Auto-injects results without agent reasoning. Useful for high-availability scenarios.

#### Scoring Triad

> **Defining retrieval scoring?** Read `references/RETRIEVAL.md` ("Retrieval Dimensions") — it owns the full Relevance + Recency + Importance rationale.

Rank memories by blending **Relevance** (semantic similarity or keyword match), **Recency** (temporal decay: `score × exp(-λ × age_days)` where `λ = ln(2) / half_life`, default half-life 30 days), and **Importance** (a 0–1 weight assigned at generation; confidence and guard levels serve as proxies). Projects implementing all three outperform single-dimension retrieval.

#### Hybrid Search Fusion

Combine keyword (FTS/BM25) and semantic (vector) search:

- **Reciprocal Rank Fusion (RRF)**: `score(d) = Σ 1/(k + rank(d))` across both methods. Best for general-purpose retrieval where both methods should contribute equally.
- **Weighted Fusion**: `finalScore = 0.7 × vectorScore + 0.3 × textScore`. Best when semantic understanding is primary but exact matches still matter.
- **MMR Diversification**: After ranking, apply Maximal Marginal Relevance to avoid redundant results: `MMR = λ × relevance − (1−λ) × max_similarity_to_selected`. Best for top-k retrieval where diversity matters.

See [Retrieval & Inference Strategies](references/RETRIEVAL.md) for fusion algorithms and placement details.

### 4. Initialize Memory (The Cold Start)

A new agent starts with empty memory. Cold-starting well determines how useful the agent is from its first interaction.

#### Bootstrap from Codebase

If the agent operates within a specific project, scan the codebase to generate initial memory:

- **Project structure**: Map the directory layout, key entry points, and architectural patterns.
- **Conventions**: Extract coding style, testing patterns, dependency management, and CI/CD configuration.
- **Gotchas**: Flag footguns, deprecated patterns, and known issues from comments and documentation.
- **Tooling**: Document build commands, test runners, linters, and deployment steps.

Fan out across concurrent workers for large codebases — each worker processes a subset of files, then results are merged back.

#### Bootstrap from Conversation History

If the agent has access to prior conversation logs (from previous tools, exported histories, or user-provided context):

- **Process in parallel**: Split history into time-based slices and extract facts concurrently.
- **Extract preferences, decisions, and facts**: Run the three-stage extraction pipeline over each slice.
- **Merge into hierarchy**: Deduplicate across slices and organize results into the hierarchical structure.

#### Target State

Aim for 15–25 files organized in 2–3 levels of hierarchy (see Memory Filesystem Design above). Cover: identity/preferences, project context, conventions, gotchas, and persona. Start with `system/` files for always-visible knowledge, then add progressive-tier files for reference material.

## Best Practices

- **Strict Isolation**: Scope memories per-user (or per-conversation). Container-level isolation is the gold standard (NanoClaw); per-agent filesystem isolation is the pragmatic production pattern (CoPaw); application-level database scoping is the minimum (MicroClaw, OpenFang).
- **Multi-Agent Memory Coordination**: When multiple agents or subagents write to shared memory concurrently, isolate writes and merge explicitly. Use separate branches/worktrees for each writer — each agent gets an independent copy to modify, then merges back through a coordination step. For versioned (git-backed) stores, this is natural: branch per agent, merge with conflict resolution. For database-backed stores, use optimistic concurrency with per-row version tracking. When both agents modify the same content, prefer the write with higher confidence or more recent provenance.
- **Versioned Memory**: Treat memory mutations like you'd treat data mutations in a production system — track them. Git-based versioning works for file stores; changelog tables or event sourcing work for databases. Every write should carry a message describing what changed and why. This pays for itself the first time you need to answer "when did we start believing X?" or revert a bad extraction.
- **PII Redaction**: Redact sensitive information before persisting. This is a universal blind spot — zero out of nine analyzed implementations do it well. Treat it as a first-class requirement, not an afterthought.
- **Asynchronous Processing**: Run memory extraction in the background. A dedicated reflector loop is the gold standard (MicroClaw); async queued extraction after each turn is the cost-efficient approach (LobsterAI); tool-armed background summarization is the most memory-productive approach (CoPaw).
- **Anti-Poisoning**: Filter noise before it becomes memory. Use guard levels to let users control the strictness/coverage tradeoff.
- **Graceful Degradation**: Always have a fallback when compaction or summarization fails — raw archive, truncation, or read-only mode.
- **File-First When Possible**: Plain Markdown is human-readable, git-friendly, and has zero vendor lock-in. Add a pluggable vector/FTS index layer on top (like ReMeLight) when you need semantic search, keeping files as the source of truth. When you use git for versioning, agents can manage memory using their full terminal capabilities — bash for batch operations, scripts for programmatic processing, and standard git workflows for coordination.

### Memory Guardrails for Injection

When injecting retrieved memory back into the agent's context, mark it as auxiliary — not authoritative:

- **Stale marker**: Prepend injected memory with `"The following memory may be stale or incomplete:"`. This prevents the agent from treating aged memories as ground truth.
- **Precedence rule**: Live context (user's current message, recent tool outputs) always overrides injected memory. If a memory contradicts current context, prefer current context.
- **Avoid overweighting**: Do not stuff so much memory into the system prompt that it drowns out current task instructions. Use token budgets (~2000 characters for medium corpora).
- **No secrets in memory**: Memory files are not vaults. Never store API keys, passwords, or tokens in learning memory. Use environment variables or a secrets manager instead.
- **Temporal tagging**: Include `created_at` and `updated_at` on every memory. When injecting, sort by recency and annotate age (e.g., `"(3 days ago)"`). This helps the agent calibrate trust. See [Memory Lifecycle Deep-Dive](references/MEMORY.md) for CJK bigram tokenization and bilingual extraction patterns.
