#!/usr/bin/env python3
"""Mistral Document QnA — ask natural-language questions about a document.

Sends a chat completion with the document as a `document_url` (or `image_url`)
content item. Stdlib only. Reads $MISTRAL_API_KEY.

    MISTRAL_API_KEY=<your-key> python3 qna.py report.pdf "What is the last sentence?"
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

CHAT_API = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL = "mistral-small-latest"
IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".avif"}


def doc_chunk(src: str) -> dict:
    """Build a chat content chunk pointing at the document."""
    if src.startswith(("http://", "https://")):
        lower = src.lower().split("?", 1)[0]
        kind = "image_url" if any(lower.endswith(e) for e in IMG_EXTS) else "document_url"
        return {"type": kind, kind: src}

    if not os.path.isfile(src):
        sys.exit(f"error: not a file: {src}")
    mime, _ = mimetypes.guess_type(src)
    mime = mime or "application/octet-stream"
    kind = "image_url" if mime.startswith("image/") else "document_url"
    with open(src, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    return {"type": kind, kind: f"data:{mime};base64,{b64}"}


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="qna.py",
        description="Ask a natural-language question about a document via Mistral chat.",
    )
    ap.add_argument("source", help="local file path or http(s) URL")
    ap.add_argument("question", help="question to ask about the document")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help="chat model (default: mistral-small-latest; use mistral-large-latest for hard reasoning)")
    ap.add_argument("--json", action="store_true", help="print the full raw API response")
    args = ap.parse_args()

    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        sys.exit("error: MISTRAL_API_KEY not set. Export it in your environment.")

    body = {
        "model": args.model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": args.question},
                doc_chunk(args.source),
            ],
        }],
    }

    req = urllib.request.Request(
        CHAT_API,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        sys.exit(f"error: HTTP {exc.code} from Mistral\n{detail}")
    except urllib.error.URLError as exc:
        sys.exit(f"error: request failed: {exc.reason}")

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    choices = data.get("choices", [])
    if not choices:
        sys.exit("error: no choices in response")
    print(choices[0].get("message", {}).get("content", ""))


if __name__ == "__main__":
    main()
