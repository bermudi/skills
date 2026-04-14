# Poe prompt caching probe report

Date: 2026-04-13

## Test setup

- Fixture: `poe-provider/test_file.txt`
- To exceed cache thresholds, the fixture was repeated **8×** into a stable prompt prefix (~34k chars)
- Output was constrained to a tiny answer (`OK`) to keep output-token noise low
- Live APIs tested:
  - `POST /v1/messages`
  - `POST /v1/chat/completions`
  - `POST /v1/responses`
- Models tested:
  - `claude-haiku-4.5`
  - `gpt-5.4-mini`

Raw artifacts:
- Script: `poe-provider/cache_probe.py`
- Raw JSON: `poe-provider/cache_probe_results.json`

---

## Bottom line

| Model | Messages API | Chat Completions API | Responses API | Verdict |
|---|---:|---:|---:|---|
| `claude-haiku-4.5` | ✅ cache hit observed | ❌ no cache hit observed | ❌ no cache hit observed | Caching works through Poe **only on `/v1/messages`** in this probe |
| `gpt-5.4-mini` | ❌ endpoint returns 404/internal error | ✅ cache hit observed | ✅ cache hit observed | Caching works through Poe on **OpenAI-style endpoints** |

---

## Detailed results

| Model | Endpoint | Request 1 | Request 2 | Cache evidence | Observed points |
|---|---|---|---|---|---|
| `claude-haiku-4.5` | `/v1/messages` | `input_tokens=17`, `cache_creation_input_tokens=8352`, `output_tokens=4` | `input_tokens=17`, `cache_read_input_tokens=8352`, `output_tokens=4` | **Yes** — second call read 8,352 cached tokens | `299 → 26` |
| `claude-haiku-4.5` | `/v1/chat/completions` | `prompt_tokens=8369`, `cached_tokens=0`, `completion_tokens=4` | `prompt_tokens=8369`, `cached_tokens=0`, `completion_tokens=4` | **No** — zero cached tokens on both calls | `239 → 239` |
| `claude-haiku-4.5` | `/v1/responses` | `input_tokens=8370`, `cached_tokens=0`, `output_tokens=4` | `input_tokens=8370`, `cached_tokens=0`, `output_tokens=4` | **No** — zero cached tokens on both calls | `239 → 239` |
| `gpt-5.4-mini` | `/v1/messages` | HTTP `404` with body `{"type":"error","error":{"type":"api_error","message":"Internal server error"}}` | same | Not testable | n/a |
| `gpt-5.4-mini` | `/v1/chat/completions` | `prompt_tokens=7661`, `cached_tokens=0`, `completion_tokens=5` | `prompt_tokens=7661`, `cached_tokens=7424`, `completion_tokens=5` | **Yes** — second call cached 7,424 tokens | `174 → 24` |
| `gpt-5.4-mini` | `/v1/responses` | `input_tokens=7657`, `cached_tokens=0`, `output_tokens=5` | `input_tokens=7657`, `cached_tokens=7424`, `output_tokens=5` | **Yes** — second call cached 7,424 tokens | `174 → 24` |

---

## What Poe’s billing API reported

### Claude Haiku via `/v1/messages`

First call:
- `Input`: `238 points (8369 tokens)`
- `Cache write`: `60 points (8352 tokens)`
- `Output`: `1 point (4 tokens)`
- `Total`: **299 points**

Second call:
- `Input`: `238 points (8369 tokens)`
- `Output`: `1 point (4 tokens)`
- `Cache discount`: `-213 points (8352 tokens)`
- `Total`: **26 points**

### GPT-5.4-Mini via `/v1/chat/completions`

First call:
- `Input`: `173 points (7661 tokens)`
- `Output`: `1 point (5 tokens)`
- `Total`: **174 points**

Second call:
- `Input`: `173 points (7661 tokens)`
- `Output`: `1 point (5 tokens)`
- `Cache discount`: `-150 points (7424 tokens)`
- `Total`: **24 points**

### GPT-5.4-Mini via `/v1/responses`

First call:
- `Input`: `173 points (7657 tokens)`
- `Output`: `1 point (5 tokens)`
- `Total`: **174 points**

Second call:
- `Input`: `173 points (7657 tokens)`
- `Output`: `1 point (5 tokens)`
- `Cache discount`: `-150 points (7424 tokens)`
- `Total`: **24 points**

---

## Additional models from the Poe pricing cards

I checked Poe’s live model catalog and then tried `POST /v1/responses`.

| Model | Supported endpoints in `/v1/models` | Live probe result | Pricing-based cache discount |
|---|---|---|---:|
| `glm-5.1-fw` | `[]` | `400` — `Model does not support responses method.` | **81.4%** (`0.26 / 1.40`) |
| `minimax-m2.7` | `[]` | `400` — `Model does not support responses method.` | **80.0%** (`0.06 / 0.30`) |
| `kimi-k2.5` | `[]` | `400` — `Model does not support responses method.` | **83.3%** (`0.10 / 0.60`) |

These match the UI cards you pasted:
- GLM-5.1-FW: ~81% discount
- Minimax-M2.7: 80% discount
- Kimi-K2.5: ~83% discount

But: **they are not currently exposed through Poe’s `/v1/messages`, `/v1/chat/completions`, or `/v1/responses` APIs**, so I could not verify API-side prompt caching behavior for them directly.

---

## Notable quirks

1. `claude-haiku-4.5` caches correctly through the Anthropic-compatible Messages API.
2. The same Claude model did **not** show cache hits through Poe’s Chat Completions or Responses endpoints in this probe, even with identical repeated prompts.
3. `gpt-5.4-mini` caches correctly through Poe’s Chat Completions and Responses APIs.
4. `gpt-5.4-mini` is listed in `/v1/models` as supporting `/v1/messages`, but live calls to `/v1/messages` returned an internal-error payload on every attempt, including a minimal non-caching request.
5. Poe’s `points_history` endpoint can briefly return a new row with `cost_points: 0` before the final cost breakdown lands; the finalized rows later showed the correct cache write / cache discount values.
