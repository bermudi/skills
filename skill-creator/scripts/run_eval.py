#!/usr/bin/env python3
"""Run trigger evaluation for a skill description.

Tests whether a skill's description causes an agent to trigger (read the skill)
for a set of queries. Uses `pi -p` under the hood. Outputs results as JSON.
"""

import argparse
import json
import os
import select
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from scripts.utils import parse_skill_md


def run_single_query(
    query: str,
    skill_name: str,
    skill_path: str,
    timeout: int,
    model: str | None = None,
) -> bool:
    """Run a single query and return whether the skill was triggered.

    Uses `pi -p --mode json --no-session --skill <path>` to run the query.
    Parses the NDJSON stream to detect if the agent reads the skill's
    SKILL.md file (which is how Pi activates skills).
    Early-exits if the agent's first action is something other than reading
    the skill file.
    """
    skill_md_path = str(Path(skill_path) / "SKILL.md")
    # Pattern to match: the skill could be read from any installed location,
    # not just the path we pass via --skill. Match on skill_name/SKILL.md.
    skill_name_pattern = f"{skill_name}/SKILL.md"

    cmd = [
        "pi", "-p", query,
        "--mode", "json",
        "--no-session",
        "--skill", skill_path,
    ]
    if model:
        cmd.extend(["--model", model])

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    triggered = False
    start_time = time.time()
    buffer = ""
    # Track tool call arguments as they stream in
    pending_read = False
    accumulated_args = ""

    try:
        while time.time() - start_time < timeout:
            if process.poll() is not None:
                remaining = process.stdout.read()
                if remaining:
                    buffer += remaining.decode("utf-8", errors="replace")
                break

            ready, _, _ = select.select([process.stdout], [], [], 1.0)
            if not ready:
                continue

            chunk = os.read(process.stdout.fileno(), 8192)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type", "")

                # Pi JSON stream events:
                #   toolcall_start  → agent is about to call a tool
                #   toolcall_delta  → streaming tool arguments
                #   toolcall_end    → tool call complete
                #   tool_execution_start → tool is being executed
                #   turn_end        → agent turn finished

                if event_type == "message_update":
                    ae = event.get("assistantMessageEvent", {})
                    ae_type = ae.get("type", "")

                    if ae_type == "toolcall_start":
                        # Check which tool the agent is calling
                        msg = ae.get("message", {})
                        for c in msg.get("content", []):
                            if c.get("type") == "toolCall":
                                tool_name = c.get("name", "")
                                if tool_name == "read":
                                    pending_read = True
                                    accumulated_args = json.dumps(c.get("arguments", {}))
                                    if skill_name_pattern in accumulated_args:
                                        return True
                                else:
                                    # First tool call is not reading the skill → not triggered
                                    return False

                    elif ae_type == "toolcall_delta" and pending_read:
                        delta = ae.get("delta", "")
                        accumulated_args += delta
                        if skill_name_pattern in accumulated_args:
                            return True

                    elif ae_type == "toolcall_end" and pending_read:
                        msg = ae.get("message", {})
                        for c in msg.get("content", []):
                            if c.get("type") == "toolCall":
                                args = c.get("arguments", {})
                                path = args.get("path", "")
                                if skill_name_pattern in path:
                                    return True
                        # read tool called but not targeting our skill
                        pending_read = False
                        return False

                elif event_type == "tool_execution_start":
                    tool_name = event.get("toolName", "")
                    if tool_name != "read":
                        return False
                    args = event.get("args", {})
                    path = args.get("path", "")
                    if skill_name_pattern in path:
                        return True
                    # read tool executed on something else
                    return False

                elif event_type == "turn_end":
                    # Agent finished without reading the skill
                    return False

        return triggered
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def run_eval(
    eval_set: list[dict],
    skill_name: str,
    skill_path: Path,
    description: str,
    num_workers: int,
    timeout: int,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: str | None = None,
) -> dict:
    """Run the full eval set and return results."""
    results = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        for item in eval_set:
            for run_idx in range(runs_per_query):
                future = executor.submit(
                    run_single_query,
                    item["query"],
                    skill_name,
                    str(skill_path),
                    timeout,
                    model,
                )
                future_to_info[future] = (item, run_idx)

        query_triggers: dict[str, list[bool]] = {}
        query_items: dict[str, dict] = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_items[query] = item
            if query not in query_triggers:
                query_triggers[query] = []
            try:
                query_triggers[query].append(future.result())
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                query_triggers[query].append(False)

    for query, triggers in query_triggers.items():
        item = query_items[query]
        trigger_rate = sum(triggers) / len(triggers)
        should_trigger = item["should_trigger"]
        if should_trigger:
            did_pass = trigger_rate >= trigger_threshold
        else:
            did_pass = trigger_rate < trigger_threshold
        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "trigger_rate": trigger_rate,
            "triggers": sum(triggers),
            "runs": len(triggers),
            "pass": did_pass,
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)

    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Run trigger evaluation for a skill description")
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override description to test")
    parser.add_argument("--num-workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per query in seconds")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Number of runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")
    parser.add_argument("--model", default=None, help="Model for pi -p, in provider/model form (e.g. 'poe-responses/Claude-Sonnet-4.6'). Short names may not resolve without a saved session.")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    eval_set = json.loads(Path(args.eval_set).read_text())
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, content = parse_skill_md(skill_path)
    description = args.description or original_description

    if args.verbose:
        print(f"Evaluating: {description}", file=sys.stderr)

    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        skill_path=skill_path,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
    )

    if args.verbose:
        summary = output["summary"]
        print(f"Results: {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}", file=sys.stderr)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
