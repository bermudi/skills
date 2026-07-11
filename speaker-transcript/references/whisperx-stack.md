# WhisperX stack, API, and runbook cells

Verified live on Colab T4, 2026-07. API details are from `inspect.signature` on
the installed package — **do not trust memory**, the API has moved (see the bug
table).

## Verified stack

| Component | Version | Notes |
|---|---|---|
| numpy | **2.2.6** | Colab's stock numpy is too old for torch 2.8 (`_blas_supports_fpe`); pin it |
| torch | **2.8.0+cu128** | WhisperX pins `torch~=2.8`; install the **triple** together |
| torchvision | **0.23.0+cu128** | must match torch 2.8 (pairs: 2.8 ↔ 0.23) |
| torchaudio | **2.8.0+cu128** | matches torch 2.8 |
| whisperx | **3.8.7rc1** | `from whisperx.diarize import DiarizationPipeline` |
| pyannote community-1 | (default diarizer) | **gated** — accept license + `HF_TOKEN` |

## WhisperX API (from `inspect.signature`)

```python
import whisperx
from whisperx.diarize import DiarizationPipeline   # NOT whisperx.DiarizationPipeline

asr          = whisperx.load_model("large-v3", device="cuda", compute_type="float16")
align_model, align_meta = whisperx.load_align_model("en", device="cuda")
audio        = whisperx.load_audio(path)                      # (file, sr=16000) -> np.ndarray
result       = asr.transcribe(audio, batch_size=16, language="en")   # built-in VAD
result       = whisperx.align(result["segments"], align_model, align_meta, audio, device="cuda")
diarizer     = DiarizationPipeline(token=HF_TOKEN, device="cuda")    # token=, NOT use_auth_token=
diarize_df   = diarizer(audio, min_speakers=4, max_speakers=6)       # -> pandas.DataFrame
result       = whisperx.assign_word_speakers(diarize_df, result, fill_nearest=True)
```

- `DiarizationPipeline.__init__(model_name=None, token=None, device='cpu', cache_dir=None)`
- `DiarizationPipeline.__call__(audio, num_speakers=None, min_speakers=None, max_speakers=None, return_embeddings=False, ...) -> DataFrame`
- After `assign_word_speakers`, each `result["segments"][i]["words"][j]` has
  `start / end / word / speaker`.
- **Word tokens are bare** (no leading spaces). Build turn text with
  `" ".join(...)`.
