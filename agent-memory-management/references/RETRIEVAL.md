# Retrieval & Inference Strategies

Retrieval is the "hot path" of an agent's response and must be optimized for latency (target < 200ms).

## Retrieval Dimensions

Don't rely solely on vector similarity. Use a blended score:

1.  **Relevance**: Semantic similarity to the current query.
2.  **Recency**: How recently the memory was created/updated.
3.  **Importance**: How critical the memory is (defined at generation time).

### The Scoring Triad in Practice

Projects implementing all three dimensions deliver noticeably better recall than those relying on a single dimension. A SQLite-backed system with the full triad will outperform a PostgreSQL-backed system with keyword search alone.

**Prioritize the scoring triad over storage complexity.**

You don't need vector embeddings for the full triad. LobsterAI achieves all three with SQL LIKE keyword matching, `updated_at` recency, and confidence scoring — compensating for simpler retrieval by injecting all memories into the prompt prefix.

## Retrieval Strategies by Corpus Size

### Small Corpus: Prompt-Prefix Injection (< 50 memories, < 2KB)

Inject all active memories directly into the prompt prefix of every user message. No search, no retrieval, no latency.

```
User message → buildPromptPrefix()
  ├─ <localTimeContext>current time</localTimeContext>
  └─ <userMemories>
       - User's name is John (confidence: 0.93)
       - User prefers dark mode (confidence: 0.88)
       ... (up to 12 items, 2000 chars budget, 200 chars/item)
     </userMemories>
→ Prepend to user message → LLM
```

**Why this works**: With a small memory set, all memories fit comfortably in context. Confidence scores help the LLM weigh trustworthiness. This eliminates retrieval latency entirely — no embedding calls, no index queries, no timeout concerns.

**Best for**: Personal agents, desktop apps, single-user scenarios. Enables prompt caching.

### Medium Corpus: Hybrid Search + System Prompt Injection (50–500)

Inject top-K relevant memories into the system prompt. Use hybrid (vector + keyword) retrieval.

1. On each turn, run hybrid search with the current query
2. Take top-K results by blended score
3. Inject into system prompt as structured XML
4. Report omitted count: `(+N memories omitted for brevity)`

**Best for**: Most production agents. Balances latency, cost, and recall quality.

### Large Corpus: Hybrid Search + Memory-as-a-Tool (500+)

The agent calls `memory_search` on demand. Too large to inject proactively.

1. Agent decides when to fetch memory (requires extra reasoning step)
2. Hybrid search with MMR diversification for diverse, non-redundant results
3. Return as tool output with citations (file path, line numbers)

**Best for**: Multi-agent systems, long-running agents with extensive memory history.

## Dual-Channel Retrieval (Production Pattern)

Don't choose between proactive and reactive — use both channels simultaneously:

```
┌────────────────────────────────────────────────────────┐
│  Channel A: Always-Loaded (System Prompt)              │
│  - Identity files: SOUL.md, PROFILE.md, AGENTS.md     │
│  - Hot-reloaded from disk on session reconnect         │
│  - Zero retrieval latency                              │
│  - Contains persona, not facts                         │
│                                                        │
│  + Progressive Disclosure (within Channel A):          │
│  - File tree with descriptions from frontmatter        │
│  - Agent sees WHAT exists without loading full content │
│  - Full content loaded on demand when relevant         │
│  - ~50 tokens/file for descriptions vs thousands       │
│    for full content                                    │
├────────────────────────────────────────────────────────┤
│  Channel B: On-Demand (Memory Tool)                    │
│  - Agent calls memory_search when needed               │
│  - Hybrid search over all memory files                 │
│  - Returns file paths, line numbers, content snippets  │
├────────────────────────────────────────────────────────┤
│  Channel C: Proactive (Force Search, optional)         │
│  - Auto-searches memory on every turn (1s timeout)     │
│  - Injects results into agent's long-term memory attr  │
│  - Higher availability, adds latency to every turn     │
└────────────────────────────────────────────────────────┘
```

**Channel A + B** is the recommended baseline. Add **Channel C** only when memory recall failure is costly and the latency budget allows it.

## Chunking for Embeddings

When indexing memory files for vector search, don't embed entire files. Break them into chunks:

- **Chunk size**: ~400 tokens per chunk
- **Overlap**: ~80 tokens between consecutive chunks
- **Line ranges**: Store start/end line numbers with each chunk so the agent can cite exactly where a memory came from

**Why chunk?** Long documents diluted into a single embedding lose specificity. A 3000-token file about a project's testing conventions, API design, and security rules produces a single "average" vector that matches poorly against specific queries. Chunking keeps each embedding focused.

