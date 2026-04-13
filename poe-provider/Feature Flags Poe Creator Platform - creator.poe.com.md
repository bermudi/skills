---
title: "Feature Flags | Poe Creator Platform"
source: "creator.poe.com"
url: "https://creator.poe.com/api-reference/feature-flags"
date_saved: "2026-04-13T19:30:17.007Z"
---

## Feature Flags

## Overview

The Poe API uses **feature flags** to let you opt into new behaviors or temporarily stay on a previous implementation during migration periods. This gives you time to test changes before they become the default.

Feature flags are controlled via a request header and confirmed via a response header.

---

## Request Header: poe-feature

Send a comma-separated list of feature flags to opt into specific behaviors:

```
poe-feature: chat-completions-strict, messages-v2
```

**Rules:**

-   Multiple flags are separated by commas
-   Each endpoint only looks at the flags relevant to it (prefix match)
-   Unrecognized flags are silently ignored
-   If the header is absent, the current default behavior applies

```
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

## Response Header: x-poe-feature-active

Every response includes this header, indicating which behavior actually served the request:

```
x-poe-feature-active: chat-completions-strict
```

Use this to confirm which version of the API handled your request, especially useful during migration periods.

---

## Available Feature Flags

| Flag | Endpoint | Description | Status |
| --- | --- | --- | --- |
| `chat-completions-strict` | `/v1/chat/completions` | Opt into the new strict OpenAI-compatible request validation | Active |
| `chat-completions-legacy` | `/v1/chat/completions` | Stay on the legacy permissive handler during grace period | Active |

Migration Timeline

---

## Best Practices

-   **Test early** — Use opt-in flags to test new behaviors against your application before the default switch
-   **Check response headers** — Verify `x-poe-feature-active` to confirm which handler served your request
-   **Plan migrations** — When a new flag is announced, update your integration during the early-access period
-   **Remove flags after migration** — Once the grace period ends, the flag is ignored. Clean up your code to remove stale headers.