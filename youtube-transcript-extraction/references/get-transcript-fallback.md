# Deep Fallback: `youtubei/v1/get_transcript`

Use this only when direct XML fetch from a fresh `baseUrl` fails (rare with
fresh URLs from the ANDROID player API). It calls the InnerTube transcript
endpoint, which requires protobuf-encoded params.

## Protobuf param encoding

InnerTube expects a base64-encoded protobuf blob in the `params` field. There is
no documented schema — the structure below is reverse-engineered and stable in
practice.

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

## Request shape

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

`ANDROID_CONTEXT` is the same client context used for the player API (see
`SKILL.md` §1).

## Response path

```js
const segments = data?.actions?.[0]?.updateEngagementPanelAction
    ?.content?.transcriptRenderer?.content?.transcriptSearchPanelRenderer
    ?.body?.transcriptSegmentListRenderer?.initialSegments ?? [];
```

Each segment has `transcriptSegmentRenderer.startMs` and `snippet.runs[].text`.
