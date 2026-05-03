# Poe Feature Flags and Chat Completions Migration

Use this file whenever a user is integrating with `/v1/chat/completions`, migrating older Poe code, or hitting validation errors after previously sending non-standard request fields.

---

## Why this matters

Poe is moving `/v1/chat/completions` from a permissive compatibility layer to **strict OpenAI-compatible request validation**.

That change is meant to reduce Poe-specific request transformations and make the endpoint behave more like the first-party API. In practice, older requests that relied on compatibility behavior may now fail.

Common risk areas:
- Fields the model does not declare in its parameter schema (check `GET /v1/models`)
- Older Poe-side renamed or translated parameters

`extra_body` works for parameters the model *does* declare (e.g., `enable_thinking` on Kimi, Qwen, DeepSeek models). The real rule: Poe rejects fields the model doesn't declare in its schema, not `extra_body` wholesale.

---

## Rollout phases

Poe announced this rollout in three phases:

1. **Early access**
   - Default behavior: legacy permissive mode
   - Opt in with `poe-feature: chat-completions-strict`

2. **Default strict**
   - Default behavior: strict mode
   - Temporary opt out with `poe-feature: chat-completions-legacy`

3. **Grace period ends**
   - Strict mode only
   - Legacy header ignored

Poe said the legacy fallback ended on **2026-04-24**.

---

## Request header: `poe-feature`

Send a comma-separated list of feature flags:

```http
poe-feature: chat-completions-strict, messages-v2
```

Rules:
- Multiple flags are comma-separated
- Each endpoint only looks at relevant flags
- Unknown flags are ignored
- If the header is absent, current rollout defaults apply

### Chat Completions flags

- `chat-completions-strict` — opt into strict validation early
- `chat-completions-legacy` — stay on the permissive handler temporarily during migration

---

## Response header: `x-poe-feature-active`

Every response includes the active mode that served the request:

```http
x-poe-feature-active: chat-completions-strict
```

Use this to confirm whether the request actually ran in strict or legacy mode.

---

## Migration checklist

1. **Check that the model supports this endpoint**
   - Call `GET https://api.poe.com/v1/models`
   - Look for `/v1/chat/completions` in `supported_endpoints`

2. **Check the model's parameter schema first**
   - Call `GET https://api.poe.com/v1/models` and inspect the model's parameter schema (enums, types, maximums)
   - Only fields the model declares in its schema will pass strict validation
   - `extra_body` with declared parameters works fine under strict mode
   - Remove older Poe-only aliases or translated parameters the model doesn't declare

3. **Test in strict mode now**
   - Send `poe-feature: chat-completions-strict`

4. **Confirm the active mode**
   - Inspect `x-poe-feature-active`

5. **Use legacy mode only as a temporary fallback**
   - `poe-feature: chat-completions-legacy`
   - Do not build long-term logic around it

6. **When parameters aren't in the model schema, use `/v1/responses` or provider API**
   - For reasoning controls the model doesn't declare for Chat Completions, use `/v1/responses` (where reasoning is native)
   - For structured outputs and web search, Responses API is the only option
   - For models without Responses API support (Kimi, Qwen, DeepSeek, etc.), use `extra_body` with declared parameters or the first-party API

---

## Example: strict-mode curl request

```bash
curl "https://api.poe.com/v1/chat/completions" \
  -H "Authorization: Bearer $POE_API_KEY" \
  -H "Content-Type: application/json" \
  -H "poe-feature: chat-completions-strict" \
  -d '{
    "model": "Claude-Sonnet-4.6",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

---

## Guidance for agents updating user code

When a user says an older Poe Chat Completions integration "used to work" but now fails:

1. Check `GET /v1/models` for the model's parameter schema — which fields does it declare?
2. Look for fields the model doesn't declare — those will fail strict validation
3. Add the strict header in testing so behavior is explicit
4. Check `x-poe-feature-active` in the response
5. If a needed parameter isn't in the model's Chat Completions schema:
   - Check if the model supports `/v1/responses` (native reasoning, etc.)
   - For models without Responses API support, use the first-party API for that parameter
