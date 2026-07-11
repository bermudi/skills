# Cluster → name mapping

Diarization returns anonymous clusters (`SPEAKER_00..N`). Resolve them to real
names. The key insight from hard experience: **heuristics are a proposal, not an
answer — and cluster IDs are not stable across runs.**

## Cluster IDs permute. Re-derive every run.

`SPEAKER_00` in run 1 is **not** `SPEAKER_00` in run 2 — pyannote assigns labels
by clustering, not by order of appearance. Do **not** hardcode a prior run's
`SPEAKER_MAP`. Print the evidence for *this* run's clusters and map them fresh.

## Step 1 — print the evidence

```python
from collections import defaultdict
for l in sorted(set(w["speaker"] for w in words)):
    ws=[w for w in words if w["speaker"]==l]
    dur=sum(w["end"]-w["start"] for w in ws)/60
    print(f"\n[{l}] {dur:.1f}min :: "+" ".join(w["text"] for w in ws[:35]))
```

Read the opening words. Distinctive signals:
- **Self-introductions** ("I'm Jonathan Capehart", "I'm X, host of Y") lock a
  cluster to a name with near-certainty.
- **Third-person references** ("thanks to Jonathan", "Ms. Isgur has talked
  about…") tell you who the *other* voices are, not the speaker's.
- **Role/affiliation tells** ("professor of law at NYU", "editor of SCOTUSblog")
  identify a speaker even without a name.

## Step 2 — resolve by elimination first (often enough)

If you know the **N** panelists up front (from the title/description/byline),
then once you've confidently mapped **N−1** clusters, the remaining cluster that
is clearly a panelist must be the Nth — by elimination, no confirmation needed.

And: once all **N** known panelists are placed, **any extra cluster is, by
definition, not a panelist** — an audience question, announcer, or off-mic
bleed. Label it `Unknown`. (We once spent Gemini calls confirming what
elimination already settled.)

## Step 3 — confirm genuinely uncertain clusters from the real audio

For a cluster you can't place from text (similar voices, no self-intro, ambiguous
content), pick a clean ~15–20 s window where that cluster speaks alone, and ask
Gemini to identify the voice against the known speakers:

```bash
mcporter call gemini-media.transcribe_segment --timeout 300000 \
  youtube_url="https://www.youtube.com/watch?v=VIDEO_ID" \
  start_time="MM:SS" end_time="MM:SS" \
  known_speakers='["First Person","Second Person", ...]'
```

- Gemini listens to the actual audio and returns `{speaker, confidence}`. This is
  the only step that resolves ambiguity with **evidence** rather than text-guessing.
- It time-aligns to the YouTube upload — and a `yt-dlp`-fetched audio shares that
  timeline, so the same `MM:SS` works in both.
- Pick the window from the cluster's longest contiguous run (less crosstalk).
- If Gemini returns `unknown` / can't place it, it's likely audience/bleed.

## Expect diarization pathologies (all fixable)

- **Splits** — one person across 2+ clusters (a soft voice or mic changes split
  them). Merge by **resolved name** in the render step (Cell G keys turns on the
  *name*, not the cluster ID, so split clusters of the same person join up).
- **Garbage / end-of-file drift** — a small cluster that mixes voices: off-mic
  chatter + stragglers + sometimes a real speaker's closing words that got
  nearest-filled to a stray segment. Re-probe its *coherent* parts; relabel or
  leave `Unknown`. Don't assume a cluster is a single coherent voice.
- **`fill_nearest=True`** assigns the nearest diarization segment to unlabeled
  words, which is how stragglers (e.g. a host's closing line) can land in a
  garbage cluster.

## Verification posture

After mapping, sanity-check by reading the first and last few turns of the
rendered transcript: the host should open and close, attributions should match
who logically speaks when. A wrong cluster→name is usually obvious at the
boundaries (intro, handoffs, closing thanks).
