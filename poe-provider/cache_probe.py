from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASE_URL = "https://api.poe.com"
API_KEY = os.environ["POE_API_KEY"]
FIXTURE_PATH = Path(__file__).with_name("test_file.txt")
OUTPUT_PATH = Path(__file__).with_name("cache_probe_results.json")


@dataclass
class HttpResult:
    status: int
    headers: dict[str, str]
    body: Any
    raw_text: str


def normalize_model_name(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def api_request(method: str, path: str, *, headers: dict[str, str] | None = None, payload: Any | None = None, timeout: int = 60) -> HttpResult:
    req_headers = dict(headers or {})
    data: bytes | None = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = raw
            return HttpResult(
                status=response.status,
                headers={k.lower(): v for k, v in response.headers.items()},
                body=body,
                raw_text=raw,
            )
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = raw
        return HttpResult(
            status=error.code,
            headers={k.lower(): v for k, v in error.headers.items()},
            body=body,
            raw_text=raw,
        )


def get_balance() -> int:
    result = api_request(
        "GET",
        "/usage/current_balance",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30,
    )
    if result.status != 200:
        raise RuntimeError(f"Balance request failed: {result.status} {result.raw_text}")
    return int(result.body["current_point_balance"])


def get_points_history(limit: int = 100) -> list[dict[str, Any]]:
    result = api_request(
        "GET",
        f"/usage/points_history?limit={limit}",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30,
    )
    if result.status != 200:
        raise RuntimeError(f"Points history request failed: {result.status} {result.raw_text}")
    return list(result.body.get("data", []))


def get_models() -> dict[str, dict[str, Any]]:
    result = api_request(
        "GET",
        "/v1/models",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30,
    )
    if result.status != 200:
        raise RuntimeError(f"Models request failed: {result.status} {result.raw_text}")
    return {item["id"]: item for item in result.body.get("data", [])}


def estimate_cost_from_usage(usage: dict[str, Any], pricing: dict[str, Any]) -> dict[str, Any]:
    prompt_price = float(pricing["prompt"]) if pricing.get("prompt") not in (None, "null") else None
    completion_price = float(pricing["completion"]) if pricing.get("completion") not in (None, "null") else None
    cache_read_price = float(pricing["input_cache_read"]) if pricing.get("input_cache_read") not in (None, "null") else None
    cache_write_price = float(pricing["input_cache_write"]) if pricing.get("input_cache_write") not in (None, "null") else None

    result: dict[str, Any] = {
        "pricing": pricing,
        "estimated_usd": None,
        "formula": None,
        "token_breakdown": {},
    }

    if not isinstance(usage, dict):
        return result

    if "prompt_tokens" in usage:
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        cached_tokens = int((usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0))
        uncached_tokens = prompt_tokens - cached_tokens
        estimated_usd = (
            uncached_tokens * (prompt_price or 0.0)
            + cached_tokens * (cache_read_price if cache_read_price is not None else (prompt_price or 0.0))
            + completion_tokens * (completion_price or 0.0)
        )
        result["estimated_usd"] = estimated_usd
        result["formula"] = "openai_chat_usage"
        result["token_breakdown"] = {
            "prompt_tokens": prompt_tokens,
            "cached_tokens": cached_tokens,
            "uncached_prompt_tokens": uncached_tokens,
            "completion_tokens": completion_tokens,
        }
        return result

    if "cache_creation_input_tokens" in usage or "cache_read_input_tokens" in usage:
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        cache_read_tokens = int(usage.get("cache_read_input_tokens", 0))
        cache_write_tokens = int(usage.get("cache_creation_input_tokens", 0))
        uncached_input_rate = prompt_price or 0.0
        cache_write_rate = cache_write_price if cache_write_price is not None else uncached_input_rate
        cache_read_rate = cache_read_price if cache_read_price is not None else uncached_input_rate
        output_rate = completion_price or 0.0
        estimated_usd = (
            input_tokens * uncached_input_rate
            + cache_read_tokens * cache_read_rate
            + cache_write_tokens * cache_write_rate
            + output_tokens * output_rate
        )
        result["estimated_usd"] = estimated_usd
        result["formula"] = "anthropic_usage"
        result["token_breakdown"] = {
            "input_tokens": input_tokens,
            "cache_read_input_tokens": cache_read_tokens,
            "cache_creation_input_tokens": cache_write_tokens,
            "output_tokens": output_tokens,
        }
        return result

    if "input_tokens" in usage:
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
        cached_tokens = int(details.get("cached_tokens", 0))
        uncached_tokens = input_tokens - cached_tokens
        estimated_usd = (
            uncached_tokens * (prompt_price or 0.0)
            + cached_tokens * (cache_read_price if cache_read_price is not None else (prompt_price or 0.0))
            + output_tokens * (completion_price or 0.0)
        )
        result["estimated_usd"] = estimated_usd
        result["formula"] = "openai_responses_usage"
        result["token_breakdown"] = {
            "input_tokens": input_tokens,
            "cached_tokens": cached_tokens,
            "uncached_input_tokens": uncached_tokens,
            "output_tokens": output_tokens,
        }
        return result

    return result


def wait_for_new_history_entry(existing_ids: set[str], model: str, *, timeout_seconds: int = 40) -> dict[str, Any] | None:
    normalized_model = normalize_model_name(model)
    deadline = time.time() + timeout_seconds
    candidate: dict[str, Any] | None = None
    candidate_id: str | None = None
    while time.time() < deadline:
        history = get_points_history(limit=20)
        unseen = [item for item in history if item.get("query_id") not in existing_ids]
        if unseen and candidate is None:
            for item in unseen:
                if normalize_model_name(item.get("bot_name", "")) == normalized_model:
                    candidate = item
                    candidate_id = item.get("query_id")
                    break
            if candidate is None:
                candidate = unseen[0]
                candidate_id = candidate.get("query_id")

        if candidate_id is not None:
            for item in history:
                if item.get("query_id") == candidate_id:
                    candidate = item
                    cost_points = item.get("cost_points")
                    breakdown = item.get("cost_breakdown_in_points") or {}
                    if cost_points not in (None, 0) or breakdown:
                        return item
        time.sleep(2)
    return candidate


def output_text_preview(endpoint: str, body: Any) -> str | None:
    try:
        if endpoint == "messages":
            parts = []
            for item in body.get("content", []):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
            return " ".join(parts).strip() or None
        if endpoint == "chat_completions":
            return body["choices"][0]["message"].get("content")
        if endpoint == "responses":
            if isinstance(body.get("output_text"), str):
                return body.get("output_text")
            output = body.get("output", [])
            texts: list[str] = []
            for item in output:
                for content in item.get("content", []):
                    if content.get("type") in {"output_text", "text"}:
                        texts.append(content.get("text", ""))
            return " ".join(texts).strip() or None
    except Exception:
        return None
    return None


def usage_from_body(endpoint: str, body: Any) -> dict[str, Any] | None:
    if not isinstance(body, dict):
        return None
    return body.get("usage")


def build_fixture(repeat_count: int = 8) -> str:
    fixture = FIXTURE_PATH.read_text()
    chunks = []
    for index in range(repeat_count):
        chunks.append(f"### Cached reference document copy {index + 1}\n\n{fixture}")
    return "\n\n".join(chunks)


def build_request_body(endpoint: str, model: str, prompt_prefix: str) -> tuple[dict[str, Any], dict[str, str]]:
    instruction = "Read the reference text carefully. Reply with exactly OK."
    if endpoint == "messages":
        return (
            {
                "model": model,
                "max_tokens": 16,
                "temperature": 0,
                "system": [
                    {
                        "type": "text",
                        "text": prompt_prefix,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                "messages": [{"role": "user", "content": instruction}],
            },
            {
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
    if endpoint == "chat_completions":
        return (
            {
                "model": model,
                "temperature": 0,
                "max_tokens": 16,
                "messages": [
                    {"role": "system", "content": prompt_prefix},
                    {"role": "user", "content": instruction},
                ],
            },
            {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "poe-feature": "chat-completions-strict",
            },
        )
    if endpoint == "responses":
        return (
            {
                "model": model,
                "temperature": 0,
                "max_output_tokens": 16,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": f"{prompt_prefix}\n\n{instruction}",
                            }
                        ],
                    }
                ],
            },
            {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
        )
    raise ValueError(f"Unknown endpoint {endpoint}")


def call_endpoint(endpoint: str, model: str, prompt_prefix: str, pricing: dict[str, Any]) -> dict[str, Any]:
    path = {
        "messages": "/v1/messages",
        "chat_completions": "/v1/chat/completions",
        "responses": "/v1/responses",
    }[endpoint]
    request_body, headers = build_request_body(endpoint, model, prompt_prefix)
    before_history = get_points_history(limit=20)
    before_ids = {item.get("query_id") for item in before_history}
    before_balance = get_balance()
    start_time = time.time()
    response = api_request("POST", path, headers=headers, payload=request_body, timeout=120)
    elapsed_ms = round((time.time() - start_time) * 1000, 1)
    history_entry = wait_for_new_history_entry(before_ids, model)
    after_balance = get_balance()
    usage = usage_from_body(endpoint, response.body)
    estimate = estimate_cost_from_usage(usage or {}, pricing)
    return {
        "endpoint": endpoint,
        "path": path,
        "model": model,
        "status": response.status,
        "elapsed_ms": elapsed_ms,
        "headers": response.headers,
        "request_body": request_body,
        "response_body": response.body,
        "response_text_preview": output_text_preview(endpoint, response.body),
        "usage": usage,
        "estimated_cost": estimate,
        "history_entry": history_entry,
        "balance_before": before_balance,
        "balance_after": after_balance,
        "balance_delta": before_balance - after_balance,
    }


def test_caching_pair(endpoint: str, model: str, prompt_prefix: str, pricing: dict[str, Any]) -> dict[str, Any]:
    first = call_endpoint(endpoint, model, prompt_prefix, pricing)
    second = call_endpoint(endpoint, model, prompt_prefix, pricing)
    return {
        "endpoint": endpoint,
        "model": model,
        "first": first,
        "second": second,
    }


def attempt_unsupported_model(endpoint: str, model: str) -> dict[str, Any]:
    prompt_prefix = "Minimal cache-compatibility probe. Reply with exactly OK."
    pricing = get_models().get(model, {}).get("pricing", {})
    return call_endpoint(endpoint, model, prompt_prefix, pricing)


def summarize_pair(pair: dict[str, Any]) -> dict[str, Any]:
    def cached_tokens(usage: dict[str, Any] | None) -> int | None:
        if not usage:
            return None
        if "cache_read_input_tokens" in usage:
            return int(usage.get("cache_read_input_tokens", 0))
        details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
        if "cached_tokens" in details:
            return int(details.get("cached_tokens", 0))
        return None

    first = pair["first"]
    second = pair["second"]
    first_cached = cached_tokens(first.get("usage"))
    second_cached = cached_tokens(second.get("usage"))
    return {
        "endpoint": pair["endpoint"],
        "model": pair["model"],
        "first_status": first["status"],
        "second_status": second["status"],
        "first_cached_tokens": first_cached,
        "second_cached_tokens": second_cached,
        "cache_hit_observed": bool(second_cached and second_cached > 0),
        "first_points": (first.get("history_entry") or {}).get("cost_points"),
        "second_points": (second.get("history_entry") or {}).get("cost_points"),
        "first_balance_delta": first.get("balance_delta"),
        "second_balance_delta": second.get("balance_delta"),
    }


def main() -> int:
    models_catalog = get_models()
    prompt_prefix = build_fixture(repeat_count=8)
    main_models = ["claude-haiku-4.5", "gpt-5.4-mini"]
    endpoints = ["messages", "chat_completions", "responses"]

    results: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fixture_path": str(FIXTURE_PATH),
        "fixture_repeat_count": 8,
        "prompt_prefix_chars": len(prompt_prefix),
        "balance_start": get_balance(),
        "pairs": [],
        "pair_summaries": [],
        "unsupported_models": [],
        "balance_end": None,
    }

    for model in main_models:
        pricing = models_catalog[model].get("pricing", {})
        for endpoint in endpoints:
            pair = test_caching_pair(endpoint, model, prompt_prefix, pricing)
            results["pairs"].append(pair)
            results["pair_summaries"].append(summarize_pair(pair))

    for model in ["glm-5.1-fw", "minimax-m2.7", "kimi-k2.5"]:
        catalog_entry = models_catalog.get(model, {})
        probe = {
            "model": model,
            "catalog": {
                "owned_by": catalog_entry.get("owned_by"),
                "supported_endpoints": catalog_entry.get("supported_endpoints"),
                "pricing": catalog_entry.get("pricing"),
            },
            "responses_probe": attempt_unsupported_model("responses", model),
        }
        results["unsupported_models"].append(probe)

    results["balance_end"] = get_balance()
    results["balance_total_delta"] = results["balance_start"] - results["balance_end"]

    OUTPUT_PATH.write_text(json.dumps(results, indent=2))
    print(json.dumps(results["pair_summaries"], indent=2))
    print(f"\nWrote detailed results to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
