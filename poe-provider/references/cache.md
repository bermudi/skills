# Prompt Caching on Poe

Poe supports prompt caching, but **only through provider-native endpoints**. Cache hits and misses are reflected in both the response `usage` object and the `cost_breakdown_in_points` field in `points_history`.

Tested 2026-04-13 against live Poe APIs.

---

## TL;DR

| Model | `/v1/messages` | `/v1/chat/completions` | `/v1/responses` |
|---|:---:|:---:|:---:|
| `claude-haiku-4.5` | ✅ | ❌ | ❌ |
| `gpt-5.4-mini` | ❌ broken | ✅ | ✅ |

**Rule of thumb:** use the endpoint that matches the model's native provider — Anthropic Messages for Claude, OpenAI Chat Completions / Responses for GPT. Cross-provider endpoints don't currently surface prompt caching.

---

## How caching works per provider

### Anthropic (Claude models) — `/v1/messages`

Poe passes `cache_control` through to Anthropic. The Anthropic prompt caching spec applies:

- Place `cache_control: {"type": "ephemeral"}` on content blocks you want to cache
- Up to 4 cache breakpoints per request
- Minimum cacheable prompt: **4096 tokens** for Haiku 4.5
- 5-minute TTL by default; refreshed on each cache hit
- 1-hour TTL available at 2× write cost: `{"type": "ephemeral", "ttl": "1h"}`

**Usage fields** in the response:

```json
{
  "usage": {
    "input_tokens": 17,
    "cache_creation_input_tokens": 8352,
    "cache_read_input_tokens": 0,
    "cache_creation": {
      "ephemeral_5m_input_tokens": 8352,
      "ephemeral_1h_input_tokens": 0
    },
    "output_tokens": 4
  }
}
```

| Field | Meaning |
|-------|---------|
| `input_tokens` | Tokens **after** the last cache breakpoint (uncached) |
| `cache_creation_input_tokens` | Tokens being written to cache (first request or cache miss) |
| `cache_read_input_tokens` | Tokens read from cache (cache hit) |

**Points billing** from `points_history`:

| Phase | Example breakdown |
|-------|-------------------|
| Cache write | `Input: 238 pts` + `Cache write: 60 pts` + `Output: 1 pt` = **299 pts** |
| Cache read | `Input: 238 pts` + `Output: 1 pt` + `Cache discount: −213 pts` = **26 pts** |

The `Cache discount` line only appears on cache hits. The `Cache write` line only appears on cache misses.

**How to enable:**

```bash
curl -X POST "https://api.poe.com/v1/messages" \
  -H "x-api-key: $POE_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-haiku-4.5",
    "max_tokens": 1024,
    "system": [
      {
        "type": "text",
        "text": "...large static context...",
        "cache_control": {"type": "ephemeral"}
      }
    ],
    "messages": [{"role": "user", "content": "Your question"}]
  }'
```

### OpenAI (GPT models) — `/v1/chat/completions` and `/v1/responses`

Poe's OpenAI-style endpoints surface automatic prompt caching. No `cache_control` is needed — caching kicks in automatically when the prompt prefix is **≥1024 tokens** and the same prefix was recently processed.

**Usage fields** in Chat Completions responses:

```json
{
  "usage": {
    "prompt_tokens": 7661,
    "completion_tokens": 5,
    "prompt_tokens_details": {
      "cached_tokens": 7424
    }
  }
}
```

**Usage fields** in Responses API responses:

```json
{
  "usage": {
    "input_tokens": 7657,
    "output_tokens": 5,
    "input_tokens_details": {
      "cached_tokens": 7424
    }
  }
}
```

| Field | Meaning |
|-------|---------|
| `prompt_tokens` / `input_tokens` | Total input tokens |
| `cached_tokens` | Tokens served from cache |
| Implicit uncached | `prompt_tokens - cached_tokens` |

**Points billing** from `points_history`:

| Phase | Example breakdown |
|-------|-------------------|
| Cache miss | `Input: 173 pts` + `Output: 1 pt` = **174 pts** |
| Cache hit | `Input: 173 pts` + `Output: 1 pt` + `Cache discount: −150 pts` = **24 pts** |

---

## Pricing model

Poe's `/v1/models` endpoint includes cache pricing per token in USD:

```json
{
  "id": "claude-haiku-4.5",
  "pricing": {
    "prompt": "0.00000085",
    "completion": "0.0000043",
    "input_cache_read": "0.000000085",
    "input_cache_write": "0.0000011"
  }
}
```

