# Poe Chat Completions API Reference

OpenAI-compatible Chat Completions endpoint for drop-in replacement with existing code.

## ✅ Tested & Confirmed (May 2026)

All core features were tested against multiple models. This endpoint has **fewer platform gaps than the Responses API** through Poe:

| Feature | Claude-Haiku-4.5 | gpt-5.4-mini |
|---------|:---:|:---:|
| Basic text generation | ✅ | ✅ |
| System messages (`role: "system"`) | ✅ | ✅ |
| Tool calling | ✅ | ✅ |
| Parallel tool calls | ✅ | ✅ |
| Agentic loop (tool result roundtrip) | ✅ | ✅ |
| Multi-turn (message history) | ✅ | ✅ |
| Streaming (SSE) | ✅ | ✅ |
| Image input (base64 data URI) | ✅ | ✅ |
| Strict mode header (`poe-feature: chat-completions-strict`) | ✅ | ✅ |
| `temperature=0` deterministic | ✅ | ✅ |
| `max_tokens` enforcement | ✅ | ⚠️ returned empty content in test |

**Contrast with Responses API:** the Responses API's `instructions` field is silently ignored through Poe. Chat Completions has no equivalent gaps — `role: "system"` and multi-turn via message history both work. See `responses-api.md` for details.

---

## Endpoint

```
POST https://api.poe.com/v1/chat/completions
```

**Note**: This is similar to OpenAI's Chat Completions API but routes through Poe's infrastructure.

## Available APIs (OpenAI-Compatible Surface)

The OpenAI-compatible API supports more than just chat completions:

- ✅ **Chat Completions** — `POST /v1/chat/completions` (streaming and non-streaming)
- ✅ **List Models** — `GET /v1/models` (see `references/models.md`)
- ✅ **Current Balance** — `GET /usage/current_balance` (see `references/costs_and_usage.md`)
- ✅ **Usage History** — `GET /usage/points_history` (see `references/costs_and_usage.md`)
- ❌ **Custom Parameters** — Not supported on this API surface; use the Poe Python Library (`fastapi-poe`) instead

## Breaking Change: Strict Validation (Active)

Poe's `/v1/chat/completions` now enforces strict validation (legacy fallback ended 2026-04-24).

What this means in practice:
- Fields the model doesn't declare in its parameter schema are rejected
- `extra_body` **works** for parameters the model *does* declare (e.g., `enable_thinking` on Kimi, Qwen, DeepSeek models)
- Check `GET /v1/models` for each model's parameter schema (enums, types, maximums) to see what's allowed
- Older Poe-side parameter transformations and renamed compatibility params have been removed

### Feature Flag Headers

During rollout, control behavior with the `poe-feature` request header:

- `poe-feature: chat-completions-strict` — opt into strict validation early
- `poe-feature: chat-completions-legacy` — temporary fallback during the grace period
- Multiple feature flags may be comma-separated
- Unknown feature flags are ignored

Every response includes `x-poe-feature-active` so you can confirm which mode actually served the request.

### Strict-Mode Test Request

```bash
curl -X POST "https://api.poe.com/v1/chat/completions" \
  -H "Authorization: Bearer $POE_API_KEY" \
  -H "Content-Type: application/json" \
  -H "poe-feature: chat-completions-strict" \
  -d '{
    "model": "Claude-Sonnet-4.6",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

---

## Authentication

```bash
curl -X POST "https://api.poe.com/v1/chat/completions" \
  -H "Authorization: Bearer $POE_API_KEY" \
  -H "Content-Type: application/json"