**Overlap rationale**: 80 tokens (~20%) ensures concepts that span chunk boundaries aren't split. Queries about "testing authentication flows" might hit the boundary between a chunk ending with "authentication" and the next starting with "test strategies." Overlap gives both chunks a chance to match.

### Embedding Cache

Embedding API calls are expensive and add up quickly. Cache embeddings keyed by content hash:

```
embedding_cache (
    content_hash  TEXT PRIMARY KEY,   -- SHA-256 of chunk text
    provider      TEXT,               -- e.g., "openai", "ollama"
    model         TEXT,               -- e.g., "text-embedding-3-small"
    embedding     BLOB                -- float32 array
)
```

**Sync workflow**: During incremental sync, hash each chunk's text. If the hash exists in the cache with the same provider+model, reuse the embedding. Only call the embedding API for new or changed chunks.

**Re-index trigger**: If the embedding provider, model, or chunk size changes, detect the mismatch in metadata and rebuild the entire index. Do this safely by building into a temporary database, then atomically swapping it into place.

## Hybrid Search

Don't choose between keyword and semantic search — use both. Users sometimes search with exact terms ("project Aurora") and sometimes with conceptual queries ("that thing we discussed about the deployment").

### Candidate Multiplier

For hybrid fusion to work well, fetch more candidates than the final result count:

- **Multiplier**: 4× the requested result count (e.g., if the agent asks for 6 results, fetch 24 from each search method)
- **Why**: Fusion can only surface documents that appear in at least one search's candidate set. A low recall from one method gets rescued by the other only if the document is in the candidate pool.
- **Cap**: Hard cap at 200 candidates total to prevent excessive latency.

### Minimum Score Threshold

After fusion and sorting, filter results below a relevance floor:

- **Default threshold**: 0.35
- **Rationale**: Below this, results are typically noise — vaguely related concepts that don't actually answer the query.
- **Tuning**: Raise to 0.50 for high-stakes domains (medical, legal) where false positives are costly. Lower to 0.25 for exploratory retrieval where breadth matters.

### Reciprocal Rank Fusion (RRF)

Combines results from multiple search methods by rank position:

```
score(d) = Σ 1/(k + rank(d))   for each method where d appears
```

- `k = 60` (default constant, prevents rank-1 from dominating)
- Documents appearing in both FTS and vector results get boosted scores
- Normalize final scores to 0–1 range
- Filter by minimum score threshold

**Best for**: General-purpose retrieval where both methods should contribute equally.

### Weighted Score Fusion

Combines normalized scores from each method with configurable weights:

```
finalScore = vectorWeight × vectorScore + textWeight × textScore
```

- Default: 70% vector + 30% text (semantic understanding matters more)
- Tunable per application: increase text weight for exact-match domains

**Best for**: Applications where semantic understanding is primary but exact matches still matter.

### BM25 Text Scoring

For the text component of hybrid search, BM25 provides better term-frequency scoring than simple keyword matching:

```
base_score = hit_terms / total_query_terms
phrase_bonus = 0.2 (for complete multi-word phrase matches)
score = min(1.0, base_score + phrase_bonus)
```

**Fusion with vector results**:
```
vector_only:  final = vector_score × 0.7
bm25_only:    final = bm25_score × 0.3
both:         final = vector_score × 0.7 + bm25_score × 0.3
```

### Fallback Chain

When vector search is unavailable (no embedding provider, startup, degraded mode):

1.  **Keyword-only**: Tokenize query, match against memory content, rank by match count.
2.  **File scan**: For file-based systems, scan memory files directly.
3.  **Load all**: For small memory corpora, inject everything and let the LLM filter.

## Temporal Decay

Recent memories are more likely to be relevant. Apply exponential decay:

```
decayedScore = originalScore × exp(-λ × age_in_days)
where λ = ln(2) / half_life_days
```

- **Default half-life**: 30 days (configurable)
- A 30-day-old memory retains 50% of its score; 60-day-old retains 25%
- Combine with the scoring triad: `finalScore = relevance × decay × importance`

## MMR Diversification

After initial ranking, results can cluster around a single topic. Maximal Marginal Relevance (MMR) re-ranks to promote diversity:

```
MMR(item) = λ × relevance(item) − (1−λ) × max_similarity(item, selected)
```

- `λ = 0.7` (default): 70% relevance, 30% diversity
- `λ = 0.0`: Maximum diversity (may surface irrelevant results)
- `λ = 1.0`: Maximum relevance (equivalent to no MMR, may surface redundant results)
- Applied greedily: select the highest-MMR item, add to results, repeat

**Best for**: Top-k retrieval where you want diverse, non-redundant results.

## Placement for Inference

