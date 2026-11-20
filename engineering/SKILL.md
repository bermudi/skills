---
name: engineering
description: >
  Use when writing, changing, debugging, refactoring, reviewing or measuring
  code, or picking a stack for new work.
license: MIT
---

# Engineering

## House rules

- Log or trace every external boundary, meaningful state change, and error path. Chatter goes to stderr.
- Validate external input at the boundary (zod in TS, pydantic in Python).
- TS: no `any`; use `unknown`, then narrow. Python: type hints everywhere, mypy passes.
- No abstraction without a second real use. No one-caller wrappers.
- Comments only for a non-obvious why.
- Stack for new work, unless the project already chose: CLIs Go (stdlib) · web/APIs TS (bun) · DB Convex · perf Zig · ML Python (uv) · heavy concurrency Rust · quick experiments https://docs.lakebed.dev/

## Playbooks

Match the task to one playbook, read it, and follow its steps. Repo procedure (issue, branch, PR, verify, merge) stays in `issue-workflow`.

- [bug-fix](playbooks/bug-fix.md): reproduce a defect, root-cause it, fix with runtime evidence.
- [feature](playbooks/feature.md): new or changed behavior, built from a named data shape.
- [refactoring](playbooks/refactoring.md): behavior-preserving change to structure.
- [perf](playbooks/perf.md): measured slowness, improved against a baseline.
- [prototype](playbooks/prototype.md): throwaway build to settle one design or empirical question.
- [investigation](playbooks/investigation.md): read-only "how does X work / why is Y".

## Principles

Read the file before you apply a principle. In your report, name each principle that changed a decision and the choice it changed.

**Core**
- [laziness-protocol](principles/laziness-protocol.md): sizing a diff, tempted to add layers. Smallest change that solves it.
- [foundational-thinking](principles/foundational-thinking.md): before logic. Data shape first, scaffold first.
- [redesign-from-first-principles](principles/redesign-from-first-principles.md): fitting a new requirement into an existing design.
- [attack-the-premise](principles/attack-the-premise.md): two fixes on one premise failed. Test the premise.
- [subtract-before-you-add](principles/subtract-before-you-add.md): remove dead weight, then build.
- [minimize-reader-load](principles/minimize-reader-load.md): code hard to trace. Cut layers and hidden state.
- [outcome-oriented-execution](principles/outcome-oriented-execution.md): planned migrations. Converge on the target, no throwaway compat code.
- [experience-first](principles/experience-first.md): product or UX tradeoffs.
- [exhaust-the-design-space](principles/exhaust-the-design-space.md): novel interaction or architecture. Prototype 2–3 options.
- [build-the-lever](principles/build-the-lever.md): non-trivial work. Build the script or codemod, not by hand.

**Architecture**
- [model-the-domain](principles/model-the-domain.md): stateful or branchy logic. A structure, not scattered conditionals.
- [boundary-discipline](principles/boundary-discipline.md): validation and error handling at boundaries; pure core.
- [type-system-discipline](principles/type-system-discipline.md): designing types. Illegal states unrepresentable.
- [make-operations-idempotent](principles/make-operations-idempotent.md): steps that run amid crashes and retries.
- [migrate-callers-then-delete-legacy-apis](principles/migrate-callers-then-delete-legacy-apis.md): new internal API. Migrate and delete in one change.
- [separate-before-serializing-shared-state](principles/separate-before-serializing-shared-state.md): concurrent writers. Remove the sharing first.

**Verification**
- [prove-it-works](principles/prove-it-works.md): before "done". The real artifact, not a proxy.
- [fix-root-causes](principles/fix-root-causes.md): debugging. Fix where the system first went wrong.
- [sequence-verifiable-units](principles/sequence-verifiable-units.md): multi-step work and commit order.
- [test-behavior-not-implementation](principles/test-behavior-not-implementation.md): any test you write or keep.
- [explain-the-number](principles/explain-the-number.md): any number you measured.

**Meta**
- [encode-lessons-in-structure](principles/encode-lessons-in-structure.md): same lesson twice. A lint, test or script, not more text.

Principles and playbooks adapted from pstack by Lauren Tan (MIT, see LICENSE).
