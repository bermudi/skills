---
title: "Download video content | Poe Creator Platform"
source: "creator.poe.com"
url: "https://creator.poe.com/api-reference/getVideoContent"
date_saved: "2026-04-13T19:29:14.964Z"
---

## Download video content

GET `https://api.poe.com/v1/videos/{video_id}/content`

## Overview

Download the content of a completed video. The video must have `status: completed` before content can be downloaded.

**Content variants:**

| Variant | Content-Type | Description |
| --- | --- | --- |
| *(default)* | video/mp4 | Full video file |
| thumbnail | image/webp | Preview thumbnail |
| spritesheet | image/jpeg | Spritesheet of frames |

## Authentication

Send your Poe API key in the `Authorization` header:

```
Authorization: Bearer sk_test_51SAMPLEKEY
```

All requests must be made over HTTPS.

## Parameters

| Name | Location | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `video_id` | path | string | **Required** | The ID of the video to download |
| `variant` | query | "thumbnail" | "spritesheet" | Optional | The content variant to download Allowed values: `thumbnail`, `spritesheet` |

| Http | Type | Description |
| --- | --- | --- |
| 401 | `authentication_error` | Authentication failed Invalid API key |
| 404 | `not_found` | Not found Video not found |
| 429 | `rate_limit_error` | Rate limit exceeded Rate limit exceeded (500 requests per minute) |

## 🔁 Callbacks & webhooks

No callbacks or webhooks are associated with this endpoint.