| Placement | Best For | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **System Instructions** | Stable, global facts (User Profile) | High authority, clean history | Risk of "over-influence" |
| **Prompt Prefix** | All active memories (small corpus) | Zero latency, enables caching | Doesn't scale past ~50 memories |
| **Conversation History** | Transient, episodic facts | Flexible, "in-the-moment" | Can be noisy, increases token cost |
| **Tool Output** | Specific data lookups | Precise, on-demand | Requires tool-use capability |

### Placement Selection Guide

| Memory Size | Retrieval Method | Placement | Rationale |
|:---|:---|:---|:---|
| Small (< 50 memories) | Load all | Prompt prefix | Zero latency, enables prompt caching |
| Medium (50–500) | Hybrid search | System prompt (top-K) | Inject most relevant K memories |
| Large (500+) | Hybrid + MMR | Memory-as-a-tool | Too large to inject proactively |

## Timing for Retrieval

- **Proactive (Force Search)**: Load memories automatically at the start of every turn (1s timeout). Higher availability but adds latency to every turn. Best for high-stakes recall.
- **Reactive (Memory-as-a-Tool)**: The agent calls `memory_search` only when it needs more context. More efficient but requires an extra LLM reasoning step. Best for most use cases.
- **Always-Loaded**: Identity and persona files always in system prompt. Zero runtime cost but limited to a fixed set of files. Recommended baseline for all systems.

## Memory Injection Guardrails

When inserting retrieved memories into the agent's working context, follow these rules to prevent memory from hijacking the agent's reasoning:

### Stale Marker

Always prepend injected memory with a stale/incomplete warning:

```
The following memory may be stale or incomplete. Prefer current context
if there is any contradiction:

- User prefers dark mode (learned 3 days ago)
- Project uses Bun instead of npm (learned 2 months ago)
```

This framing prevents the agent from treating aged memories as ground truth. It mirrors how a human treats notes from last month — useful context, but verify against current reality.

### Precedence Rules

Establish a clear hierarchy for conflicting information:

1. **Current user message** > **Recent tool output** > **Injected memory** > **System instructions**
2. If memory contradicts the user's explicit current statement, ignore the memory.
3. If two memories conflict, prefer the one with the more recent `updated_at` timestamp.
4. If timestamps are similar, prefer the memory with higher confidence score.

### Overweighting Prevention

Memory should augment, not drown, the current task:

- **Small corpus** (< 50 memories): Inject everything. No risk of overweighting.
- **Medium corpus** (50–500): Budget ~2000 characters for memory in the system prompt. Report omitted count: `(+N memories omitted for brevity)`.
- **Large corpus** (500+): Use memory-as-a-tool. The agent explicitly requests what it needs, so injection is bounded by `maxResults`.

### Format for Injection

Structure injected memory to help the agent calibrate trust:

```
[Memory: project/testing.md:12-18 | score: 0.87 | age: 3 days]
Run `pnpm test` after modifying business logic. Keep test files co-located
with the code they test.

[Memory: user/preferences.md:5-8 | score: 0.92 | age: 2 months]
User prefers compact code — collapse duplicate else branches, avoid
unnecessary nesting.
```

Each entry includes:
- **Source**: file path and line range (enables citation)
- **Score**: fusion score (helps the agent assess relevance)
- **Age**: how long ago the memory was learned (helps assess staleness)

## Optimization Techniques

- **Query Rewriting**: Use an LLM to expand ambiguous user queries into precise search terms.
- **Reranking**: Fetch the top 50 results via similarity, then use a smaller model to rerank the top 5.
- **Caching**: Store the results of expensive retrieval queries for identical subsequent turns.
- **Embedding Cache**: SHA-256 keyed LRU cache for embedding vectors (~58MB for 10K entries).
- **Incremental Indexing**: Track file hashes and mtimes to only reindex changed content.
- **File Watcher**: Monitor memory files for changes and asynchronously update the search index.
- **Expansion Pool**: Fetch 4× candidate pool (capped at 200) before fusion, then take top-K from fused results. Improves recall without increasing final result size.

## Token Budgets

When injecting memories into context, apply a token budget to prevent memory from consuming the entire context window:

1.  Estimate tokens per memory: `(content_length / 4) + 10` (rough approximation)
2.  Sort by blended score (relevance × recency × importance)
3.  Inject memories until the budget is reached
4.  Report omitted count to the LLM: `(+N memories omitted for brevity)`

**Budget guidelines**:
- Small corpus: No budget needed — inject everything
- Medium corpus: ~2000 characters budget for memories in system prompt
- Large corpus: Per-query budget controlled by `maxResults` parameter

## Citations

When returning memory search results, include provenance information:

- **File path**: Which memory file the result came from
- **Line range**: Start and end line numbers
- **Source type**: `"memory"` or `"sessions"` (session transcripts)
- **Snippet**: The matching text content

Citations help the LLM assess the reliability and recency of retrieved information. Auto-suppress citations in group/channel contexts where they'd be noisy.
