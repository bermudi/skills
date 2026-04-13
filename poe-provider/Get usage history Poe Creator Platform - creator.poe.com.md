---
title: "Get usage history | Poe Creator Platform"
source: "creator.poe.com"
url: "https://creator.poe.com/api-reference/getPointsHistory"
date_saved: "2026-04-13T19:30:47.071Z"
---

## Get usage history

GET `https://api.poe.com/usage/points_history`

## Overview

Retrieve your usage history with detailed information about each API call.

**Features:**

-   Entries are fetched by creation time, descending (most recent first)
-   Pagination support via `starting_after` cursor
-   Data available for up to 30 days
-   Maximum 100 entries per request

## Authentication

Send your Poe API key in the `Authorization` header:

```
Authorization: Bearer sk_test_51SAMPLEKEY
```

All requests must be made over HTTPS.

## Parameters

| Name | Location | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `limit` | query | integer | Optional | Number of entries to return (max 100, default 20) Min: 1 · Max: 100 · Default: `20` |
| `starting_after` | query | string | Optional | Pagination cursor - use the query\_id from the last entry of a previous response |

## Responses

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `has_more` | boolean | Optional | Whether there are more entries available for pagination |
| `length` | integer | Optional | Number of entries in the current response |
| `data` | object\[\] | Optional |  |
| `data[].creation_time` | int64 | **Required** | Unix timestamp in microseconds when the query was created |
| `data[].bot_name` | string | **Required** | Name of the bot or model used |
| `data[].query_id` | string | **Required** | Unique identifier for the query (used for pagination) |
| `data[].usage_type` | "API" | "Chat" | "Canvas App" | **Required** | Descriptor for where the points were used Allowed values: `API`, `Chat`, `Canvas App` |
| `data[].cost_points` | integer | **Required** | Number of points consumed by this query |

| Http | Type | Description |
| --- | --- | --- |
| 401 | `authentication_error` | Authentication failed Invalid API key |

## Best Practices

Implement pagination for large result sets:

-   Start with a reasonable `limit` (20-50 entries)
-   Use `has_more` to determine if more pages exist
-   Pass the last `query_id` as `starting_after` for next page
-   Data is available for 30 days

## 🔁 Callbacks & webhooks

No callbacks or webhooks are associated with this endpoint.