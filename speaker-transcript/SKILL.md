---
name: speaker-transcript
description: Turn a multi-speaker recording (panel, podcast, interview, any audio/video with two or more voices) into a timestamped transcript with named speakers. Use when the user wants speaker labels or diarization ("who said what", "add speaker names", "which voice is which"), or gives a YouTube link / audio / video file and wants it turned into a speaker-attributed transcript. For plain single-voice transcription, use the media skill instead.
disable-model-invocation: true
---

# Speaker-attributed transcripts (WhisperX on Colab)

Turn a multi-speaker recording into a **timestamped transcript with named
speakers** — i.e. resolve *who said what*, not just the words.

```
audio → 16kHz mono → faster-whisper (ASR + word timestamps + VAD)
                   → wav2vec2 forced alignment (tight word boundaries)
                   → pyannote community-1 diarization (speaker turns)
                   → assign_word_speakers (word ↔ speaker by overlap)
                   → cluster → name → .md / .txt (readable) + .json (structured turns)
```

Runs on a Colab T4 GPU (~10–15 min compute for ~1 hr audio), driven remotely via
the **colab-mcp** bridge (`mcporter call colab-mcp.<tool>`). The notebook in
`assets/diarize-panel.ipynb` is the standalone equivalent.

## When to use / when not to

- **Use** when there are 2+ speakers and the user needs speaker labels or
  diarization (who said what).
- **Skip** for a single speaker, or when only raw text is needed — that's the
  `media` skill (Gemini transcription, no diarization, much faster, no Colab).

## Local hardware constraint (why this skill runs on Colab, not locally)

**Never run WhisperX/pyannote locally on this machine.** The GPU is a GTX 1060 (Pascal, sm_61); modern torch ships no CUDA kernels for it, so diarization falls back to CPU and pegs every core for ~1 hr per file. Compute belongs on Colab. (This scopes to the ML pipeline — Tier 0 LLM reading of a transcript is local and fine.)

## The five critical rules (these all cost real time — read first)

Each is expanded in a reference; they're here so you don't hit them cold.

