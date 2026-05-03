# bermudi's Model Reference

A living reference for bermudi's favorite Poe models — how to discover them, what they support, and how to verify they still work.

---

## Model Families

These are the families he tracks closely. Within each family, newer models appear on Poe over time. The probe script automatically discovers the latest by inspecting `/v1/models`.

| Family | Provider | Current Examples | Model ID Pattern |
|--------|----------|-----------------|------------------|
| **Kimi** | Moonshot AI | `Kimi-K2.5`, `Kimi-K2.6` | `Kimi-K*` |
| **DeepSeek** | DeepSeek | `DeepSeek-V4-Pro-EL`, `DeepSeek-V4-Flash-EL`, `DeepSeek-V4-Pro-T` | `DeepSeek-V4-*` |
| **GLM** | Zhipu AI | `GLM-5`, `GLM-5.1-FW`, `GLM-5.1-T` | `GLM-5*` |
| **MiniMax** | MiniMax | `Minimax-M2.7`, `MiniMax-M2.7-HS`, `Minimax-M2.7-FW`, `Minimax-M2.7-T` | `Mini*max-M2.7*` |

### Discovering the Latest Model in a Family

```bash
# Fetch all models and filter by family
curl -s "https://api.poe.com/v1/models" \
  -H "Authorization: Bearer $POE_API_KEY" \
  | jq '.data[] | select(.id | startswith("Kimi-K")) | .id'
```

The probe script does this automatically — it reads each model's full schema from `/v1/models` including:
- `supported_endpoints` — which APIs the model works with
- `supported_features` — capabilities like tool calling, vision, etc.
- `parameter_schema` — the parameters the model declares (types, enums, maximums)

### When a New Family Member Appears

1. Run `uv run python research/model_probe.py` to test all current models
2. Check the output for any models that appeared since last run
3. If a new model follows the family pattern (e.g., `Kimi-K2.7`), add it to `BERMUDI_MODELS` in `research/model_probe.py`
4. Re-run and update this document's results table

---

## Thinking Parameters

Different models expose thinking/reasoning control through different parameter names in their Chat Completions schema. You can discover them by inspecting `/v1/models`:

```bash
curl -s "https://api.poe.com/v1/models" \
  -H "Authorization: Bearer $POE_API_KEY" \
  | jq '[.data[] | {id, thinking: (.parameter_schema // {} | to_entries | map(select(.key | test("think|reason|effort"; "i"))) | from_entries)}] | map(select(.thinking | length > 0))'
```

Common thinking parameter patterns:

| Parameter | Models | Type | Values |
|-----------|--------|------|--------|
| `enable_thinking` | Kimi, DeepSeek, MiniMax, GLM | boolean | `true` / `false` |
| `thinking` | Some newer models | object/string | varies |

Send these via `extra_body` with the OpenAI SDK:

```python
client.chat.completions.create(
    model="Kimi-K2.6",
    messages=[{"role": "user", "content": "..."}],
    extra_body={"enable_thinking": True}
)
```

The `extra_body` parameter works because these fields are **declared in the model's parameter schema** at `/v1/models`. Poe's strict validation only rejects fields the model doesn't declare.

---

## Probe Results

> **Last updated:** 2026-05-02
>
> Run: `uv run python research/model_probe.py`

### Legend

- ✅ PASS — feature works as expected
- ❌ FAIL — feature does not work (error details in notes)
- 💭 Thinking — parameters declared in model schema
- ⚠️ Not in catalog — model not listed in `/v1/models` but still accessible (catalog status noted in Notes column)
- 🚫 404 — API returns 404, model genuinely unavailable

### Chat Completions API

