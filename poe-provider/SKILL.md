---
name: poe-provider
description: "Complete reference for integrating with Poe as an AI model provider. Use when: (1) Configuring Poe as a provider for coding agents (Claude Code, Codex, OpenCode, Kimi), (2) Setting up Poe API authentication with API keys or OAuth, (3) Querying AI models — Chat Completions for simple text (most reliable), Responses API for reasoning/web search/structured outputs, Messages API for Anthropic SDK/Claude Code, (4) Generating images, videos, or audio through Poe, (5) Managing API usage and compute points billing, (6) Configuring Poe's MCP server for model access, (7) Using Poe as a drop-in replacement for the Anthropic API / Claude Code provider, (8) Users mention Poe subscriptions, model access, or wanting to use Poe with their favorite AI tools. Triggers especially when users say 'use Poe', 'Poe API', 'poe-code', 'configure AI provider', 'Anthropic compatible', 'Claude Code with Poe', or need to access models through Poe."
---

# Poe Provider Integration

Poe provides unified access to hundreds of AI models from multiple providers through a single API. This skill covers authentication, API usage, content generation, and best practices for integrating with Poe.

---

## ⚠️ Critical Poe Gotchas (Read First!)

**These are the mistakes agents make repeatedly without explicit guidance:**

| Gotcha | Wrong | Correct |
|--------|-------|---------|
| **Env var name** | `OPENAI_API_KEY` | `POE_API_KEY` |
| **API key prefix** | `sk-...` or `your-key` | `poe-xxxxx-...` |
| **Base URL** | `api.openai.com` | `api.poe.com/v1` |
| **Anthropic base URL** | `api.anthropic.com` | `https://api.poe.com` |
| **Model names** | `gpt-4`, `claude-3` | `Claude-Sonnet-4.6`, `GPT-5.5`, `Gemini-3.1-Pro` |
| **Billing** | Tokens | Compute points |
| **Auth header** | Varies by endpoint | See below |
| **Chat Completions strict mode** | Strip all `extra_body` and non-standard fields | Use `extra_body` to pass custom bot parameters through the OpenAI SDK (e.g., `extra_body={"aspect": "1280x720"}` for Sora-2). The API rejects fields the model does not declare in its schema. |

---

## Quick Setup (3 Steps)

### 1. Get Your API Key

```bash
# Visit https://poe.com/api/keys while logged in
# Click "Create API Key"
# Copy the key (it starts with poe-)
```

### 2. Set Environment Variable

```bash
export POE_API_KEY=poe-xxxxx-your-key-here
```

### 3. Verify It Works

```bash
poe-code auth status
```

---

## Poe Python Library (Recommended)

For new Python projects, use the official Poe Python library (`fastapi-poe`). It provides the most feature-complete way to interact with Poe bots and models, including custom parameters and native file upload that are not available through the OpenAI-compatible API.

### Installation

```bash
pip install fastapi-poe
```

### Basic Usage

```python
import fastapi_poe as fp

api_key = "your_api_key"  # Get from https://poe.com/api/keys
message = fp.ProtocolMessage(role="user", content="Hello world")

for partial in fp.get_bot_response_sync(
    messages=[message],
    bot_name="GPT-5.5",
    api_key=api_key
):
    print(partial)
```

```python
import asyncio
import fastapi_poe as fp

async def get_response():
    api_key = "your_api_key"
    message = fp.ProtocolMessage(role="user", content="Hello world")

    async for partial in fp.get_bot_response(
        messages=[message],
        bot_name="GPT-5.5",
        api_key=api_key
    ):
        print(partial)

asyncio.run(get_response())
```

**Key features:**
- ✅ **All bots** — access any public bot on Poe
- ✅ **Custom parameters** — pass model-specific parameters (e.g., `thinking_budget`, `aspect_ratio`) via the `parameters` field on `ProtocolMessage`
- ✅ **File upload** — upload files natively with `fp.upload_file()` / `fp.upload_file_sync()`
- ✅ **Streaming** — both sync and async streaming supported