```

---

## Request Format

### Minimal Request

```json
{
  "model": "Claude-Sonnet-4.6",
  "messages": [
    {"role": "user", "content": "Hello"}
  ]
}
```

### Full Request

```json
{
  "model": "Claude-Sonnet-4.6",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Explain quantum computing"}
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "top_p": 1.0,
  "stream": false,
  "stop": null
}
```

> **Strict-mode rule:** Fields the model doesn't declare in its parameter schema are rejected. Custom bot parameters can be passed via `extra_body` through the OpenAI SDK (e.g., `extra_body={"aspect": "1280x720"}` for Sora-2). Check `GET /v1/models` for each model's parameter schema.

---

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | Required | Model identifier |
| `messages` | array | Required | Conversation messages |
| `temperature` | float | 1.0 | Sampling temperature (0–2) |
| `max_tokens` | int | Model default | Max response tokens |
| `max_completion_tokens` | int | null | Maximum number of completion tokens to generate |
| `top_p` | float | 1.0 | Nucleus sampling |
| `stream` | boolean | false | Enable streaming |
| `stream_options` | object | null | Options for streaming |
| `stop` | string \| string[] | null | Stop sequences where the API will stop generating (all non-whitespace sequences work) |
| `tools` | array | null | Available functions |
| `tool_choice` | string \| object | auto | Controls which function is called |
| `parallel_tool_calls` | boolean | null | Enable parallel function calling |
| `n` | int | 1 | Number of completion choices (must be 1) |
| `logprobs` | boolean | null | Whether to return logprobs |
| `top_logprobs` | int | null | Number of most likely tokens to return logprobs for |
| `reasoning_effort` | string | null | Ignored — use `extra_body` instead |
| `response_format` | object | null | Ignored (`json_schema` not supported in Chat Completions) |
| `store` | boolean | null | Ignored |
| `metadata` | object | null | Ignored |
| `prediction` | object | null | Ignored |
| `presence_penalty` | float | null | Ignored |
| `frequency_penalty` | float | null | Ignored |
| `seed` | int | null | Ignored |
| `service_tier` | string | null | Ignored |
| `audio` | object | null | Ignored (audio input is stripped) |
| `logit_bias` | object | null | Ignored |
| `user` | string | null | Ignored |
| `modalities` | array | null | Ignored |

### Temperature vs Top-P

Use **either** `temperature` **or** `top_p`, not both. Using both can lead to unexpected behavior.

- `temperature`: Direct sampling control (0.0 = deterministic, 2.0 = very random)
- `top_p`: Nucleus sampling (0.1 = top 10% probability mass)

---

## Message Format

### Standard Roles

```json
[
  {"role": "system", "content": "You are a helpful assistant"},
  {"role": "user", "content": "What is 2+2?"},
  {"role": "assistant", "content": "2+2 equals 4."},
  {"role": "user", "content": "Thanks!"}
]
```

### Message Fields

| Field | Type | Description |
|-------|------|-------------|
| `role` | "system" \| "user" \| "assistant" \| "tool" | Message author role |
| `content` | string \| object[] | Message content |
| `name` | string | Name of the message author |
| `tool_calls` | object[] | Tool calls generated by the model |
| `tool_call_id` | string | Tool call this message responds to |

### Roles Reference

| Role | Description |
|------|-------------|
| `system` | System instructions (precedes user). Note: Poe UI-specific system prompts are skipped |
| `user` | Human messages |
| `assistant` | AI responses |
| `tool` | Tool execution results |

### Multimodal Content

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "What is in this image?"},
    {
      "type": "image_url",
      "image_url": {
        "url": "https://example.com/photo.jpg",
        "detail": "auto"
      }
    }
  ]
}
```

**Image detail options:**
- `auto`: Model decides
- `low`: Lower resolution (faster, cheaper)
- `high`: High resolution (slower, more expensive)

### File Inputs

You can pass PDF, audio, and video files using base64-encoded data URLs with `type: "file"`:

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "Summarize this document."},
    {
      "type": "file",
      "file": {
        "filename": "report.pdf",
        "file_data": "data:application/pdf;base64,..."
      }
    },
    {
      "type": "file",
      "file": {
        "filename": "audio.mp3",
        "file_data": "data:audio/mp3;base64,..."
      }
    },
    {
      "type": "file",
      "file": {
        "filename": "video.mp4",
        "file_data": "data:video/mp4;base64,..."
      }
    }
  ]
}
```

Poe also accepts publicly accessible URLs for images:

```json
{
  "type": "image_url",
  "image_url": {
    "url": "https://example.com/photo.jpg"
  }
}
```

---

## Response Format

### Non-Streaming

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "Claude-Sonnet-4.6",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Response text..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 150,
    "total_tokens": 200
  }
}
```

### Finish Reasons

| Reason | Meaning |
|--------|-------------|
| `stop` | Natural stopping point |
| `length` | Hit `max_tokens` limit |
| `content_filter` | Content filtered |
| `tool_calls` | Tool execution needed |

---

## Streaming

### Request

```bash
curl -X POST "https://api.poe.com/v1/chat/completions" \
  -H "Authorization: Bearer $POE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Claude-Sonnet-4.6",
    "messages": [{"role": "user", "content": "Count to 5"}],
    "stream": true
  }'
```

### Streaming Response

Server-Sent Events format:

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":123,"model":"Claude-Sonnet-4.6","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":123,"model":"Claude-Sonnet-4.6","choices":[{"index":0,"delta":{"content":" world"},"finish_reason":null}]}

