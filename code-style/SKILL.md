---
name: code-style
description: >
  Use when writing, changing or reviewing code, or picking a stack for new
  work.
---

# Code style

- Log or trace every external boundary, meaningful state change, and error path. Chatter goes to stderr.
- Validate external input at the boundary (zod in TS, pydantic in Python).
- TS: no `any`; use `unknown`, then narrow. Python: type hints everywhere, mypy passes.
- Same lesson twice → encode it as a lint, test, or script.
- Make the smallest change that solves the problem. Remove dead code before adding new code.
- Name the data shape before writing logic. Make illegal states unrepresentable.
- No abstraction without a second real use. No one-caller wrappers.
- Guard at system boundaries only. Trust internal types; no defensive checks inside.
- Fix the root cause, where the system first went wrong. Don't add a guard for the symptom.
- Tests assert what users of the code can observe, not how it works inside.
- When replacing an internal API, migrate its callers and delete the old one in the same change.
- Comments only for a non-obvious why.
- Stack for new work, unless the project already chose: CLIs Go (stdlib) · web/APIs TS (bun) · DB Convex · perf Zig · ML Python (uv) · heavy concurrency Rust · quick experiments https://docs.lakebed.dev/