For advanced usage, see the [External Application Guide](https://creator.poe.com/docs/external-applications/external-application-guide).

---

## Switching from OpenAI SDK

**This is the fastest way to use Poe with existing code:**

```typescript
// ❌ Wrong - OpenAI
import OpenAI from 'openai';
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// ✅ Correct - Poe (just add baseURL!)
import OpenAI from 'openai';
const client = new OpenAI({ 
  baseURL: 'https://api.poe.com/v1',
  apiKey: process.env.POE_API_KEY 
});
```

**Python:**
```python
# Same pattern - just add base_url
from openai import OpenAI
client = OpenAI(
    base_url="https://api.poe.com/v1",
    api_key=os.environ.get("POE_API_KEY")
)
```

### Model Name Mapping

| OpenAI | Poe Equivalent |
|--------|---------------|
| `gpt-4o` | `Claude-Sonnet-4.6` or `GPT-5.5` |
| `gpt-4-turbo` | `Claude-Sonnet-4.6` |
| `gpt-3.5-turbo` | `Claude-Sonnet-4.6` or `Gemini-3.1-Pro` |
| `o1-preview` | `Claude-Opus-4.7` or `o3` |

---

## Poe Code CLI (Essential Tool)

Poe provides a powerful CLI for managing Poe integration:

### Core Commands

```bash
# Install
npm install -g poe-code

# Check balance
poe-code usage

# View usage history
poe-code usage list --pages 5

# List available models
poe-code models
poe-code models --search claude

# Wrap Claude Code with Poe
poe-code wrap claude

# One-off prompt
poe-code spawn claude "Fix the bug in auth.ts"

# Spawn against GitHub repo
poe-code spawn codex "Review auth module" --cwd github://owner/repo
```

### MCP Server Setup

```bash
# Configure Claude Code to use Poe MCP
npx poe-code@latest mcp configure claude-code

# Available MCP tools:
# - generate_text  (query any Poe bot)
# - generate_image
# - generate_video
# - generate_audio
```

---

## API Selection Guide

Poe exposes four primary integration methods. Choose based on your needs, not a rigid priority order.

| API / Library | Best For | Watch Out |
|-----|----------|-----------|
| **Poe Python Library** (`fastapi-poe`) | New Python projects, custom parameters, native file upload, all bots | Python only |
| **Chat Completions API** (OpenAI-compatible) | Simple text generation, OpenAI SDK users, `role: "system"`, reliable multi-turn | No built-in reasoning, web search, or structured outputs. Private bots are not currently supported; App-Creator and Script-Bot-Creator bots are also not available. Image/video/audio bots should use `stream: false` for best results. Custom bot parameters can be passed via `extra_body` through the OpenAI SDK — check the model schema at `GET /v1/models` first. |
| **Responses API** | Reasoning/thinking, web search, structured outputs | `instructions` silently ignored, `previous_response_id` broken on tested models, `output_text` missing on many models. For plain text, Chat Completions is more reliable. |
| **Messages API** (Anthropic-compatible) | Claude models, Anthropic SDK, Claude Code | Claude-only. Authentication uses `x-api-key` header (recommended) or `Authorization: Bearer`. |

### ⚠️ Responses API Platform Gaps (confirmed May 2026)

The Responses API has persistent gaps through Poe (official docs may show these features but they don't work in practice):
- **`instructions` is silently ignored** — accepted but has no effect on any provider
- **`previous_response_id` returns errors** — 500 for Claude, data-retention rejection for GPT
- **`output_text` shortcut missing** on many models — parse `output[].content[]` instead

Workaround: inject system context in the `input` array; use `input` array for multi-turn history. See `references/responses-api.md` for details.

### Chat Completions — Most Reliable for Text Generation

Chat Completions has **fewer platform gaps** than the Responses API. Tested against multiple models (May 2026):

| Feature | Status |
|---------|--------|
| Basic text | ✅ |
| System messages (`role: "system"`) | ✅ |
| Tool calling | ✅ |
| Parallel tool calls | ✅ |
| Agentic loop (tool result roundtrip) | ✅ |
| Multi-turn (message history) | ✅ |
| Streaming | ✅ |
| Image input | ✅ |
| Strict mode header | ✅ |
| `temperature`, `max_tokens` | ✅ |

Use Chat Completions when you need `role: "system"` or reliable multi-turn and don't want to work around the Responses API gaps.

### Chat Completions Strict Validation Rollout

Poe's `/v1/chat/completions` enforces **strict OpenAI-compatible request validation** (legacy fallback ended 2026-04-24). Fields the model doesn't declare in its schema are rejected. Custom bot parameters can be passed via `extra_body` through the OpenAI SDK (e.g., `extra_body={"aspect": "1280x720"}` for Sora-2).

1. Check `GET https://api.poe.com/v1/models` — confirm the model lists `/v1/chat/completions` in `supported_endpoints`, and **inspect the model's parameter schema** (enums, types, maximums) to see which parameters are declared
2. Test with `poe-feature: chat-completions-strict`
3. Inspect `x-poe-feature-active` on the response to confirm which mode handled the request
4. If a parameter isn't in the model's schema, move to `/v1/responses` or the first-party provider API

---

### Responses API (Primary Choice)

```bash
curl -X POST "https://api.poe.com/v1/responses" \
  -H "Authorization: Bearer $POE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "Claude-Sonnet-4.6", "input": "Your question"}'
```

### Messages API (Anthropic-Compatible — Secondary Choice for Claude Models)

```bash
curl "https://api.poe.com/v1/messages" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $POE_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-sonnet-4.6",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Ideal for**: Claude Code, Anthropic SDK integrations, or any tool that already speaks the Anthropic API protocol. Just swap `ANTHROPIC_BASE_URL` → `https://api.poe.com` and `ANTHROPIC_API_KEY` → your Poe key.

### Chat Completions API

```bash
curl -X POST "https://api.poe.com/v1/chat/completions" \
  -H "Authorization: Bearer $POE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Claude-Sonnet-4.6",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Use when**: you need the OpenAI SDK shape, or when `instructions`/`previous_response_id` gaps on the Responses API matter for your integration. System messages, multi-turn, tools, streaming, and image input all work reliably. Private bots are not currently supported.

**Strict validation note**: Poe's strict validation for `/v1/chat/completions` is now the default (legacy fallback ended 2026-04-24). Fields the model doesn't declare in its schema are rejected. Custom bot parameters can be passed via `extra_body` through the OpenAI SDK (e.g., `extra_body={"aspect": "1280x720"}` for Sora-2) — check `GET /v1/models` for each model's parameter schema. See `references/feature-flags.md` for full details.

### Auth Header by Endpoint

| Endpoint | Header |
|----------|--------|
| `/v1/responses` | `Authorization: Bearer $POE_API_KEY` |
| `/v1/messages` | `x-api-key: $POE_API_KEY` (recommended) or `Authorization: Bearer $POE_API_KEY` |
| `/v1/chat/completions` | `Authorization: Bearer $POE_API_KEY` |
| `/bot/*` | `Poe-API-Key: $POE_API_KEY` (legacy, for content generation) |

---

## Authentication

### API Key (Simplest)

```bash
# Environment variable
export POE_API_KEY=poe-xxxxx

# Or use poe-code login (opens browser)
npx poe-code@latest login
```

### OAuth PKCE (For User-Facing Apps)

```typescript
import { poeOAuth } from 'poe-oauth';

// 1. Create auth URL
const { authorizationUrl } = await poeOAuth.createAuthCode({
  callbackUrl: 'https://yourapp.com/callback'
});
res.redirect(authorizationUrl);

// 2. Exchange code for key
const { key } = await poeOAuth.exchangeCode({ code: req.query.code });
```

---

## Usage & Billing

**Poe uses compute points**, not tokens. Monitor usage:

```bash
# Check balance
poe-code usage

# View history
poe-code usage list --pages 5

# Filter by model
poe-code usage list --filter claude
```

### Point Costs (Relative)

| Type | Relative Cost |
|------|---------------|
| Text (100 tokens) | 1x |
| Image (1024x1024) | ~10x |
| Video (5 sec) | ~50x |

---

## Error Handling

### Quick Reference

| Status | Meaning | Fix |
|--------|---------|-----|
| **401** | Invalid API key | Check `POE_API_KEY`, regenerate key |
| **402** | Insufficient credits | Balance is zero or negative; check `poe-code usage` |
| **403** | Moderation / permission denied | Check subscription or authorization |
| **404** | Model not found | Use `poe-code models` to verify name |
| **408** | Timeout | Model didn't start in a reasonable time; retry later |
| **413** | Request too large | Input exceeds context window; reduce prompt size |
| **429** | Rate limited | Wait, implement backoff (500 requests/minute) |
| **502** | Upstream error | Model backend not working; retry later |
| **529** | Overloaded | Transient traffic spike; retry with backoff |

### 401 vs 403

- **401 Unauthorized**: Your API key is wrong or expired
- **403 Forbidden**: Your subscription doesn't cover this

### Retry Pattern

```typescript
async function retryWithBackoff(fn: () => Promise<Response>, maxRetries = 5) {
  for (let i = 0; i < maxRetries; i++) {
    const response = await fn();
    if (response.ok) return response;
    if (response.status === 429 || response.status >= 500) {
      await sleep(Math.pow(2, i) * 1000);
      continue;
    }
    throw new Error(`HTTP ${response.status}`);
  }
}
```

---

## Content Generation

### Image Generation

```bash
curl -X POST "https://api.poe.com/bot/dalle-3" \
  -H "Poe-API-Key: $POE_API_KEY" \
  -d '{"query": "A sunset over mountains", "image_size": "1024x1024"}'
```

**Sizes:** `1024x1024` (square), `1792x1024` (landscape), `1024x1792` (portrait)  
**Styles:** `vivid` (enhanced), `natural` (realistic)

### Video Generation

```bash
curl -X POST "https://api.poe.com/bot/video-generator" \
  -H "Poe-API-Key: $POE_API_KEY" \
  -d '{"query": "Ocean waves crashing"}'
```

### Audio (TTS)

```bash
curl -X POST "https://api.poe.com/bot/audio-tts" \
  -H "Poe-API-Key: $POE_API_KEY" \
  -d '{"query": "Hello!", "voice": "alloy"}'
```

**Voices:** `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

---

## Gotchas (Additional)

- **OAuth requires subscription**: Users need Poe Pro subscription for API access
- **Rate limits vary by tier**: Check `poe-code usage` for your limits
- **Streaming errors**: Wrap in try/catch, handle incomplete streams
- **Model availability**: Not all models available via API (some web-only)
- **App-Creator and Script-Bot-Creator bots** are not available via the OpenAI-compatible API
- **Audio input** is ignored and stripped from Chat Completions requests
- **Structured outputs (`response_format: {type: "json_schema"}`)** are not supported in Chat Completions — use the Responses API instead
- **File inputs** (PDF, audio, video) can be passed via `type: "file"` with base64 data URLs in Chat Completions

---

## Reference Files

| File | Priority | When to Read |
|------|----------|--------------|
| `references/responses-api.md` | — | Full Responses API reference (reasoning, web search, structured outputs, streaming, tool use) |
| `references/anthropic-api.md` | **2nd** | Anthropic-compatible Messages API (Claude Code, Anthropic SDK, tool use) |
| `references/chat-completions-api.md` | — | Chat Completions API — most reliable for text generation (system messages, tools, multi-turn, streaming, images). Use when Responses API gaps matter. |
| `references/feature-flags.md` | — | `/v1/chat/completions` rollout guidance: strict vs legacy headers, response confirmation, and migration steps |
| `references/authentication.md` | — | OAuth flow, Poe-specific auth gotchas |
| `references/bermudi-models.md` | — | bermudi's tracked models — families, thinking params, probe results, re-run instructions |
| `references/costs_and_usage.md` | — | Compute point balance, usage history API, pagination patterns |
| `references/cache.md` | — | Prompt caching: what works, what doesn't, point savings, per-endpoint guide |
| `references/errors.md` | — | Error codes and debugging |
