# Large Files — Use the Files API

Inline `data:` URIs (what `scripts/mistral_ocr.py` uses by default) suit typical
documents. For large PDFs, upload first and feed the signed URL back to the OCR
endpoint.

## Three-step pattern

```bash
# 1. upload (purpose MUST be "ocr")
FILE_ID=$(curl -s https://api.mistral.ai/v1/files \
  -H "Authorization: Bearer $MISTRAL_API_KEY" \
  -F purpose=ocr -F file=@big.pdf \
  | uv run python -c 'import sys,json;print(json.load(sys.stdin)["id"])')

# 2. get a signed URL
URL=$(curl -s "https://api.mistral.ai/v1/files/$FILE_ID/url" \
  -H "Authorization: Bearer $MISTRAL_API_KEY" \
  | uv run python -c 'import sys,json;print(json.load(sys.stdin)["url"])')

# 3. OCR the signed URL (the script accepts URLs directly)
uv run scripts/mistral_ocr.py "$URL"
```

Signed URLs expire — use them immediately, don't cache them.

## For large-scale OCR

For batch workloads, use Mistral's Batch Inference service — cheaper and
parallel — rather than looping the OCR API directly.
