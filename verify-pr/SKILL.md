---
name: verify-pr
description: >
  Verify a PR the way a user would: a clean-context agent drives the change
  live, proves each finding, and posts PASS, PASS+NOTES or FAIL on the PR.
  Use when a change is built and needs verifying, or a fix needs re-checking.
---

# Verify a PR

The builder checks what it meant to build. A verifier with clean context checks what was asked. Only its verdict counts: green CI and the builder's own review don't run the change as a user would.

## Who verifies

- **Default:** a subagent of your own harness with fresh context, on the same model. Every harness has one, or runs on Herdr or T3, which can start a session.
- **The user or the brief named a verifier** (harness, model): start that as a fresh session on Herdr or T3 instead. Never substitute one.
- Never a context that saw the build: not you if you built or reviewed it, not a session holding the builder's transcript.
- A new verifier every round, so it never inherits its own earlier conclusions.

## The verifier's brief

You write it; the verifier gets nothing else.

- PR number and repo, head SHA, base.
- The asks in the user's words: from the issue and the user's comments, not your summary.
- The intent in one line.
- How to run it: the repo's `verify-<app>` skill (`.agents/skills/verify-*`), or "none".
- Re-check rounds only: the open findings checklist, and "check only these items and the diff since <sha>". A re-check is not a fresh hunt.
- Not your design reasoning, not the builder's report.

Then paste the job below into the brief.

## The verifier's job

1. Read CI on the head SHA. No CI in the repo → run the full suite once.
   Check the PR head out in your own worktree (`git worktree add <scratch>/wt-<N> origin/<branch>`), never in the shared checkout: other agents run there (2026-11-18: a verifier flipped a shared tree's HEAD mid-run). Remove the worktree when done.
2. Drive every ask live through the verify skill. None → `agent-browser` for web and Electron, a `tmux` session you start for CLI/TUI, `curl` for services, and say no verify skill exists. Never drive the user's running instances.
3. Try to break it. A finding counts only with proof: the exact command or steps, the output it gave, and the output the intent requires. List every finding you can prove, not only the first. Style, naming and "could break if someone later…" are out.
4. Write the report with the verdict as its first line:
   - `PASS`: every ask driven, no findings.
   - `PASS+NOTES`: no proven defect, but notes the caller must answer: an ask you couldn't reach (the missing prerequisite and the route you tried), or a gap between the verify skill's map and the app.
   - `FAIL`: at least one proven finding.

   Then exactly one line naming the commit you checked, in this exact form (tools read it):

   ```text
   Checked-SHA: <full 40-character lowercase commit SHA>
   ```
5. Post it on the PR as a new comment (`gh pr comment <N> --body-file <report>`), one per checked head, and return it.

## After the verdict

You, the caller, answer it:

- Every finding: a fix, recorded in the PR's findings checklist (`issue-workflow`), or a rejection with a concrete disproof. Never accept or dismiss one unread.
- Every note: answered. An unreached ask goes to the user; it never ships as verified.
- After fixes, start a new verifier for a re-check round. A verdict covers only its `Checked-SHA`: any later push needs a new one.
- `PASS`, or `PASS+NOTES` with every note answered, on the current head → `gh pr ready`. Neither is permission to merge.

## Basis

Proof rule from pstack's `interrogate`; verdict format and the non-author rule from its `shipping` playbook (cursor/plugins @ 236e548). Split out of `fusion` (2026-11-12) so any driver, not only a fusion lead, can verify.
