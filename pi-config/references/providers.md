# Providers & Models

## Authentication

**Subscriptions:** `/login` in interactive mode for Anthropic Claude Pro/Max, OpenAI ChatGPT Plus/Pro, GitHub Copilot.

**API keys:** Set the appropriate environment variable before starting pi.

| Provider | Env variable |
|----------|-------------|
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Google Gemini | `GEMINI_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| Groq | `GROQ_API_KEY` |
| Mistral | `MISTRAL_API_KEY` |
| xAI | `XAI_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| Cerebras | `CEREBRAS_API_KEY` |
| Fireworks | `FIREWORKS_API_KEY` |

Full provider list (including Azure OpenAI, Cloudflare AI Gateway, Cloudflare Workers AI, Vercel AI Gateway, ZAI, OpenCode, HuggingFace, Kimi, MiniMax, and more) and setup instructions:
https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/providers.md

## Model selection

**Interactive:** `/model` (or Ctrl+L) to browse and switch. Ctrl+P / Shift+Ctrl+P to cycle through scoped models.

**Settings:** Set defaults in `settings.json`:
```json
{
  "defaultProvider": "anthropic",
  "defaultModel": "claude-sonnet-4-20250514"
}
```

**CLI flags:**
```bash
pi --provider openai --model gpt-4o
pi --model openai/gpt-4o            # provider prefix, no --provider needed
pi --model sonnet:high              # thinking level shorthand
pi --thinking high                  # thinking level
pi --models "claude-*,gpt-4o"       # scoped model cycling
pi --list-models                    # list available
pi --list-models sonnet             # search models
```

## Scoped model cycling

Configure which models Ctrl+P cycles through:
```json
{ "enabledModels": ["claude-*", "gpt-4o", "gemini-2*"] }
```

Or from CLI: `pi --models "claude-*,gpt-4o"`

## Thinking levels

| Level | Use case |
|-------|----------|
| `off` | Simple tasks, no thinking needed |
| `minimal` | Quick answers |
| `low` | Light reasoning |
| `medium` | Default for most tasks |
| `high` | Complex reasoning |
| `xhigh` | Maximum reasoning budget |

Set via `/settings`, `settings.json` (`defaultThinkingLevel`), `--thinking <level>`, or inline with model name (`--model sonnet:high`). Cycle with Shift+Tab in interactive mode.

## Custom models & providers

**Add models** for supported provider APIs via `~/.pi/agent/models.json`.
Full docs: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/models.md

**Add custom providers** (custom APIs, OAuth flows) via extensions.
Full docs: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/custom-provider.md

## API key override

```bash
pi --api-key sk-ant-...   # overrides env vars
```
