---
title: "Get video status | Poe Creator Platform"
source: "creator.poe.com"
url: "https://creator.poe.com/api-reference/getVideo"
date_saved: "2026-04-13T19:29:11.603Z"
---

## Get video status

GET `https://api.poe.com/v1/videos/{video_id}`

## Overview

Retrieve the current status and details of a video generation request. Use this endpoint to poll for completion after submitting a request with Create Video, Extend Video, or Remix Video.

**Polling pattern:** Check the `status` field — continue polling while it is `queued` or `in_progress`. A recommended polling interval is 5 seconds.

## Authentication

Send your Poe API key in the `Authorization` header:

```
Authorization: Bearer sk_test_51SAMPLEKEY
```

All requests must be made over HTTPS.

## Parameters

| Name | Location | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `video_id` | path | string | **Required** | The ID of the video to retrieve |

## Responses

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | Optional | Unique video identifier |
| `object` | "video" | Optional | Object type, always "video" Allowed values: `video` |
| `status` | "queued" | "in\_progress" | "completed" | "failed" | Optional | Current status of the video generation Allowed values: `queued`, `in_progress`, `completed`, `failed` |
| `created_at` | integer | Optional | Unix timestamp of when the video was created |
| `completed_at` | integer | null | Optional | Unix timestamp of when the video completed (null if not yet complete) |
| `expires_at` | integer | null | Optional | Unix timestamp of when the video content expires |
| `model` | string | Optional | Model used for generation |
| `seconds` | integer | Optional | Duration of the video in seconds |
| `size` | string | Optional | Resolution as `WIDTHxHEIGHT` |
| `progress` | integer | Optional | Generation progress (0-100) Min: 0 · Max: 100 |
| `remixed_from_video_id` | string | null | Optional | ID of the source video if this video was created via remix |
| `error` | object | null | Optional | Error details if the video generation failed (null unless status is `failed`) |
| `usage` | object | null | Optional | Token/point usage information (null until video is completed) |

| Http | Type | Description |
| --- | --- | --- |
| 401 | `authentication_error` | Authentication failed Invalid API key |
| 404 | `not_found` | Not found Video not found |
| 429 | `rate_limit_error` | Rate limit exceeded Rate limit exceeded (500 requests per minute) |

## 🔁 Callbacks & webhooks

No callbacks or webhooks are associated with this endpoint.