data: [DONE]
```

### Client Implementation

```typescript
async function* streamChat(messages: any[], model: string) {
  const response = await fetch('https://api.poe.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.POE_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ model, messages, stream: true })
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  while (reader) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') return;
        try {
          yield JSON.parse(data);
        } catch {}
      }
    }
  }
}
```

---

## Tool Calling

Tool calling enables LLMs to interact with external functions. The model suggests tool calls with specific arguments, your client executes them, and returns results to continue the conversation.

> **Tool calling works** — tested with both Claude and GPT models through Poe. The model returns `function` tool calls with correct arguments, supports parallel calls, and correctly incorporates tool results when you send them back. Note that tool support still varies across *all* Poe models (not every model supports tools); the major ones (Claude, GPT) do.

> **Note:** The `strict` parameter for function calling is ignored. Tool use JSON is not guaranteed to follow the supplied schema.

---

### Defining Tools

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "plus",
            "description": "Add two integers together",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "First integer"},
                    "b": {"type": "integer", "description": "Second integer"}
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City and state, e.g. San Francisco, CA"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                },
                "required": ["location"]
            }
        }
    }
]
```

---

### Tool Calling Flow

#### Step 1: Request with Tools

```python
messages = [
    {"role": "user", "content": "What is 1999 + 2036? Also, what's the weather like in New York?"}
]

response = client.chat.completions.create(
    model="Claude-Sonnet-4.6",
    messages=messages,
    tools=TOOLS,
    tool_choice="auto"
)

print(response.choices[0].message.tool_calls)
```

**Example output:**

```python
[
  ChatCompletionMessageToolCall(
    id='call_abc123',
    function=Function(arguments='{"a": 1999, "b": 2036}', name='plus'),
    type='function'
  ),
  ChatCompletionMessageToolCall(
    id='call_def456',
    function=Function(arguments='{"location": "New York"}', name='get_weather'),
    type='function'
  )
]
```

#### Step 2: Execute Tools (Client)

```python
import json

tool_messages = []

for tool_call in response.choices[0].message.tool_calls:
    if tool_call.function.name == "plus":
        args = json.loads(tool_call.function.arguments)
        result = args["a"] + args["b"]  # 4035
        tool_messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": str(result)
        })

    elif tool_call.function.name == "get_weather":
        args = json.loads(tool_call.function.arguments)
        result = {"temperature": 72, "unit": "fahrenheit", "condition": "sunny"}
        tool_messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result)
        })
```

#### Step 3: Continue Conversation with Tool Results

```python
messages.append(response.choices[0].message)
messages.extend(tool_messages)

final_response = client.chat.completions.create(
    model="Claude-Sonnet-4.6",
    messages=messages,
    tools=TOOLS
)

print(final_response.choices[0].message.content)
```

**Example output:**

```
1999 + 2036 = 4035.

Current weather in New York, NY: sunny, around 72°F.
```

---

### tool_choice Options

Control how the model uses tools:

| Option | Behavior |
|--------|----------|
| `"auto"` | Model decides (default) |
| `"none"` | Model must not call tools |
| `{"type": "function", "function": {"name": "get_weather"}}` | Force a specific tool |

#### Force a Specific Tool

```python
response = client.chat.completions.create(
    model="Claude-Sonnet-4.6",
    messages=[{"role": "user", "content": "What's 42 plus 58?"}],
    tools=TOOLS,
    tool_choice={"type": "function", "function": {"name": "plus"}}
)

print(response.choices[0].message.tool_calls)
```

> **Note**: The `allowed_tools` option (`{"type": "allowed_tools", "allowed_tools": {...}}`) is not supported by most Poe models, even though it's in the OpenAI spec. Only specific models like `o3-mini` may support it.

---

### Agentic Loop

Models can chain multiple tool calls for complex workflows:

```python
import json

def execute_tool_call(tool_call):
    function_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)

    if function_name == "plus":
        return str(arguments["a"] + arguments["b"])
    elif function_name == "get_weather":
        return json.dumps({"temperature": 72, "condition": "sunny"})
    return "Tool not found"

messages = [
    {"role": "user", "content": "What is 30000 + 30000 + 30000 + 4000 + 41? Treat that number as a ZIP code and tell me the weather there."}
]

max_iterations = 10
for i in range(max_iterations):
    response = client.chat.completions.create(
        model="GPT-5.5",
        messages=messages,
        tools=TOOLS
    )

    assistant_message = response.choices[0].message

    if not assistant_message.tool_calls:
        print(f"Final response: {assistant_message.content}")
        break

    messages.append(assistant_message)

    for tool_call in assistant_message.tool_calls:
        print(f"Calling {tool_call.function.name} with {tool_call.function.arguments}")
        result = execute_tool_call(tool_call)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result
        })
```

**Example output:**

```
Calling plus with {"a": 30000, "b": 30000}
Calling plus with {"a": 60000, "b": 30000}
Calling plus with {"a": 90000, "b": 4041}
Calling get_weather with {"location": "94041", "unit": "fahrenheit"}
Final response: The sum is 94,041. Current weather in ZIP 94041: 72°F and sunny.
```

---

