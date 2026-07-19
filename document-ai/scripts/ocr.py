#!/usr/bin/env python3
"""Mistral Document AI — OCR + structured extraction in a single command.

Stdlib only. The API key is read from $MISTRAL_API_KEY:

    MISTRAL_API_KEY=<your-key> python3 ocr.py invoice.pdf

Defaults to printing extracted markdown. Use --prompt/--schema for whole-document
structured extraction, --bbox (with a JSON Schema) for per-image annotations,
--images to pull out embedded figures, --blocks for paragraph-level bounding
boxes, --json for the raw response.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://api.mistral.ai/v1/ocr"
DEFAULT_MODEL = "mistral-ocr-latest"
IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".avif"}
TABLE_FORMATS = {"null", "markdown", "html"}
CONFIDENCE_GRANULARITIES = {"page", "word"}


def doc_payload(src: str) -> dict:
    """Build the `document` payload from a local path or an http(s) URL.

    Mistral has no `base64` document type — files go in as `data:` URIs. Images
    use `image_url`; everything else (PDF, DOCX, PPTX, etc.) uses `document_url`.
    """
    if src.startswith(("http://", "https://")):
        lower = src.lower().split("?", 1)[0]
        kind = "image_url" if any(lower.endswith(e) for e in IMG_EXTS) else "document_url"
        return {kind: src, "type": kind}

    if not os.path.isfile(src):
        sys.exit(f"error: not a file: {src}")
    mime, _ = mimetypes.guess_type(src)
    mime = mime or "application/octet-stream"
    kind = "image_url" if mime.startswith("image/") else "document_url"
    with open(src, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    return {kind: f"data:{mime};base64,{b64}", "type": kind}


def call(url: str, body: dict, key: str) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        sys.exit(f"error: HTTP {exc.code} from Mistral\n{detail}")
    except urllib.error.URLError as exc:
        sys.exit(f"error: request failed: {exc.reason}")


def schema_to_format(schema: dict, name_hint: str) -> dict:
    """Wrap a JSON Schema into the API's `*_annotation_format` shape."""
    name = re.sub(r"[^a-z0-9]+", "_", str(schema.get("title", name_hint)).lower()).strip("_") or name_hint
    return {
        "type": "json_schema",
        "json_schema": {"name": name, "schema": schema, "strict": True},
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="ocr.py",
        description="OCR a document (file or URL) with Mistral Document AI.",
    )
    ap.add_argument("source", help="local file path or http(s) URL")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--pages", help="page subset, e.g. '0-4' or '0,2,5' (0-indexed)")
    ap.add_argument("--images", action="store_true", help="include extracted figures as base64")
    ap.add_argument("--blocks", action="store_true", help="include paragraph-level bounding boxes (OCR 4+)")
    ap.add_argument("--header", action="store_true", help="populate each page's header field (OCR 2512+)")
    ap.add_argument("--footer", action="store_true", help="populate each page's footer field (OCR 2512+)")
    ap.add_argument("--table-format", choices=sorted(TABLE_FORMATS), default="null",
                    help="emit tables separately as markdown/html (OCR 2512+)")
    ap.add_argument("--confidence", choices=sorted(CONFIDENCE_GRANULARITIES),
                    help="return confidence scores at page or word granularity")
    ap.add_argument("--prompt", help="prompt for whole-document structured extraction (needs --schema)")
    ap.add_argument("--schema", help="path to a JSON Schema for --prompt output")
    ap.add_argument("--bbox", help="path to a JSON Schema for per-image (bbox) annotation (implies --images)")
    ap.add_argument("--json", action="store_true", help="print the full raw API response")
    ap.add_argument("-o", "--out", help="write markdown to this file instead of stdout")
    args = ap.parse_args()

    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        sys.exit("error: MISTRAL_API_KEY not set. Export it in your environment.")

    body: dict = {"model": args.model, "document": doc_payload(args.source)}
    if args.pages:
        body["pages"] = args.pages
    if args.images or args.bbox:
        body["include_image_base64"] = True
    if args.blocks:
        body["include_blocks"] = True
    if args.header:
        body["extract_header"] = True
    if args.footer:
        body["extract_footer"] = True
    if args.table_format and args.table_format != "null":
        body["table_format"] = args.table_format
    if args.confidence:
        body["confidence_scores_granularity"] = args.confidence

    if args.schema and not args.prompt:
        sys.exit("error: --schema is only used with --prompt (whole-document structured extraction)")

    if args.prompt:
        if not args.schema:
            sys.exit("error: --prompt requires --schema (a JSON Schema for the extraction)")
        with open(args.schema) as fh:
            schema = json.load(fh)
        body["document_annotation_format"] = schema_to_format(schema, "document_annotation")
        body["document_annotation_prompt"] = args.prompt

    if args.bbox:
        with open(args.bbox) as fh:
            bbox_schema = json.load(fh)
        body["bbox_annotation_format"] = schema_to_format(bbox_schema, "bbox_annotation")

    resp = call(API, body, key)

    def emit(text: str, label: str) -> None:
        if args.out:
            with open(args.out, "w") as fh:
                fh.write(text + "\n")
            print(f"wrote {label} -> {args.out}", file=sys.stderr)
        else:
            print(text)

    if args.json:
        emit(json.dumps(resp, ensure_ascii=False, indent=2), "raw response")
        return

    if args.prompt:
        ann = resp.get("document_annotation")
        if isinstance(ann, str):
            try:
                ann = json.loads(ann)
            except ValueError:
                pass
        emit(json.dumps(ann, ensure_ascii=False, indent=2) if ann is not None else "",
             "document annotation")
        return

    if args.bbox:
        # Bbox annotations land in `image_annotation` on each image in `pages[].images[]`,
        # returned as JSON strings.
        annotations = []
        for page in resp.get("pages", []):
            for img in page.get("images", []):
                ann = img.get("image_annotation")
                if ann is None:
                    continue
                if isinstance(ann, str):
                    try:
                        ann = json.loads(ann)
                    except ValueError:
                        pass
                annotations.append(ann)
        emit(json.dumps(annotations, ensure_ascii=False, indent=2), "bbox annotations")
        return

    pages = resp.get("pages", [])
    md = "\n\n---\n\n".join(page.get("markdown", "") for page in pages)
    emit(md, f"{len(pages)} page(s)")


if __name__ == "__main__":
    main()