| Model | Tool Calling | Multi-turn Memory | Thinking Params | Notes |
|-------|:---:|:---:|------|-------|
| DeepSeek-V4-Pro-EL | ❌ FAIL | ✅ PASS | `enable_thinking`, `thinking_budget` | Tool calling returns 500 — Poe-side issue despite `tools` feature flag |
| DeepSeek-V4-Flash-EL | ❌ FAIL | ✅ PASS | `enable_thinking`, `thinking_budget` | Same 500 on tool calling as Pro-EL |
| MiMo-V2.5-Pro | ✅ PASS | ✅ PASS | `deep_thinking` | |
| MiniMax-M2.7-HS | ✅ PASS | ✅ PASS | — | ⚠️ Not in `/v1/models` catalog |
| Kimi-K2.6 | ✅ PASS | ✅ PASS | `enable_thinking` | |
| Minimax-M2.7 | ✅ PASS | ✅ PASS | — | |
| GLM-5 | ✅ PASS | ✅ PASS | `enable_thinking` | |
| Kimi-K2.5 | ✅ PASS | ✅ PASS | `enable_thinking` | |
| Minimax-M2.7-FW | ✅ PASS | ✅ PASS | — | |
| GLM-5.1-FW | ✅ PASS | ✅ PASS | — | |
| GLM-5.1-FWAI | 🚫 404 | 🚫 404 | — | API returns 404 — genuinely unavailable. |
| Kimi-K2.5-FW | ✅ PASS | ✅ PASS | — | |
| DeepSeek-V4-Pro-T | ❌ FAIL | ❌ FAIL | — | No tool support (400). Multi-turn timed out. |
| Kimi-K2.6-T | ❌ FAIL | ❌ FAIL | — | ⚠️ Not in catalog. No tool support (400). Multi-turn timed out (thinking model). |
| Minimax-M2.7-T | ❌ FAIL | ❌ FAIL | — | ⚠️ Not in catalog. No tool support (400). Multi-turn timed out (thinking model). |
| GLM-5.1-T | ❌ FAIL | ❌ FAIL | — | No tool support (400). Multi-turn: remembered context but got stuck in thinking loop. |
| GLM-5-T | ❌ FAIL | ❌ FAIL | — | No tool support (400). Multi-turn timed out. |
| Kimi-K2.5-Tog | ❌ FAIL | ❌ FAIL | — | No tool support (400). Multi-turn timed out. |

---

## Re-Running the Probe

### Prerequisites

```bash
export POE_API_KEY=poe-xxxxx-your-key-here
```

### Run All Models

```bash
uv run python research/model_probe.py
```

This takes ~10-12 minutes (18 models × 2 probes = 36 API calls + catalog fetch).

### Run Specific Models

```bash
uv run python research/model_probe.py --models Kimi-K2.6,GLM-5,DeepSeek-V4-Pro-EL
```

### Skip Live Thinking Test (Faster)

```bash
uv run python research/model_probe.py --no-thinking-test
```

The thinking parameter test tries to send each declared parameter directly in the request body. Since `extra_body` is an OpenAI SDK concept (not a raw HTTP field), the live test injects the parameter as a top-level JSON field. If the model declares it, strict mode should accept it.

### Output

- **Terminal**: Summary table with pass/fail per model
- **File**: `research/model_probe_results.json` — full detailed results including:
  - Model catalog info (endpoints, features, pricing)
  - Raw request/response for each probe stage
  - Error details for failures
  - Thinking parameter schemas

### Adding New Models

Edit `BERMUDI_MODELS` in `research/model_probe.py` and add the model name exactly as it appears in `/v1/models`.

### When Models Disappear or Change

If a model moves or is renamed:
1. Check `/v1/models` for the current name
2. Update `BERMUDI_MODELS` in the probe script
3. Re-run and update this document
4. If a model now `FAIL`s a probe that previously `PASS`ed, investigate — Poe may have changed something

### Models Not in /v1/models Catalog

Some models work via the API even though they don't appear in the `/v1/models` listing:
- `MiniMax-M2.7-HS` — ✅ works (tool calling + multi-turn both pass)
- `Kimi-K2.6-T` — ❌ no tool support, multi-turn times out (thinking model)
- `Minimax-M2.7-T` — ❌ no tool support, multi-turn times out (thinking model)
- `GLM-5.1-FWAI` — ❌ API returns 404 (model not available)

The probe script now tries all models regardless of catalog presence. Only models returning 404 are truly unavailable.

---

## Probe Design

### Tool Calling Probe

1. Send: "What is the destination for ticket ZX-81? Use the lookup_trip tool."
2. Force `tool_choice` to `lookup_trip`
3. Expect model to call `lookup_trip` with `ticket_id="ZX-81"`
4. Send tool result: `{"destination": "Lisbon", ...}`
5. Expect model response to mention "Lisbon"

**What it validates:** Tool call format, correct argument passing, tool result incorporation.

### Multi-turn Memory Probe

1. Turn 1: "Remember this codeword: GLACIER-17. Reply with exactly READY."
2. Turn 2: Send full message history (user + assistant + user followup)
3. Followup: "What codeword did I ask you to remember?"
4. Expect response: "GLACIER-17"

**What it validates:** Message history roundtrip, context retention across turns.

**⚠️ `-T` and `-Tog` variants:** These are thinking/reasoning models that don't expose thinking control via Chat Completions parameters. They time out on trivial requests because their internal reasoning process exceeds the probe's 120s timeout. They're not suitable for fast agentic loops — use them for single-turn deep reasoning instead.

### Thinking Parameter Discovery

1. Read `/v1/models` for each model's `parameter_schema`
2. Extract parameters whose names match `think`, `reason`, `effort`, or `budget`
3. Optionally test live: send parameter as top-level body field, check if accepted

**What it validates:** Which thinking controls each model declares, and whether Poe accepts them under strict mode.
