---
name: issue-workflow
description: >
  Use when leading a repo task to a PR, opening, labelling or closing a GitHub issue or pull
  request, testing or verifying a change, reporting it done, reviewing, or merging a branch.
---

# Issue workflow

## Lead the task

If the user gives you a repo task, you are its lead unless explicitly assigned a supporting role. Delegation is how you carry out the task, not a separate workflow for the user to choose.

For a task that ends in a PR, read [references/fusion.md](references/fusion.md) and follow it. A sidekick or verifier never reads it.

## Rules

- Work is tracked in GitHub Issues. Each states a problem, not a solution. No plan documents.
- Each issue gets a branch in its own git worktree and a draft PR that closes it. If the task has no issue, open one.
- Exception: plain docs changes (typos, notes, how-tos) go straight to `main`. Docs that set rules, direction or design get a PR like code.
- Don't stack PRs: branch from `main` and wait for the base to merge. If a stack is unavoidable, the stacked PR says so in its body, and you retarget it to `main` before merging its base. A PR merged into another branch has not reached `main`.
- Out-of-scope finds become labelled issues, not part of this branch.
- A ruling the user makes is posted as a comment on its issue the same turn, dated, with the facts it rests on, and the fix that lands it writes it into the repo's design docs. The issue thread and the docs, not the chat, are where it lives.
- When the user asks for one lead per issue, each issue is its own branch, worktree and draft PR with its own lead. The lead starts the verifier itself (`verify-pr`), on the model the user named.
- Some repos are public: nothing private goes in issues or pushed commits.
- Nothing merges without the user's green light.
- Builds run in CI.
- If a repo works differently and its AGENTS.md doesn't explain why, flag it once and carry on with its existing approach until the user decides.

## Labels

- Label each issue when you open it (`gh issue create --label <type> --label <priority> …`), never "later": one type, one priority, and one area if the repo has area labels. If a repo lacks a type or priority label, create it with this name and meaning as its description.
  - Types: `bug` something isn't working · `enhancement` new feature or request · `refactor` behaviour-preserving structural change.
  - Priorities: `P0` drop everything, blocks release or operations · `P1` urgent, next cycle · `P2` normal, fix eventually · `P3` low, nice to have.
  - A path to unbounded spend of the user's money is always P1, even when it's off by default.
- `deep-dive`: the user wants to think this through before any ruling. Never start work on it unasked: not when picking from a backlog, not as a side fix, not as part of another issue. Work on it only when the user names that issue. You may comment with facts you found, but make no plan, branch or PR. If a repo lacks the label, create it with this meaning as its description.
- If no area label fits, create one with a description and say so in your report. No label-like prefixes in titles (`[P3]`, `[arch]`, `telegram:`).

## Worktree

Make it with the surface you're on, so it shows up there:

- Herdr (`HERDR_ENV=1`): `herdr worktree create --cwd <repo> --branch <branch>`. It lands in `~/.herdr/worktrees/<repo>/`.
- T3 Code: its own worktree option for the thread. It lands in `~/.t3/worktrees/<repo>/`.
- Neither: `git -C <repo> worktree add ~/.worktrees/<repo>/<branch> -b <branch> main`.

Already given a worktree (the brief names one, or your cwd is one): use it. Check with `git rev-parse --git-dir --git-common-dir`: two different paths mean a linked worktree; identical paths mean the main checkout. A later session on the same issue works in the same worktree. After the merge, `git worktree remove <path>`; the branch stays.

## Pull request

- Open a draft PR on the branch's first push: `gh pr create --draft --title "<issue title>" --body "Closes #N"`. One PR per issue; the PR is where review, verdicts and evidence live, so the issue stays the problem statement.
- Mark it ready (`gh pr ready`) only after a verifier `PASS`, or a `PASS+NOTES` with every note answered.
- Push follow-up commits to the same branch. Never force-push a PR branch without the user's confirmation.

## Evidence and a way to try it

- Your report and the PR description (or a PR comment) must carry evidence it works and a way for the user to try it. "Tests pass" alone isn't evidence.
- A way to try it means seconds, not setup: a link to the branch already running on a throwaway instance (plus how to stop it), or one command that starts it configured and lands on the feature. A list of setup steps doesn't count. Leave the user only what really needs them directly, like a real login or token, and say why.

## Test tiers

Each test runs once; the machine can't take repeat runs:

- Implementer: only the tests for what changed, plus typecheck and lint on those files. Never the full suite.
- CI: the full suite, on every branch push.
- Verifier: a clean-context agent run with the `verify-pr` skill. It drives the feature live and reads the CI result; if the repo has no CI, it runs the full suite once. Its verdict goes on the PR as a comment and on the checked commit as a `verify-pr` commit status.
- Reviewer (whichever tool is available): reads the diff, runs no tests.
- Merge: runs nothing if CI is green on that exact commit and `main` hasn't moved; otherwise only the tests for what changed since. If CI couldn't run, the report says so and the user decides.

## Repo with no CI

First work in an actively used repo with no CI: open a separate, labelled issue and branch to add it (existing tests, typecheck, lint, on every branch push), without holding up the feature. If the suite needs real credentials or paid services, ask the user first.

## Review and merge

**A finding needs proof.** From a verifier: the exact command or steps, the output, and the output the intent requires. From a diff reviewer: the file and line, and a concrete input or state that produces a wrong result. Style, naming and "could break if someone later…" are not findings. An unproven finding is dropped, not filed.

Every proven finding is sorted by where the problem came from, never by priority, effort or taste. There is no third bucket.

| Finding | Goes to |
|---|---|
| Introduced by this branch's diff | **Fix before merge**, even a P3. The branch made it, so the branch owns it. |
| Already on `main` before the branch | **Separate issue** (this branch didn't cause it), labelled per Labels. Keeps the finding's priority as its priority label. Skip it if it is standing policy. |
| The fix needs a design or product decision | **Ask the user** before filing or fixing. If they say file it, label it `deep-dive`. |

- Fix-before-merge findings go in **one checklist comment on the PR**, one `- [ ]` item each with its proof. No issue per finding. Fix them on the same branch, tick each item with the commit that fixed it, and edit that comment (`gh api -X PATCH repos/OWNER/REPO/issues/comments/ID -f body=...`) instead of adding a new one per round.
- A re-check covers the checklist items and the changed diff only, not a fresh hunt.
- On the user's green light, merge the PR with the repo's usual method (`gh pr merge --merge` if it has none). Don't pass `--delete-branch`: deleting the branch needs its own confirmation. The PR's `Closes #N` closes the issue; don't close it by hand.
- After every merge, check it landed: `git fetch && git merge-base --is-ancestor <merge-commit> origin/main` and `gh issue view N --json state`. Report both. An open issue after a merge means the work is not on `main`.
- Before `gh pr merge`, every check on the head must be finished: `gh pr checks N --json state -q '.[].state' | grep -vxE 'SUCCESS|SKIPPED'` must print nothing. `IN_PROGRESS` or `PENDING` means wait, even when a sibling run on the same commit is green (merged twice with shards still running, 2026-11-18). `gh pr merge --auto` is no way around this: in a repo with no required checks, it merges at once (2026-11-18).
