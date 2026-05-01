# Settings

Pi uses JSON settings files. Project settings override global settings. Nested objects merge (not replace).

| Location | Scope |
|----------|-------|
| `~/.pi/agent/settings.json` | Global (all projects) |
| `.pi/settings.json` | Project (current directory) |

Edit directly or use `/settings` for a TUI form for common options.

## Key setting groups

### Model & thinking

```json
{
  "defaultProvider": "anthropic",
  "defaultModel": "claude-sonnet-4-20250514",
  "defaultThinkingLevel": "medium",
  "hideThinkingBlock": false,
  "thinkingBudgets": {
    "minimal": 1024,
    "low": 4096,
    "medium": 10240,
    "high": 32768
  }
}
```

### UI & display

```json
{
  "theme": "dark",
  "quietStartup": false,
  "collapseChangelog": false,
  "doubleEscapeAction": "tree",
  "treeFilterMode": "default",
  "editorPaddingX": 0,
  "autocompleteMaxVisible": 5,
  "showHardwareCursor": false
}
```

### Compaction (context window management)

```json
{
  "compaction": {
    "enabled": true,
    "reserveTokens": 16384,
    "keepRecentTokens": 20000
  }
}
```

### Retry behavior

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `retry.enabled` | boolean | `true` | Enable auto-retry on transient errors |
| `retry.maxRetries` | number | `3` | Max agent-level retry attempts |
| `retry.baseDelayMs` | number | `2000` | Base delay for exponential backoff |
| `retry.provider.timeoutMs` | number | SDK default | Provider request timeout (ms) |
| `retry.provider.maxRetries` | number | SDK default | Provider retry attempts |
| `retry.provider.maxRetryDelayMs` | number | `60000` | Max server-requested delay before failing |

```json
{
  "retry": {
    "enabled": true,
    "maxRetries": 3,
    "baseDelayMs": 2000,
    "provider": {
      "timeoutMs": 3600000,
      "maxRetries": 0,
      "maxRetryDelayMs": 60000
    }
  }
}
```

### Message delivery (steering/follow-up)

```json
{
  "steeringMode": "one-at-a-time",
  "followUpMode": "one-at-a-time",
  "transport": "sse"
}
```

### Shell

```json
{
  "shellPath": "/bin/zsh",
  "shellCommandPrefix": "shopt -s expand_aliases",
  "npmCommand": ["mise", "exec", "node@20", "--", "npm"]
}
```

### Sessions

```json
{ "sessionDir": ".pi/sessions" }
```

### Model cycling (Ctrl+P)

```json
{ "enabledModels": ["claude-*", "gpt-4o", "gemini-2*"] }
```

### Markdown output

```json
{ "markdown": { "codeBlockIndent": "  " } }
```

### Terminal & images

```json
{
  "terminal": {
    "showImages": true,
    "imageWidthCells": 60,
    "clearOnShrink": false
  },
  "images": {
    "autoResize": true,
    "blockImages": false
  }
}
```

### Telemetry & update checks

| Setting | Description |
|---------|-------------|
| `enableInstallTelemetry` (bool, default `true`) | Controls the anonymous install/update version ping. Does NOT control update checks. |
| `PI_SKIP_VERSION_CHECK=1` (env) | Skip the version update check. |
| `PI_OFFLINE=1` (env) / `--offline` | Disable ALL startup network operations. |

### Warnings

| Setting | Description |
|---------|-------------|
| `warnings.anthropicExtraUsage` (bool, default `true`) | Show a warning when Anthropic subscription auth may use paid extra usage |

```json
{ "warnings": { "anthropicExtraUsage": false } }
```

## Project overrides (merge behavior)

Project settings merge into global. Nested objects are merged, not replaced.

```json
// ~/.pi/agent/settings.json
{ "theme": "dark", "compaction": { "enabled": true, "reserveTokens": 16384 } }

// .pi/settings.json
{ "compaction": { "reserveTokens": 8192 } }

// Result
{ "theme": "dark", "compaction": { "enabled": true, "reserveTokens": 8192 } }
```

## Full docs

https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/settings.md

Local copy (if pi is installed): `~/.local/share/pnpm/global/5/.pnpm/@mariozechner+pi-coding-agent@<version>/node_modules/@mariozechner/pi-coding-agent/docs/settings.md`
