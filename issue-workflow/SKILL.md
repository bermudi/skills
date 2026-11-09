---
name: issue-workflow
description: >
  Use when opening, labelling or closing a GitHub issue, testing or verifying a
  change, reporting it done, reviewing, or merging a branch.
---

# Issue workflow

Hub rules (issue per problem, worktree per issue, nothing merges without the
operator) still apply. This skill holds the procedures.

## Labels

- Label each issue: one type, one priority, and one area if the repo has area labels. If a repo lacks a type or priority label, create it with this name and meaning as its description.
  - Types: `bug` something isn't working · `enhancement` new feature or request · `refactor` behaviour-preserving structural change.
  - Priorities: `P0` drop everything, blocks release or operations · `P1` urgent, next cycle · `P2` normal, fix eventually · `P3` low, nice to have.
- If no area label fits, create one with a description and say so in your report. No label-like prefixes in titles (`[P3]`, `[arch]`, `telegram:`).

## Evidence and a way to try it

- Your report and a comment on the issue must carry evidence it works and a way for the operator to try it. "Tests pass" alone isn't evidence.
- A way to try it means seconds, not setup: a link to the branch already running on a throwaway instance (plus how to stop it), or one command that starts it configured and lands on the feature. A list of setup steps doesn't count. Leave the operator only what really needs them directly, like a real login or token, and say why.

## Test tiers

Each test runs once; the operator's machine can't take repeat runs:

- Implementer: only the tests for what changed, plus typecheck and lint on those files. Never the full suite.
- CI: the full suite, on every branch push.
- Verifier (a clean-session agent, not the builder): drives the feature live and reads the CI result. If the repo has no CI, it runs the full suite once.
- Reviewer (whichever tool is available): reads the diff, runs no tests.
- Merge: runs nothing if CI is green on that exact commit and `main` hasn't moved; otherwise only the tests for what changed since. If CI couldn't run, the report says so and the operator decides.

## Repo with no CI

First work in an actively used repo with no CI: open a separate issue and branch to add it (existing tests, typecheck, lint, on every branch push), without holding up the feature. If the suite needs real credentials or paid services, ask the operator first.

## Review and merge

- Review findings go in an issue comment: "fix before merge" (fix on this branch) or "later" (file a new issue only if the operator approves; it keeps the finding's priority).
- On the operator's green light, merge to `main` with `Closes #N` in the merge commit. GitHub closes the issue when `main` is pushed; don't close it by hand.
