---
title: "Remix a video | Poe Creator Platform"
source: "creator.poe.com"
url: "https://creator.poe.com/api-reference/remixVideo"
date_saved: "2026-04-13T19:29:19.454Z"
---

## Remix a video

POST `https://api.poe.com/v1/videos/{video_id}/remix`

## Overview

Re-style an existing video with a new prompt. The source video must have `status: completed`. The model is inherited from the source video — no `model` parameter is needed.

Poll Get Video until the remix's status becomes `completed` or `failed`, then download the result with Get Video Content.

**Sora models only.** Veo models (Vertex AI) do not support remix operations.

## Authentication

Send your Poe API key in the `Authorization` header:

```
Authorization: Bearer sk_test_51SAMPLEKEY
```

All requests must be made over HTTPS.

## Parameters

| Name | Location | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `video_id` | path | string | **Required** | The ID of the source video to remix |

### Request body

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `prompt` | string | **Required** | New prompt describing the desired style for the remixed video |

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
| 400 | `invalid_request_error` | Bad request Malformed JSON or missing required fields |
| 401 | `authentication_error` | Authentication failed Invalid API key |
| 402 | `insufficient_credits` | Insufficient credits Point balance is zero or negative |
| 404 | `not_found` | Not found Video not found |
| 429 | `rate_limit_error` | Rate limit exceeded Rate limit exceeded (500 requests per minute) |

## 🔁 Callbacks & webhooks

No callbacks or webhooks are associated with this endpoint.