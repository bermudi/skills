---
name: issue-workflow
description: >
  Use when opening, labelling or closing a GitHub issue or pull request, testing or verifying a
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

## Pull request

- Open a draft PR on the branch's first push: `gh pr create --draft --title "<issue title>" --body "Closes #N"`. One PR per issue; the PR is where review, verdicts and evidence live, so the issue stays the problem statement.
- Mark it ready (`gh pr ready`) only after a verifier `PASS`, or a `PASS+NOTES` with every note answered.
- Push follow-up commits to the same branch. Never force-push a PR branch without the operator's confirmation.

## Evidence and a way to try it

- Your report and the PR description (or a PR comment) must carry evidence it works and a way for the operator to try it. "Tests pass" alone isn't evidence.
- A way to try it means seconds, not setup: a link to the branch already running on a throwaway instance (plus how to stop it), or one command that starts it configured and lands on the feature. A list of setup steps doesn't count. Leave the operator only what really needs them directly, like a real login or token, and say why.

## Test tiers

Each test runs once; the operator's machine can't take repeat runs:

- Implementer: only the tests for what changed, plus typecheck and lint on those files. Never the full suite.
- CI: the full suite, on every branch push.
- Verifier (a clean-session agent: not the builder, not the lead): drives the feature live and reads the CI result. If the repo has no CI, it runs the full suite once. Its report opens with `PASS`, `PASS+NOTES` or `FAIL` and goes on the PR as a comment.
- Reviewer (whichever tool is available): reads the diff, runs no tests.
- Merge: runs nothing if CI is green on that exact commit and `main` hasn't moved; otherwise only the tests for what changed since. If CI couldn't run, the report says so and the operator decides.

## Repo with no CI

First work in an actively used repo with no CI: open a separate issue and branch to add it (existing tests, typecheck, lint, on every branch push), without holding up the feature. If the suite needs real credentials or paid services, ask the operator first.

## Review and merge

**A finding needs proof.** From a verifier: the exact command or steps, the output, and the output the intent requires. From a diff reviewer: the file and line, and a concrete input or state that produces a wrong result. Style, naming and "could break if someone later…" are not findings. An unproven finding is dropped, not filed.

Every proven finding is sorted by where the problem came from, never by priority, effort or taste. There is no third bucket.

| Finding | Goes to |
|---|---|
| Introduced by this branch's diff | **Fix before merge**, even a P3. The branch made it, so the branch owns it. |
| Already on `main` before the branch | **Separate issue** (this branch didn't cause it). Keeps the finding's priority. Skip it if it is standing policy. |
| The fix needs a design or product decision | **Ask the operator** before filing or fixing. |

- Fix-before-merge findings go in **one checklist comment on the PR**, one `- [ ]` item each with its proof. No issue per finding. Fix them on the same branch, tick each item with the commit that fixed it, and edit that comment (`gh api -X PATCH repos/OWNER/REPO/issues/comments/ID -f body=...`) instead of adding a new one per round.
- A re-check covers the checklist items and the changed diff only, not a fresh hunt.
- On the operator's green light, merge the PR with the repo's usual method (`gh pr merge --merge` if it has none). Don't pass `--delete-branch`: deleting the branch needs its own confirmation. The PR's `Closes #N` closes the issue; don't close it by hand.
