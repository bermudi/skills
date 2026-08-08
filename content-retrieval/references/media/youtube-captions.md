# YouTube captions — pull them directly (deterministic-first)

The cheapest way to get a YouTube video's transcript is to **pull the captions
YouTube already has** — manual or auto-generated — via the InnerTube API. Free,
instant, no model, no GPU. This is the deterministic-first route for any
YouTube-transcript task; reach for it before Gemini `transcribe_segment`.

**Escalate to Gemini** (see [overview.md](overview.md), `transcribe_segment` /
`verify_speaker`) only when:
- the video has **no captions** at all, or
- you need **speaker attribution** (who said it), which captions don't carry.

The examples below are JavaScript (InnerTube is an HTTP API, so any client works
— `curl`, Python, etc.). `ANDROID_CONTEXT` and the player endpoint are
language-agnostic.

## Core pipeline (in order of reliability)

### 1. Get fresh caption tracks via the ANDROID client (PRIMARY)

`ytInitialPlayerResponse` embedded in the page HTML contains `captionTracks`,
but the `baseUrl` fields have **expired signatures**. By the time you fetch them,
those URLs return empty responses.

**Always hit the player API first** for fresh URLs:

```js
const ANDROID_CONTEXT = {
    client: { clientName: 'ANDROID', clientVersion: '20.10.38' }
};

async function fetchPlayerResponse(videoId, apiKey) {
    const url = `https://www.youtube.com/youtubei/v1/player?key=${encodeURIComponent(apiKey)}`;
    const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Goog-Api-Format-Version': '1' },
        body: JSON.stringify({ context: ANDROID_CONTEXT, videoId })
    });
    return resp.json();
}

// captionTracks live here:
const tracks = response?.captions?.playerCaptionsTracklistRenderer?.captionTracks;
```

The ANDROID client avoids bot checks better than the WEB client for programmatic
access, and returns the same caption metadata with **live signatures**.

### 2. Extract the API key from the page HTML

```js
function extractInnertubeApiKey(html) {
    const m = html.match(/"INNERTUBE_API_KEY":\s*"([a-zA-Z0-9_-]+)"/);
    return m?.[1] || '';
}
```

The key is stable per-page-load.

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

Default format is XML (`<text start="1.23" dur="4.56">...</text>`). YouTube
double-encodes HTML entities in the XML text content — you must decode
`&amp;#39;` to `'` in two passes.

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

### 5. Fallback: regex-extract caption tracks from inline HTML

If the ANDROID API fails (rate limit, network), fall back to scraping
`ytInitialPlayerResponse` from the page's `<script>` tags:

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

**Do not rely on these URLs** — they are signed to the page-load session and
expire quickly. Use them only to know *which* languages exist.

### 6. Deep fallback: `youtubei/v1/get_transcript`

If direct XML fetch fails (rare with fresh URLs), the InnerTube `get_transcript`
endpoint accepts protobuf-encoded params. Read
[get-transcript-fallback.md](get-transcript-fallback.md) for the `PbWriter`
protobuf encoder, the request body, and the response path.

## What does NOT work

- **The WEB client for `youtubei/v1/player`** triggers bot checks aggressively
  for programmatic POSTs. Use `clientName: "ANDROID"`.
- **`baseUrl` from `ytInitialPlayerResponse` in the HTML** carries signatures
  (`sig=...`, `expire=...`) tied to the initial page load; they expire within
  minutes. Always get fresh URLs from the player API.
- **Unsigned `/api/timedtext` URLs** (`?v=...&lang=en` with no `sig`) return
  empty responses. YouTube requires a valid signature.
- **`fmt=json3` on a stale URL** — YouTube silently ignores format-parameter
  changes on expired URLs and returns empty bodies.

## DOM scraping (last resort, browser only)

If all API paths fail and the transcript panel is visible in the UI, scrape it —
but YouTube uses Shadow DOM heavily, so a naive `document.querySelector` won't
reach it:

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

const panel = querySelectorDeep(document, 'ytd-transcript-body-renderer');
```

This path only applies inside a real browser (e.g. via the `agent-browser`
skill). Prefer the API pipeline above for content retrieval.
