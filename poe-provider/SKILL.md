---
name: poe-provider
description: "Complete reference for integrating with Poe as an AI model provider. Use when: (1) Configuring Poe as a provider for coding agents (Claude Code, Codex, OpenCode, Kimi), (2) Setting up Poe API authentication with API keys or OAuth, (3) Querying AI models — prefer the Responses API first, then the Anthropic-compatible Messages API for Claude models, and only use Chat Completions as a last resort (many models don't support tools via that endpoint), (4) Generating images, videos, or audio through Poe, (5) Managing API usage and compute points billing, (6) Configuring Poe's MCP server for model access, (7) Using Poe as a drop-in replacement for the Anthropic API / Claude Code provider, (8) Users mention Poe subscriptions, model access, or wanting to use Poe with their favorite AI tools. Triggers especially when users say 'use Poe', 'Poe API', 'poe-code', 'configure AI provider', 'Anthropic compatible', 'Claude Code with Poe', or need to access models through Poe."
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
| **Anthropic base URL** | `api.anthropic.com` | `api.poe.com` |
| **Model names** | `gpt-4`, `claude-3` | `claude-3-5-sonnet`, `gpt-4o` |
| **Billing** | Tokens | Compute points |
| **Auth header** | Varies by endpoint | See below |

---

## Quick Setup (3 Steps)

### 1. Get Your API Key

```bash
# Visit https://poe.com/api while logged in
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
| `gpt-4o` | `claude-3-5-sonnet` or `gpt-4o` |
| `gpt-4-turbo` | `claude-3-5-sonnet` |
| `gpt-3.5-turbo` | `claude-3-haiku` |
| `o1-preview` | `o1-preview` |

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

Poe exposes three APIs. **Always use the highest-priority API that fits your use case.**

| Priority | API | Use When | Why |
|----------|-----|----------|-----|
| **1st** | **Responses API** | Any model, any task | Full tool support, streaming, multi-turn, Poe-native features |
| **2nd** | **Messages API** (Anthropic-compatible) | Claude/Anthropic models, or when integrating with the Anthropic SDK | Drop-in replacement for `api.anthropic.com`, native Claude tool use format |
| **3rd** | **Chat Completions API** (OpenAI-compatible) | Only when you must use the OpenAI SDK/API shape | Last resort — many models on Poe do not support tools via this endpoint |

### ⚠️ Chat Completions Limitations

The Chat Completions API is an OpenAI-compatibility shim. It works for basic text generation, but:
- **Not all Poe models support tools** through this endpoint
- Tool calling behavior may differ from the Responses or Messages APIs
- Prefer Responses API or Messages API when tools are needed

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
curl -X POST "https://api.poe.com/v1/messages" \
  -H "x-api-key: $POE_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4.6",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Ideal for**: Claude Code, Anthropic SDK integrations, or any tool that already speaks the Anthropic API protocol. Just swap `ANTHROPIC_BASE_URL` → `https://api.poe.com` and `ANTHROPIC_API_KEY` → your Poe key.

### Chat Completions API (Last Resort)

```bash
curl -X POST "https://api.poe.com/v1/chat/completions" \
  -H "Authorization: Bearer $POE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Use only when**: you're locked into the OpenAI SDK or need OpenAI-shaped responses and can't use either of the above.

### Auth Header by Endpoint

| Endpoint | Header |
|----------|--------|
| `/v1/responses` | `Authorization: Bearer $POE_API_KEY` |
| `/v1/messages` | `x-api-key: $POE_API_KEY` _or_ `Authorization: Bearer $POE_API_KEY` |
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
| **403** | No permission | Upgrade subscription |
| **404** | Model not found | Use `poe-code models` to verify name |
| **429** | Rate limited | Wait, implement backoff |

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

---

## Reference Files

| File | Priority | When to Read |
|------|----------|--------------|
| `references/responses-api.md` | **1st** | Full Responses API reference (reasoning, web search, structured outputs, streaming, tool use, agentic loops) |
| `references/anthropic-api.md` | **2nd** | Anthropic-compatible Messages API (Claude Code, Anthropic SDK, tool use, streaming, agentic loops) |
| `references/chat-completions-api.md` | **3rd** | Chat Completions API details (last resort — limited tool support, agentic loops) |
| `references/authentication.md` | — | OAuth flow, credential storage |
| `references/models.md` | — | Full model catalog (if needed) |
| `references/content-gen.md` | — | Image/video/audio details |
| `references/errors.md` | — | Error codes, debugging |