- `whisperx` has **no `__version__`** attribute (don't probe it).

## Runbook cells

Drive these by `update_cell` + `run_code_cell` on a scratch cell (see
`colab-mcp-playbook.md`). Long cells use `--timeout 900000`.

### Cell A — install (no imports yet), then restart
```python
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
   "numpy==2.2.6", "torch==2.8.0", "torchvision==0.23.0",
   "torchaudio==2.8.0", "whisperx", "yt-dlp"])
print("INSTALL DONE — restart next")
```
Then restart: `import os; os.kill(os.getpid(), 9)` in its own cell, wait ~12 s,
reconnect if needed, then run Cell B.

### Cell B — verify the coherent stack + creds
```python
import numpy as np, torch, torchvision
print("numpy", np.__version__, "| torch", torch.__version__,
      "| torchvision", torchvision.__version__)
assert torch.cuda.is_available(), "NO GPU — Runtime → Change runtime type → T4"
import whisperx
from whisperx.diarize import DiarizationPipeline
from google.colab import userdata
HF_TOKEN = userdata.get("HF_TOKEN"); assert HF_TOKEN and len(HF_TOKEN) > 10
print("READY", torch.cuda.get_device_name(0))
```

### Cell C — load models (`--timeout 600000`; ~4 GB weights first run)
```python
import whisperx, time
from whisperx.diarize import DiarizationPipeline
from google.colab import userdata
HF_TOKEN = userdata.get("HF_TOKEN"); t0=time.time()
asr_model = whisperx.load_model("large-v3", device="cuda", compute_type="float16")
align_model, align_meta = whisperx.load_align_model("en", device="cuda")
diarize_pipeline = DiarizationPipeline(token=HF_TOKEN, device="cuda")
print(f"{time.time()-t0:.0f}s ALL MODELS LOADED")
```

### Cell D — acquire audio (yt-dlp) + resample
```python
import subprocess, os, time
VIDEO_URL="https://www.youtube.com/watch?v=VIDEO_ID"   # or upload to /content/ and set raw=that
WORK="/content/work"; os.makedirs(WORK, exist_ok=True)
raw=os.path.join(WORK,"src.m4a"); WAV16=os.path.join(WORK,"audio_16k_mono.wav")
t0=time.time()
if not os.path.exists(raw):
    subprocess.run(["yt-dlp","-f","bestaudio","-x","--audio-format","m4a","-o",raw,VIDEO_URL], check=True)
subprocess.run(["ffmpeg","-y","-i",raw,"-ac","1","-ar","16000","-c:a","pcm_s16le",WAV16],
               check=True, capture_output=True)
print(f"{time.time()-t0:.0f}s {WAV16} ({os.path.getsize(WAV16)/1e6:.1f} MB)")
```

### Cell E — transcribe + align (`--timeout 900000`)
```python
import whisperx, time
t0=time.time()
audio = whisperx.load_audio(WAV16)
result = asr_model.transcribe(audio, batch_size=16, language="en")
result = whisperx.align(result["segments"], align_model, align_meta, audio, device="cuda")
n = sum(len(s.get("words",[])) for s in result["segments"])
print(f"{time.time()-t0:.0f}s | {len(result['segments'])} segs | {n} words")
```

### Cell F — diarize + assign + build word list (`--timeout 900000`)
```python
import time
t0=time.time()
diarize_df = diarize_pipeline(audio, min_speakers=4, max_speakers=6)
result = whisperx.assign_word_speakers(diarize_df, result, fill_nearest=True)
labels = sorted(diarize_df["speaker"].unique())
print(f"{time.time()-t0:.0f}s | {len(labels)} clusters {labels}")
words=[]
for seg in result["segments"]:
    for w in seg.get("words",[]):
        s=w.get("start"); e=w.get("end",s)
        if s is None: continue
        words.append({"start":float(s),"end":float(e),"text":w.get("word",""),"speaker":w.get("speaker")})
print(f"{sum(1 for w in words if w['speaker'])}/{len(words)} labeled")
```

### Cell G — render (fill SPEAKER_MAP from `name-mapping.md`)
```python
import json, datetime, os
from collections import defaultdict
SPEAKER_MAP = {"SPEAKER_00":"<Name>", ...}   # re-derive EVERY run; merge splits here
def name_of(l): return SPEAKER_MAP.get(l, l)
def fmt_t(s): s=max(0,int(round(s))); return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"
GAP_S=1.0; turns=[]; cur=None
for w in sorted(words, key=lambda x:x["start"]):
    sp=name_of(w["speaker"])
    if cur and cur["speaker"]==sp and (w["start"]-cur["end"])<=GAP_S:
        cur["end"]=w["end"]; cur["w"].append(w["text"])
    else:
        if cur: turns.append(cur)
        cur={"speaker":sp,"start":w["start"],"end":w["end"],"w":[w["text"]]}
if cur: turns.append(cur)
for t in turns: t["text"]=" ".join(t["w"]).strip()
WORK="/content/work"; NAME="output-slug"
json.dump([{"speaker":t["speaker"],"start":t["start"],"end":t["end"],"text":t["text"]}
           for t in turns], open(f"{WORK}/{NAME}.json","w"), indent=2)
open(f"{WORK}/{NAME}.txt","w").write("\n".join(
    f"[{fmt_t(t['start'])}] {t['speaker']}: {t['text']}" for t in turns))
print("turns", len(turns))
```
Then **immediately** run `scripts/pull_colab_output.sh` (Rule 1 in SKILL.md).

## Bug table

| Symptom | Cause | Fix |
|---|---|---|
| `numpy._core._multiarray_umath has no attribute '_blas_supports_fpe'` | Colab's numpy too old for torch 2.8 | pin `numpy==2.2.6` in the install; restart kernel |
| `operator torchvision::nms does not exist` | torch upgraded, torchvision left on old ABI | install the torch/torchvision/torchaudio triple together; restart |
| `module 'whisperx' has no attribute 'DiarizationPipeline'` | not exported in `__init__` (3.8.7rc1) | `from whisperx.diarize import DiarizationPipeline` |
| `unexpected keyword argument 'use_auth_token'` | ctor param renamed | `DiarizationPipeline(token=..., device=...)` |
| `module 'whisperx' has no attribute '__version__'` | it just doesn't | don't probe it |
| `403 GatedRepoError … community-1` | license not accepted | accept at the HF model card (same account as the token); sub-models can also be gated — the error names the URL |
| New Colab window + "Connect" mid-run | mcporter 120 s timeout killed a long `run_code_cell` → bridge dropped → `open_colab_browser_connection` spawned a window | long `--timeout`; don't reconnect after a timeout (see playbook) |
| `py_compile` passed but runtime `AttributeError` | syntax check ≠ API check | `inspect.signature` the installed package; smoke-import |

If versions drift (Colab updates its base image), re-derive the working set the
same way: `inspect.signature` the API, pin a coherent torch/numpy triple, restart
after install.
