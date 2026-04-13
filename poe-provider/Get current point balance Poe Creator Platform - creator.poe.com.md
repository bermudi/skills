---
title: "Get current point balance | Poe Creator Platform"
source: "creator.poe.com"
url: "https://creator.poe.com/api-reference/getCurrentBalance"
date_saved: "2026-04-13T19:30:44.816Z"
---

## Get current point balance

GET `https://api.poe.com/usage/current_balance`

## Overview

Retrieve your current point balance, including both plan points and add-on points.

Use this endpoint to monitor your available points before making API calls.

## Authentication

Send your Poe API key in the `Authorization` header:

```
Authorization: Bearer sk_test_51SAMPLEKEY
```

All requests must be made over HTTPS.

## Parameters

This endpoint does not accept query or path parameters.

## Responses

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `current_point_balance` | integer | **Required** | Your current available points |

| Http | Type | Description |
| --- | --- | --- |
| 401 | `authentication_error` | Authentication failed Invalid API key |

## Best Practices

Monitor your point balance to avoid service interruptions:

-   Check balance before batch operations
-   Set up alerts when balance drops below threshold
-   Monitor usage patterns via `/usage/points_history`

## 🔁 Callbacks & webhooks

No callbacks or webhooks are associated with this endpoint.