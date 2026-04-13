---
title: "Create a video | Poe Creator Platform"
source: "creator.poe.com"
url: "https://creator.poe.com/api-reference/createVideo"
date_saved: "2026-04-13T19:29:02.742Z"
---

## Create a video

POST `https://api.poe.com/v1/videos`

## Overview

Submit a video generation request. Video generation is asynchronous — the response returns immediately with a `queued` status. Poll Get Video until the status becomes `completed` or `failed`, then download the result with Get Video Content.

**Capabilities:**

-   Text-to-video generation from a prompt
-   Image-to-video generation via `input_image` (base64-encoded)
-   Configurable duration and resolution

**Supported models:** Sora-2, Sora-2-Pro, Veo-2, Veo-3, Veo-3-Fast, Veo-3.1, Veo-3.1-Fast

**Note:** Default duration when `seconds` is omitted varies by provider: 4 seconds for OpenAI models, 8 seconds for Vertex AI models. Default resolution is 720x1280 (portrait) — specify `size` explicitly if you need a different aspect ratio.

## Authentication

Send your Poe API key in the `Authorization` header:

```
Authorization: Bearer sk_test_51SAMPLEKEY
```

All requests must be made over HTTPS.

## Parameters

This endpoint does not accept query or path parameters.

### Request body

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `model` | string | **Required** | Poe bot name of the video model to use.

**Supported models:** Sora-2, Sora-2-Pro, Veo-2, Veo-3, Veo-3-Fast, Veo-3.1, Veo-3.1-Fast
 |
| `prompt` | string | **Required** | Text description of the video to generate |
| `seconds` | integer | null | Optional | Duration of the video in seconds. Default varies by model (4s for OpenAI, 8s for Vertex AI) |
| `size` | string | null | Optional | Resolution as `WIDTHxHEIGHT` (e.g. `1280x720`). Default is `720x1280` (portrait) |
| `input_image` | string | null | Optional | Base64-encoded reference image for image-to-video generation (JSON body). Use `input_reference` for multipart form uploads |

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
| 429 | `rate_limit_error` | Rate limit exceeded Rate limit exceeded (500 requests per minute) |

## 🔁 Callbacks & webhooks

No callbacks or webhooks are associated with this endpoint.