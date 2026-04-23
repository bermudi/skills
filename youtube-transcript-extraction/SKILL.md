---
name: youtube-transcript-extraction
description: >
  Extract YouTube video transcripts in browser extensions. Covers the full pipeline
  from discovery through formatting, including InnerTube API access, caption track
  selection, XML parsing, and DOM-based fallbacks. Triggers on: "YouTube transcript",
  "extract captions", "YouTube captions", "video transcript extraction",
  "timedtext API", "InnerTube transcript", "scrape YouTube subtitles".
---

# YouTube Transcript Extraction

Skill for extracting YouTube video transcripts in browser extensions. Covers the full pipeline from discovery through formatting, with emphasis on the failure modes that matter in practice.

## When to use

- Building a browser extension that needs video transcripts
- Scraping YouTube captions from a content script
- Working with `youtubei` InnerTube APIs

## Core pipeline (in order of reliability)

### 1. Get fresh caption tracks via ANDROID client (PRIMARY)

The `ytInitialPlayerResponse` embedded in the page HTML contains `captionTracks`, but the `baseUrl` fields have **expired signatures**. By the time the user clicks your extension button, those URLs return empty responses.

**Always hit the player API first** for fresh URLs:

```js
const ANDROID_CONTEXT = {
    client: {
        clientName: 'ANDROID',
        clientVersion: '20.10.38'
    }
};

async function fetchPlayerResponse(videoId, apiKey) {
    const url = `https://www.youtube.com/youtubei/v1/player?key=${encodeURIComponent(apiKey)}`;
    const resp = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Goog-Api-Format-Version': '1'
        },
        body: JSON.stringify({
            context: ANDROID_CONTEXT,
            videoId
        })
    });
    return resp.json();
}

// captionTracks live here:
const tracks = response?.captions?.playerCaptionsTracklistRenderer?.captionTracks;
```

The ANDROID client avoids bot checks better than the WEB client for programmatic access, and returns the same caption metadata with **live signatures**.

### 2. Extract API key from the page HTML

```js
function extractInnertubeApiKey(html) {
    const m = html.match(/"INNERTUBE_API_KEY":\s*"([a-zA-Z0-9_-]+)"/);
    return m?.[1] || '';
}
```

The key is stable per-page-load. Grab it from `document.documentElement.innerHTML`.

### 3. Fetch transcript XML from the fresh baseUrl

```js
async function fetchTranscriptXml(baseUrl) {
    const url = new URL(baseUrl);
    url.searchParams.delete('fmt');  // remove any stale format param

    const resp = await fetch(url.toString());
    const text = await resp.text();

    const parser = new DOMParser();
    const doc = parser.parseFromString(text, 'text/xml');
    const texts = doc.getElementsByTagName('text');

    return Array.from(texts).map((el) => {
        const start = Number(el.getAttribute('start') || '0');
        const raw = el.textContent || '';
        // YouTube double-encodes entities: &amp;#39; → &#39; → '
        const decoded = raw
            .replace(/<[^>]*>/gi, '')
            .replace(/&amp;/g, '&')
            .replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>')
            .replace(/&quot;/g, '"')
            .replace(/&#39;/g, "'")
            .trim();
        return { start, text: decoded };
    }).filter((seg) => seg.text);
}
```

Default format is XML (`<text start="1.23" dur="4.56">...</text>`). YouTube double-encodes HTML entities in the XML text content — you must decode `&amp;#39;` to `'` in two passes.

### 4. Language selection logic

```js
const LANG_FALLBACK_CHAIN = ['en', 'de', 'fr', 'es', 'it', 'zh', 'ja', 'ko', 'pt', 'ru'];

function pickBestTrack(tracks, preferredLang = 'auto') {
    if (!tracks?.length) return null;
    const byTwo = (code) => code.toLowerCase().slice(0, 2);

    if (preferredLang !== 'auto') {
        return tracks.find((t) => t.languageCode === preferredLang)
            || tracks.find((t) => byTwo(t.languageCode) === byTwo(preferredLang));
    }

    // Auto: prefer manual English over auto-generated English
    const enTracks = tracks.filter((t) => byTwo(t.languageCode) === 'en');
    const manualEn = enTracks.find((t) => t.kind !== 'asr');
    if (manualEn) return manualEn;
    const autoEn = enTracks.find((t) => t.kind === 'asr');
    if (autoEn) return autoEn;

    // Walk fallback chain
    for (const lang of LANG_FALLBACK_CHAIN) {
        const match = tracks.find((t) => byTwo(t.languageCode) === lang);
        if (match) return match;
    }

    return tracks[0];
}
```

Track shape:
```js
{
    baseUrl: "https://www.youtube.com/api/timedtext?v=...&lang=en&kind=asr...",
    languageCode: "en",
    name: { simpleText: "English (auto-generated)" },
    kind: "asr"   // "" for manual captions, "asr" for auto-generated
}
```

### 5. Fallback: regex-extract from inline HTML

If the ANDROID API fails (rate limit, network), fall back to scraping `ytInitialPlayerResponse` from the page's `<script>` tags:

```js
function extractCaptionTracksFromHtml(html) {
    const parts = html.split('"captions":');
    if (parts.length < 2) return null;
    const jsonPart = parts[1].split(',"videoDetails')[0].replace('\n', '');
    const renderer = JSON.parse(jsonPart).playerCaptionsTracklistRenderer;
    return renderer?.captionTracks?.map((t) => ({
        baseUrl: t.baseUrl.startsWith('/api/timedtext')
            ? `https://www.youtube.com${t.baseUrl}`
            : t.baseUrl,
        languageCode: t.languageCode,
        name: { simpleText: t.name?.simpleText || t.languageCode },
        kind: t.kind || ''
    })) ?? null;
}
```

**Do not rely on these URLs** — they are signed to the page load session and expire quickly. Use them only to know *which* languages exist, then construct fresh URLs or fall back to the panel scraper.

### 6. Last resort: scrape the visible transcript panel

If all API paths fail and the transcript panel is visible in the UI:

```js
function querySelectorDeep(root, selector) {
    if (!root) return null;
    const el = root.querySelector(selector);
    if (el) return el;
    for (const h of root.querySelectorAll('*')) {
        if (h.shadowRoot) {
            const found = querySelectorDeep(h.shadowRoot, selector);
            if (found) return found;
        }
    }
    return null;
}