### 1. Never leave the only copy in Colab. Extract the instant rendering finishes.
Colab free runtimes disconnect on idle — and **flagging the risk then asking the
user is not enough** (that exact mistake lost a completed 55-min transcript
once). The render step and the extract step are one unit of work. Run
`scripts/pull_colab_output.sh` the moment the `.json` is written, then save it
locally (and commit, if it's going into a repo). Treat the Colab VM as volatile.

### 2. Long cells need a long mcporter timeout (and never "recover" a timeout by reconnecting).
`run_code_cell` **blocks** until the cell finishes. mcporter's default per-call
timeout is **120 s**; a transcribe/diarize cell runs minutes, so mcporter kills
the call, which tears down the bridge. If you then call
`open_colab_browser_connection` to recover, its implementation runs
`webbrowser.open_new(...)` and **spawns a new Colab window + forces a "Connect"
click**.
- Use `--timeout 900000` (15 min) for any cell that runs >~60 s. Set the shell
  (`bash`) timeout a bit higher than mcporter's, in seconds (e.g. 960).
- After a timed-out call, **poll with `get_cells`**, do not call
  `open_colab_browser_connection`.
- Details + the source reference: `references/colab-mcp-playbook.md`.

### 3. The environment needs a numpy pin AND a kernel restart.
WhisperX pins `torch~=2.8`. On a fresh Colab runtime, `import torch` (2.8.0)
dies against Colab's stock numpy: `module 'numpy._core._multiarray_umath' has no
attribute '_blas_supports_fpe'` (numpy too old). Fix: install the coherent
torch/torchvision/torchaudio triple **plus** `numpy==2.2.6` in one pip command,
then restart the kernel (`os.kill(os.getpid(), 9)` — the bridge survives it),
then re-probe the import. The old numpy is already in `sys.modules`, so a
restart is mandatory; reinstalling is not enough. Verified versions + the exact
cells + bug table: `references/whisperx-stack.md`.

### 4. After any disconnect, the editing tools are gated.
Reconnect with `open_colab_browser_connection`, then **wait ~10 s and re-`list`**.
Until the browser front-end reconnects, `mcporter list colab-mcp` shows only
`open_colab_browser_connection` and every other tool (`run_code_cell`,
`update_cell`, …) is "Unknown tool". Don't call them before they appear.
Procedure + how to drive a kernel restart: `references/colab-mcp-playbook.md`.

### 5. Diarization cluster IDs are NOT stable across runs.
`SPEAKER_00` in one run is not `SPEAKER_00` in the next — the IDs permute. **Re-
derive the cluster→name mapping every run** from content + elimination; never
reuse a prior run's `SPEAKER_MAP`. With N known panelists, the (N+1)th cluster is
audience/announcer by definition (no confirmation needed). Details + how to
confirm an uncertain cluster from the real audio: `references/name-mapping.md`.

## Workflow

### 0. Source + speakers
- **Source**: a YouTube URL is easiest — `yt-dlp` fetches the audio in-notebook
  (reproducible, no manual upload). A local file works too (user uploads to
  `/content/` via the Colab Files panel).
- **Speaker names**: get them up front from the title/description/byline. You
  need them for cluster→name. Count them; pass `min_speakers`/`max_speakers`
  with headroom (e.g. known+2) for an announcer / audience Q&A.

### 1. Provision Colab
Read `references/colab-mcp-playbook.md`. Connect, confirm the **8 tools are
visible** (`mcporter list colab-mcp`), confirm a **GPU runtime** is attached.

### 2. Environment (numpy + torch triple + whisperx + yt-dlp), restart, verify
Read `references/whisperx-stack.md` for the exact install + restart + verify
cells and the verified WhisperX API.

### 3. Load models + acquire audio
Load the three models (ASR, align, diarizer). `yt-dlp` → m4a → `ffmpeg` to 16 kHz
mono wav. Confirm the `HF_TOKEN` Colab secret is set **and** the user has accepted
the `pyannote/speaker-diarization-community-1` model-card license (else 403
GatedRepoError; sub-models can also be gated — the error names the URL).

### 4. Transcribe + align (long cell, `--timeout 900000`)
### 5. Diarize + assign (long cell, `--timeout 900000`)
The exact cells are in `references/whisperx-stack.md`.

### 6. Map clusters → names
Read `references/name-mapping.md`. Print per-cluster evidence (talk time + first
~35 words), resolve by self-intro + **elimination**, and only Gemini-confirm the
genuinely uncertain clusters. Merge splits by resolved name in the render step.

### 7. Render
Merge words into turns (split on resolved-name change or gap > ~1 s), build turn
text with `" ".join(word_tokens)` (tokens are bare — no spaces), write
`.md` / `.txt` / `.json` to `/content/work/`. Cell in `references/whisperx-stack.md`.

### 8. EXTRACT — do not skip (Rule 1)
```bash
bash scripts/pull_colab_output.sh /content/work/<name>.json  <local_dest>.json
bash scripts/pull_colab_output.sh /content/work/<name>.txt   <local_dest>.txt
```
Then save/commit locally. The `.json` (structured turns
`[{speaker, start, end, text}]`) is the canonical artifact — `.md`/`.txt`
regenerate from it.

## Known limitations
- **ASR mishears proper names** (e.g. "Isger"/"Isberg" = Isgur, "Bruin" = Bruen).
  These are transcription artifacts, not attribution errors — note the variants
  in a header so a reader (or later filing) isn't confused.
- **A small "garbage" cluster** mixing off-mic bleed + end-of-file stragglers is
  common. Label it `Unknown`; re-probe its coherent parts if attribution there
  matters.
- Diarization can't find more voices than `max_speakers`; leave headroom.

## Files in this skill
- `scripts/pull_colab_output.sh` — chunked base64 extraction from Colab (Rule 1).
- `references/colab-mcp-playbook.md` — connect, tool gating, timeout trap, kernel
  restart, polling, cell management.
- `references/whisperx-stack.md` — verified versions, the WhisperX API (from
  `inspect.signature`), the runbook cells, bug table.
- `references/name-mapping.md` — heuristics, elimination, Gemini confirmation,
  splits, garbage clusters, cluster-ID instability.
- `assets/diarize-panel.ipynb` — the standalone Colab notebook.