### Tool Response Format

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "index": 0,
        "id": "call_abc123",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"location\": \"San Francisco\"}"
        }
      }]
    },
    "finish_reason": "tool_calls"
  }]
}
```

### Continuing with Tool Results

```json
{
  "model": "Claude-Sonnet-4.6",
  "messages": [
    {"role": "user", "content": "What's the weather in San Francisco?"},
    {"role": "assistant", "tool_calls": [{"id": "call_abc123", "function": {"name": "get_weather", "arguments": "{\"location\": \"San Francisco\"}"}}]},
    {"role": "tool", "tool_call_id": "call_abc123", "content": "{\"temperature\": 22, \"conditions\": \"Sunny\"}"}
  ]
}
```

---

## Migration Checklist for Strict Mode

1. **Check model endpoint support first**
   - Call `GET https://api.poe.com/v1/models`
   - Confirm your model includes `/v1/chat/completions` in `supported_endpoints`
2. **Check the model's parameter schema**
   - Call `GET https://api.poe.com/v1/models` and inspect your model's parameter schema
   - Custom bot parameters can be passed via `extra_body` through the OpenAI SDK (e.g., `extra_body={"aspect": "1280x720"}` for Sora-2)
   - Remove fields the model doesn't declare
3. **Test with strict mode during rollout**
   - Send `poe-feature: chat-completions-strict`
4. **Confirm the active mode**
   - Inspect `x-poe-feature-active` on the response
5. **Use legacy mode only as a short-lived fallback**
   - `poe-feature: chat-completions-legacy`
   - Do not treat this as a permanent fix
6. **When parameters aren't in the schema, use `/v1/responses` or provider API**
   - For reasoning controls the model doesn't declare for Chat Completions, check if the model supports `/v1/responses`
   - For models without Responses API support, use the first-party API

---

## OpenAI SDK Compatibility

### Node.js

```typescript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'https://api.poe.com/v1',
  apiKey: process.env.POE_API_KEY
});

// Use exactly like OpenAI
const chat = await client.chat.completions.create({
  model: 'Claude-Sonnet-4.6',
  messages: [{ role: 'user', content: 'Hello' }]
});
```

### Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.poe.com/v1",
    api_key=os.environ.get("POE_API_KEY")
)

response = client.chat.completions.create(
    model="Claude-Sonnet-4.6",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### LangChain

```typescript
import { ChatOpenAI } from '@langchain/openai';

const llm = new ChatOpenAI({
  model: 'Claude-Sonnet-4.6',
  openAIApiKey: process.env.POE_API_KEY,
  configuration: {
    basePath: 'https://api.poe.com/v1'
  }
});
```

---

## Model Mapping

| OpenAI Model | Poe Equivalent |
|--------------|---------------|
| `gpt-4` | `Claude-Sonnet-4.6` or `Claude-Opus-4.7` |
| `gpt-3.5-turbo` | `Claude-Sonnet-4.6` or `Gemini-3.1-Pro` |
| `gpt-4-turbo` | `Claude-Sonnet-4.6` |
| `gpt-4o` | `Claude-Sonnet-4.6` or `GPT-5.5` |

**Note**: Model names on Poe may differ. Use `poe-code models` to find exact identifiers.

---

## Error Handling

### Common Errors

| Status | Error | Solution |
|--------|-------|----------|
| 400 | Bad request | Check JSON format or missing required fields |
| 401 | Invalid key | Verify `POE_API_KEY` |
| 402 | Insufficient credits | Point balance is zero or negative |
| 403 | Moderation / permission denied | Check subscription or authorization |
| 404 | Model not found | Use correct model name |
| 408 | Timeout | Model didn't start in a reasonable time; retry later |
| 413 | Request too large | Input exceeds context window; reduce prompt size |
| 429 | Rate limited | Implement backoff (500 requests/minute) |
| 500 | Server error | Retry later |
| 502 | Upstream error | Model backend not working; retry later |
| 529 | Overloaded | Transient traffic spike; retry with backoff |

**Important notes:**
- Private bots are not currently supported; App-Creator and Script-Bot-Creator bots are also not available
- Image/video/audio bots should use `stream: false` for best results
- Audio input is ignored and stripped from requests
- Structured outputs (`response_format: {type: "json_schema"}`) are not supported in Chat Completions
- The `strict` parameter for function calling is ignored
- Custom bot parameters can be passed via `extra_body` through the OpenAI SDK

### Retry Implementation

```typescript
async function chatWithRetry(messages: any[], model: string, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch('https://api.poe.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${process.env.POE_API_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ model, messages })
      });

      if (!response.ok) {
        if (response.status === 429 || response.status >= 500) {
          await sleep(Math.pow(2, i) * 1000);
          continue;
        }
        throw new Error(`HTTP ${response.status}`);
      }

      return response.json();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await sleep(Math.pow(2, i) * 1000);
    }
  }
}
```
