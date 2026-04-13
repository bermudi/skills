---
title: "Client SDKs | Poe Creator Platform"
source: "creator.poe.com"
url: "https://creator.poe.com/api-reference/client-sdks"
date_saved: "2026-04-13T19:29:46.286Z"
---

## Client SDKs

The Poe API can be accessed through three primary methods: the native Poe Python library, the OpenAI-compatible REST API, or the Anthropic-compatible REST API. Choose the method that best fits your use case.

## Quick Comparison

| Feature | Poe Python Library | OpenAI-Compatible API | Anthropic-Compatible API |
| --- | --- | --- | --- |
| **Installation** | `pip install fastapi-poe` | Any HTTP client or OpenAI SDK | Any HTTP client or Anthropic SDK |
| **Language Support** | Python only | Any language | Any language |
| **Supported Bots** | All bots on Poe | All bots on Poe | ⚠️ **Claude models only** |
| **Custom Parameters** | ✅ Full support | ❌ Not supported | ❌ Not supported |
| **File Upload** | ✅ Native support | Limited | Via Anthropic format |
| **Streaming** | ✅ Async/sync | ✅ Via standard streaming | ✅ Via SSE |
| **Error Handling** | ✅ Enhanced | Standard HTTP errors | Anthropic error format |
| **Best For** | New Python projects, custom parameters | OpenAI migrations, multi-language projects | Anthropic migrations, Claude-only use cases |

Recommendation

---

The official Poe Python library provides the most feature-complete way to interact with Poe bots and models.

### Installation

```
pip install fastapi-poe
```

### Basic Usage

### Key Features

#### Custom Parameters (Python Library Only)

The Poe Python library supports passing custom parameters that are not available via the OpenAI-compatible API:

#### File Upload

```
import fastapi_poe as fp

api_key = "your_api_key"

# Upload file
pdf_attachment = fp.upload_file_sync(
    open("document.pdf", "rb"),
    api_key=api_key
)

# Send message with attachment
message = fp.ProtocolMessage(
    role="user",
    content="Summarize this document",
    attachments=[pdf_attachment]
)

for partial in fp.get_bot_response_sync(
    messages=[message],
    bot_name="GPT-5.4",
    api_key=api_key
):
    print(partial)
```

### Available APIs

The Poe Python library can access:

-   ✅ **Chat Completions** - `fp.get_bot_response()` / `fp.get_bot_response_sync()`
-   ✅ **File Upload** - `fp.upload_file()` / `fp.upload_file_sync()`
-   ✅ **Custom Parameters** - Via `parameters` field
-   ✅ **All public bots and models**

### Learn More

For detailed documentation and advanced usage, see the External Application Guide.

---

## Option 2: OpenAI-Compatible API

Use the standard OpenAI SDK or any HTTP client to access Poe models through an OpenAI-compatible interface.

### Using the OpenAI SDK

### Using Raw HTTP Requests

You can also make direct HTTP requests to the Poe API using any HTTP client:

### Available APIs

The OpenAI-compatible API supports:

-   ✅ **Chat Completions** - `/v1/chat/completions` (streaming and non-streaming)
-   ✅ **List Models** - `/v1/models`
-   ✅ **Current Balance** - `/usage/current_balance`
-   ✅ **Usage History** - `/usage/points_history`
-   ❌ **Custom Parameters** - Not supported (use Poe Python library instead)

### Key Limitations

For detailed compatibility information, see the OpenAI Compatible API Guide.

---

## Option 3: Anthropic-Compatible API

Use the standard Anthropic SDK or any HTTP client to access Claude models through an Anthropic-compatible interface. This is ideal if you're migrating from Anthropic or prefer the Anthropic Messages API format.

Claude Models Only

### Using the Anthropic SDK

### Available APIs

The Anthropic-compatible API supports:

-   ✅ **Messages** - `/v1/messages` (streaming and non-streaming)
-   ✅ **Tool Use** - Function calling with Claude
-   ✅ **Vision** - Image inputs
-   ❌ **Non-Claude bots** - Only official Claude models are supported

### Key Differences

-   **Claude models only** - Cannot access GPT, Gemini, Llama, or custom bots
-   **Anthropic error format** - Errors follow Anthropic's API conventions
-   **Direct provider proxy** - Requests are proxied to Anthropic with minimal transformation

For detailed information, see the Anthropic Compatible API Guide.

---

## Authentication

All API methods require authentication using your Poe API key.

### Get Your API Key

1.  Visit https://poe.com/api/keys
2.  Copy your API key
3.  Store it securely (see best practices below)

### Best Practices

Security Warning

**Key Management:**

-   ✅ Store API keys in environment variables, not in code
-   ✅ Use different API keys for development and production
-   ✅ Rotate API keys periodically
-   ✅ Revoke compromised keys immediately
-   ❌ Never commit API keys to version control
-   ❌ Never expose keys in client-side code

### Environment Variable Setup

---

## Rate Limits and Usage

### Rate Limits

-   **500 requests per minute** per API key
-   Monitor usage with response headers
-   Implement exponential backoff for retries

### Point-Based Billing

All API usage consumes points from your account:

-   Check balance: Get Current Balance
-   View history: Get Points History
-   Purchase additional points: https://poe.com/api/keys

Different models consume different amounts of points based on computational cost. See the List Models endpoint for pricing information.