---
name: agent-memory-management
description: Implements stateful AI agents using Sessions (short-term history) and Memory (long-term persistence). Use this skill when building agents that need to remember user preferences, track multi-turn state, or maintain context across different interactions.
license: Apache-2.0
metadata:
  version: "3.0"
  topic: context-engineering
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

**Rule of thumb**: Start with file-based (JSONL + Markdown). Scale to SQLite when you need structured queries. Reserve PostgreSQL for multi-agent workloads. The ETL pipeline quality matters more than the storage backend.

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

## Implementation Workflow

### 1. Manage the Session (The "Now")

- **Capture Events**: Record every user input, model response, tool call, and tool output.
- **Tiered Compaction**: Escalate through tiers based on context pressure:
    1. **Tool Output Truncation** (70–75% full): Truncate old tool outputs (3KB cap), preserve recent (50KB). Cheapest tier.
    2. **Move to Workspace** (75–85% full): Extract key facts to long-term memory; keep recent turns verbatim.
    3. **Summarize** (85–95% full): LLM summarizes older messages, prefix summary before recent turns.
    4. **Truncate** (95%+): Drop oldest messages entirely. Last resort.
- **Tool-Armed Summarization**: Give the summarizer `read_file`/`write_file`/`edit_file` tools so it actively persists important information during compaction — not just compresses. This turns compaction into a memory-persistence step.
- **User-Turn Boundaries**: Only compact at user-turn boundaries to avoid splitting tool-call/tool-result pairs.
- **Fallback Strategy**: Always have a degradation path (raw-archive after N summarization failures).

See [Session Management Details](references/SESSIONS.md) for compaction strategies.

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

#### Anti-Poisoning

Filter aggressively before information becomes "fact":

**Reject if:**
- Small talk, greetings, hedged statements
- Contradictions of established high-confidence memories (flag for review instead)
- Content below minimum length threshold (< 10 characters)
- Statements about the agent itself ("you're helpful", "you made a mistake")
- Questions or procedural text (commands, scripts)

**Guard Levels**: Offer configurable strictness to control false-positive vs. false-negative tradeoff:
- `strict`: Higher thresholds, fewer but higher-quality memories
- `standard`: Balanced (default)
- `relaxed`: Lower thresholds, more memories but potentially noisier

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

1. **Relevance**: Semantic similarity (vector embeddings) OR keyword match (SQL LIKE / FTS). Vector is better for conceptual queries; keyword is better for exact terms.
2. **Recency**: Temporal decay: `score × exp(-λ × age_days)` where `λ = ln(2) / half_life`. Default half-life: 30 days.
3. **Importance**: Significance weight (0–1) assigned at generation time. Confidence scores and guard levels serve as importance proxies.

#### Hybrid Search Fusion

Combine keyword (FTS/BM25) and semantic (vector) search:

- **Reciprocal Rank Fusion (RRF)**: `score(d) = Σ 1/(k + rank(d))` across both methods. Best for general-purpose retrieval where both methods should contribute equally.
- **Weighted Fusion**: `finalScore = 0.7 × vectorScore + 0.3 × textScore`. Best when semantic understanding is primary but exact matches still matter.
- **MMR Diversification**: After ranking, apply Maximal Marginal Relevance to avoid redundant results: `MMR = λ × relevance − (1−λ) × max_similarity_to_selected`. Best for top-k retrieval where diversity matters.

See [Retrieval & Inference Strategies](references/RETRIEVAL.md) for fusion algorithms and placement details.

## Best Practices

- **Strict Isolation**: Scope memories per-user (or per-conversation). Container-level isolation is the gold standard (NanoClaw); per-agent filesystem isolation is the pragmatic production pattern (CoPaw); application-level database scoping is the minimum (MicroClaw, OpenFang).
- **PII Redaction**: Redact sensitive information before persisting. This is a universal blind spot — zero out of nine analyzed implementations do it well. Treat it as a first-class requirement, not an afterthought.
- **Asynchronous Processing**: Run memory extraction in the background. A dedicated reflector loop is the gold standard (MicroClaw); async queued extraction after each turn is the cost-efficient approach (LobsterAI); tool-armed background summarization is the most memory-productive approach (CoPaw).
- **Anti-Poisoning**: Filter noise before it becomes memory. Use guard levels to let users control the strictness/coverage tradeoff.
- **Graceful Degradation**: Always have a fallback when compaction or summarization fails — raw archive, truncation, or read-only mode.
- **File-First When Possible**: Plain Markdown is human-readable, git-friendly, and has zero vendor lock-in. Add a pluggable vector/FTS index layer on top (like ReMeLight) when you need semantic search, keeping files as the source of truth.
- **Bilingual Awareness**: If your users are multilingual, ensure extraction patterns, tokenization, and deduplication work across languages. CJK bigram tokenization and bilingual regex patterns are validated patterns.