| Field | Meaning |
|-------|---------|
| `prompt` | Base input token price |
| `completion` | Output token price |
| `input_cache_read` | Price per cached token on read (cache hit) |
| `input_cache_write` | Price per cached token on write (cache miss) — `null` for some models |

**Discount ratios** (from pricing or Poe UI cards):

| Model | Cache read discount |
|-------|-------------------:|
| `claude-haiku-4.5` | **90%** off input (`0.085 / 0.85`) |
| `gpt-5.4-mini` | **90%** off input (`0.068 / 0.68`) |
| `glm-5.1-fw` | **81%** off input (`0.26 / 1.40`) |
| `minimax-m2.7` | **80%** off input (`0.06 / 0.30`) |
| `kimi-k2.5` | **83%** off input (`0.10 / 0.60`) |

---

## Observed point savings

These are from live repeated-identical-request tests (same prompt sent twice, seconds apart):

| Model | Endpoint | Points (cache miss) | Points (cache hit) | Savings |
|---|---|---:|---:|---:|
| `claude-haiku-4.5` | `/v1/messages` | 299 | 26 | **91%** |
| `gpt-5.4-mini` | `/v1/chat/completions` | 174 | 24 | **86%** |
| `gpt-5.4-mini` | `/v1/responses` | 174 | 24 | **86%** |

---

## What does NOT cache through Poe

These were tested with identical repeated prompts and showed zero cached tokens:

| Model | Endpoint | Result |
|---|---|---|
| `claude-haiku-4.5` | `/v1/chat/completions` | `cached_tokens: 0` on both requests. Billed full price both times (239 pts each). |
| `claude-haiku-4.5` | `/v1/responses` | `cached_tokens: 0` on both requests. Billed full price both times (239 pts each). |
| `gpt-5.4-mini` | `/v1/messages` | Returns `404` / internal server error. Not usable at all. |

**Why:** Poe translates between API formats at the edge. The Anthropic cache machinery only activates on the Anthropic-native Messages path; the OpenAI cache machinery only activates on OpenAI-native paths. Cross-format translation strips the cache context.

---

## Best practices

1. **Match endpoint to provider.** Claude → `/v1/messages`. GPT → `/v1/chat/completions` or `/v1/responses`.
2. **Structure prompts for prefix reuse.** Place static content (system instructions, documents, tool definitions) at the start. Put variable content (user messages, timestamps) at the end.
3. **For Claude, use explicit `cache_control`.** Mark the last stable block with `"cache_control": {"type": "ephemeral"}`. Don't place it on blocks that change every request.
4. **For GPT, just repeat the same prefix.** Caching is automatic — no special fields needed. Keep the prefix identical across requests.
5. **Verify with `points_history`.** Check `cost_breakdown_in_points` for `Cache discount` lines to confirm caching is active. Note: the entry may briefly show `cost_points: 0` before the final cost lands.
6. **Monitor with usage fields.** Check `cache_read_input_tokens` (Messages) or `cached_tokens` (Chat Completions / Responses) in the response to measure cache hit rates.
7. **Don't bother caching small prompts.** Claude Haiku 4.5 requires ≥4096 tokens; OpenAI models require ≥1024 tokens. Below these thresholds, caching is silently skipped.

---

## Third-party models with advertised cache discounts

Some models in Poe's catalog advertise cache discounts in their UI pricing cards but are not currently accessible through the `/v1/messages`, `/v1/chat/completions`, or `/v1/responses` APIs (`supported_endpoints: []`):

| Model | Provider | Cache discount | API access |
|---|---|---:|---|
| `glm-5.1-fw` | Fireworks AI | ~81% | ❌ not available |
| `minimax-m2.7` | Novita AI | ~80% | ❌ not available |
| `kimi-k2.5` | Novita AI | ~83% | ❌ not available |

These models may be accessible through Poe's chat interface or legacy bot API (`/bot/*`), but prompt caching behavior through those paths is unverified.

---

## Reproducing these results

The probe script and raw JSON are in the skill directory:

- `cache_probe.py` — runnable with `POE_API_KEY=... uv run python cache_probe.py`
- `cache_probe_results.json` — full response bodies, headers, timing, and billing
- `cache_probe_report.md` — detailed per-request breakdown

The fixture used was `test_file.txt` repeated 8× (~34k chars) to ensure the prompt exceeded all models' cache thresholds.
