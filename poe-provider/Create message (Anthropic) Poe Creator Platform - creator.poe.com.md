---
title: "Create message (Anthropic) | Poe Creator Platform"
source: "creator.poe.com"
url: "https://creator.poe.com/api-reference/createMessage"
date_saved: "2026-04-13T19:30:35.595Z"
---

## Create message (Anthropic)

POST `https://api.poe.com/v1/messages`

## Overview

Creates a message using the Anthropic Messages API format. This endpoint provides a drop-in replacement for the Anthropic API, allowing you to use your Poe subscription points to access Claude models.

**⚠️ Claude Models Only:** This endpoint only supports official Anthropic Claude models. You cannot use this endpoint to call custom bots or models from other providers. For access to all bots on Poe, use the OpenAI-compatible API or the Poe Python SDK.

**Key benefits:**

-   Drop-in replacement for Anthropic API
-   Works with existing Anthropic SDK code
-   Use your existing Poe subscription points
-   No separate Anthropic API key needed
-   Requests proxied directly to provider with minimal transformation

**Features:**

-   Streaming support via SSE
-   Tool calling (function calling)
-   Multi-modal inputs (text, images)
-   Vision capabilities

## Authentication

Send your Poe API key in the `Authorization` header:

```
Authorization: Bearer sk_test_51SAMPLEKEY
```

All requests must be made over HTTPS.

## Parameters

| Name | Location | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `anthropic-version` | header | string | **Required** | Anthropic API version (required) |

### Request body

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `model` | string | **Required** | Claude model to use. You can use either Poe bot names or Anthropic API model names.

**Supported models:**
\- `claude-sonnet-4`, `claude-sonnet-4-20250514`
\- `claude-opus-4`, `claude-opus-4-20250514`
\- `claude-sonnet-4.5`, `claude-sonnet-4-5-20250929`
\- `claude-opus-4.5`, `claude-opus-4-5-20251101`
\- `claude-haiku-3.5`, `claude-3-5-haiku-20241022`
\- And other Claude models available on Poe
 |
| `max_tokens` | integer | **Required** | Maximum number of tokens to generate |
| `messages` | object\[\] | **Required** | A list of messages comprising the conversation |
| `messages[].role` | "user" | "assistant" | **Required** | The role of the message author Allowed values: `user`, `assistant` |
| `messages[].content` | string | object\[\] | **Required** | The contents of the message |
| `system` | string | object\[\] | Optional | System prompt for the conversation |
| `temperature` | number | Optional | Sampling temperature between 0 and 1 Min: 0 · Max: 1 |
| `top_p` | number | Optional | Nucleus sampling parameter |
| `top_k` | integer | Optional | Top-k sampling parameter |
| `stream` | boolean | Optional | Whether to stream the response Default: `false` |
| `stop_sequences` | string\[\] | Optional | Custom sequences that will cause the model to stop |
| `tools` | object\[\] | Optional | Definitions of tools the model may use |
| `tool_choice` | object | Optional | How the model should use the provided tools |
| `metadata` | object | Optional | Metadata about the request |

## Responses

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Optional | Unique identifier for the message |
| `type` | "message" | Optional | Object type, always "message" Allowed values: `message` |
| `role` | "assistant" | Optional | Role of the generated message Allowed values: `assistant` |
| `content` | object\[\] | Optional | Array of content blocks |
| `content[].type` | "text" | "tool\_use" | Optional | Type of content block Allowed values: `text`, `tool_use` |
| `content[].text` | string | Optional | Text content (for text blocks) |
| `content[].id` | string | Optional | Tool use ID (for tool\_use blocks) |
| `content[].name` | string | Optional | Tool name (for tool\_use blocks) |
| `content[].input` | object | Optional | Tool input (for tool\_use blocks) |
| `model` | string | Optional | The model that handled the request |
| `stop_reason` | "end\_turn" | "max\_tokens" | "stop\_sequence" | "tool\_use" | Optional | Reason the model stopped generating Allowed values: `end_turn`, `max_tokens`, `stop_sequence`, `tool_use` |
| `stop_sequence` | string | null | Optional | The stop sequence that caused generation to stop, if any |
| `usage` | object | Optional |  |
| `usage.input_tokens` | integer | Optional | Number of input tokens |
| `usage.output_tokens` | integer | Optional | Number of output tokens |

| Http | Type | Description |
| --- | --- | --- |
| 400 | `invalid_request_error` | Invalid request Malformed request or missing required fields |
| 401 | `authentication_error` | Authentication failed Invalid API key |
| 404 | `not_found_error` | Model not found Requested model not found. Only Claude models are supported. |
| 429 | `rate_limit_error` | Rate limit exceeded Rate limit exceeded (500 requests per minute) |

## 🔁 Callbacks & webhooks

No callbacks or webhooks are associated with this endpoint.