function scrapeTranscriptFromDom() {
    const panel = querySelectorDeep(document, 'ytd-transcript-body-renderer');
    if (!panel) return null;

    const segments = querySelectorDeep(panel, 'ytd-transcript-segment-renderer');
    // ... extract timestamp + text from each segment
}
```

YouTube uses Shadow DOM heavily. A naive `document.querySelector` won't reach the panel.

## What does NOT work

### ❌ Using the WEB client for `youtubei/v1/player`

The WEB client triggers bot checks aggressively for programmatic POSTs. Use `clientName: "ANDROID"`.

### ❌ Trusting `baseUrl` from `ytInitialPlayerResponse` in the HTML

These URLs carry signatures (`sig=...`, `expire=...`) tied to the initial page load. They expire within minutes. Always get fresh URLs from the player API.

### ❌ Constructing unsigned `/api/timedtext` URLs

```js
// This does NOT work — YouTube requires a valid signature
`https://www.youtube.com/api/timedtext?v=${videoId}&lang=en`
```

Unsigned requests return empty responses. You need the signed `baseUrl` from the player API response.

### ❌ `fmt=json3` on a stale URL

YouTube silently ignores format parameter changes on expired URLs and returns empty bodies.

## Deep fallback: `youtubei/v1/get_transcript`

If direct XML fetch fails (rare with fresh URLs), you can call the InnerTube transcript endpoint. It requires protobuf-encoded params:

```js
class PbWriter {
    constructor() { this.buf = []; }
    varint(v) {
        while (v > 127) { this.buf.push((v & 0x7f) | 0x80); v >>>= 7; }
        this.buf.push(v);
    }
    string(field, val) {
        this.varint((field << 3) | 2);
        const bytes = new TextEncoder().encode(val);
        this.varint(bytes.length);
        this.buf.push(...bytes);
    }
    finish() { return new Uint8Array(this.buf); }
}

function bytesToBase64(bytes) {
    const bin = Array.from(bytes, (b) => String.fromCharCode(b)).join('');
    return btoa(bin);
}

function encodeGetTranscriptParams(videoId, language, kind) {
    const inner = new PbWriter();
    inner.string(1, kind);      // "" for manual, "asr" for auto
    inner.string(2, language);  // e.g. "en"
    const innerB64 = bytesToBase64(inner.finish());

    const outer = new PbWriter();
    outer.string(1, videoId);
    outer.string(2, innerB64);
    return bytesToBase64(outer.finish());
}
```

Request shape:
```js
const resp = await fetch(`https://www.youtube.com/youtubei/v1/get_transcript?key=${apiKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        params: encodeGetTranscriptParams(videoId, language, kind),
        context: ANDROID_CONTEXT
    })
});
```

Response path:
```js
const segments = data?.actions?.[0]?.updateEngagementPanelAction
    ?.content?.transcriptRenderer?.content?.transcriptSearchPanelRenderer
    ?.body?.transcriptSegmentListRenderer?.initialSegments ?? [];
```

Each segment has `transcriptSegmentRenderer.startMs` and `snippet.runs[].text`.

## Key findings from the field

1. **Start with the ANDROID client API.** HTML-scraped URLs are expired by the time the user interacts with your extension.
2. **XML is the default and most reliable format.** JSON3 works, but XML is what YouTube serves when you fetch `baseUrl` as-is.
3. **Double-decode HTML entities.** YouTube sends `&amp;#39;` in XML text nodes.
4. **Shadow DOM traversal is required for DOM scraping.** The transcript panel is not reachable with standard `querySelector`.
5. **The commercial extension pattern is correct.** The `getrecall` approach (ANDROID client → XML parse → protobuf fallback) is battle-tested.

## References

- YouTube's `timedtext` API (undocumented, but stable for years)
- InnerTube API (`youtubei/v1/*`) — reverse-engineered, changes slowly
- `response.json` in this repo for an example `get_transcript` response structure
