---
name: forking-projects
description: >
  Use when creating, organizing, maintaining, or syncing a fork, cleaning up
  downstream patches, or turning a fork into an independent project.
---

# Forking projects

A fork should answer, without archaeology: **why it exists, what we carry, how we keep it working.** These are defaults, not reasons to reorganize a working repo.

## 1. Declare the mode in root `FORK.md`

- **Patch-carrying:** upstream decides the product; we carry a small, justified set of changes. Success = less divergence, cheap syncs, ideally retiring the fork.
- **Independent:** we own direction, releases, security and support; upstream is lineage and a source of fixes. Say whether it is a divergent product or a succession of stewardship.

Painful merges don't make a fork independent. Propose a mode change explicitly, with the upkeep it adds; never stop syncing while still promising compatibility. For a new fork, first ask whether a plugin, wrapper, upstream PR or package patch solves it with less upkeep. Don't relitigate an established fork on small tasks.

## 2. Names and existing forks

New forks default to: `origin` = ours (push), `upstream` = original (fetch only), `main` = our product, `patch/<topic>`, `sync/<upstream-version>`. `upstream/main` is a remote-tracking ref, not our branch, and upstream's default branch may differ: inspect. A clean-mirror branch is optional; if it exists, document it and never put product commits on it.

For an existing fork, inspect tracking, worktrees, release automation and real consumers before proposing anything, and record in `FORK.md` only what a fresh clone would get wrong (product branch, merge/rebase policy, push restrictions, local setup). Documenting is separate from migrating. Remote URLs can hold credentials: keep them out of logs and reports.

## 3. The maintenance record lives in the repo

Start from [assets/FORK.md](assets/FORK.md). Patch inventory and sync log stay in it until size justifies splitting; no parallel wiki.

- **`FORK.md`:** purpose, mode, maintainer, lineage, convention breaks, compatibility promises, release policy, carried changes with reasons.
- **`UPSTREAM`:** last fully integrated upstream `ref:` and full `commit:` SHA on separate lines. Resolve the ref; never guess the SHA. For an independent project it stays the original base; record later selective imports separately (cherry-picking a fix is not integrating everything up to it).
- **README opening:** says it's a fork, why, where issues go, links `FORK.md`; keep upstream license and attribution.
- The repo's `AGENTS.md` stays short: point at `FORK.md` and entry points (`just check`, the release workflow), not their contents. Unknown facts stay marked unknown, never invented owners, passing checks or dates.

### Write decisions, not a copy of the repo

Every line is read at the start of each agent session, so a stale line costs tokens every time, re-verification at every sync, and a false claim an agent acts on. With agents committing continuously, copied state rots in hours.

**Test per line: can a command answer this in under a minute?** If yes, record the command, stable handle or decision it feeds, not the answer. Handles (`just check`, CI job name, `UPSTREAM`, a test filter) change slowly and fail loudly; copied values change fast and fail silently.

| Record in `FORK.md` (nothing else holds it) | Leave to the source of truth |
|---|---|
| Why the fork exists; why a plugin/wrapper/PR wasn't enough | Files touched, line numbers, constants → `git log -p`, `grep` |
| Mode and the responsibilities it adds | Branch/ref/remote/worktree lists → `git branch -vv`, `git for-each-ref` |
| Promises and exclusions we chose | Ahead/behind, dirty files, unpushed work → `git status -sb` |
| Per-change purpose, upstream status, removal condition | SHAs, lineage, tags → `git log`, `gh release list` |
| Traps and dead ends: what broke, why upstream declined | Test bodies, CI steps, command expansions → the files |
| Cadence, owner, time-box, exit conditions as *triggers* | "Pending" lists, "current" version pins, "byte-identical" claims |

- **Tense is the tell.** Present-tense claims about repo state are drift on a timer; dated statements of events or decisions don't rot. SHAs, versions, dates and counts belong in the sync log ("as of then"), not in status prose ("now").
- **Facts whose system of record is the document** (`UPSTREAM`: nothing else knows which ref was integrated) are recorded. When document and command disagree, the command wins.
- **Encode the invariant, not the value:** "our integration markers stay strictly above upstream's latest *released* number" survives dozens of syncs; "marker = 13" is wrong at the next release and an equal number with different content silently skips upgrades.
- **Delete stale state; never refresh it.** Refreshing renews the subscription. Real cases, both false within days: an "unpushed work" item that had shipped, and "five commits pending" when it was seven. `git status -sb` and `git log <base>..upstream/master` were already right.
- **The sync log is a ledger:** one short entry per sync: old base → new base, what conflicted and why, what retired, what ran, what shipped, failed attempts too. A page-long entry is a design note: link it. One-task knowledge goes in a commit message or session report.

## 4. Carry intentional patches

- Prefix carried-change commits with `fork:`; one behavior change per commit, no drive-by formatting.
- Each active patch: stable inventory ID, reason, the seam it disturbs (name the seam, not files), a command or test filter proving it's alive, upstream issue/PR, removal condition. SHAs are poor IDs because private stacks change.
- The inventory covers active behavior, not history. A reverted patch isn't carried: mark or remove it and keep the retirement in the sync log.
- Prefer upstreamable changes and extension points; track proposed/accepted/rejected/kept-local.
- Merge upstream into shared history; rebase only private unshared stacks; never rewrite published history to tidy it.
- Judge invasiveness by churn in patched areas, not commit counts: two changes to a core abstraction can cost more than twenty isolated ones.

An independent project doesn't need `fork:` on every commit: track inherited compatibility obligations and selective imports, not a fictional permanent patch stack.

## 5. A sync is a maintenance event

Set cadence and owner in `FORK.md` (weekly for a fast tracked core, quarterly for pinned bases; security fixes don't wait). Review changes *since the recorded base*, especially in patched areas; prefer a stable upstream tag unless the fork tracks development. Work on a candidate branch, never an unannounced change to the shipped branch. Re-read `FORK.md` against the tree in the same session and delete or demote every claim the tree contradicts; don't spend the sync refreshing copied state.

`rerere` is fine but review replayed resolutions. A clean merge isn't proof of correct behavior. Never blanket `ours`/`theirs`/union to hide semantic conflicts.

For a releasable sync:
- Run upstream's checks and the fork's regression/conformance checks (they protect promises upstream doesn't make for us). Report checks that couldn't run; don't call an untested integration ready.
- Audit each patch: still needed, absorbed (does upstream's version really cover our use case?), obsolete, or needing redesign. Reverse obsolete behavior without rewriting public history.
- Advance `UPSTREAM` only to the fully integrated base; update patch status, changelog and sync log together. A failed attempt is logged without advancing the base. If the new base falsifies a compatibility invariant, restate the invariant rather than patching a number.

Repeated semantic conflicts in core code are a design warning: time-box, then simplify the patch, negotiate an extension point, or change modes.

## 6. Shipped builds

Document the release path by entry point (workflow or target), not expanded command lines. Before enabling inherited release jobs, check package names, update URLs, issue links, publish targets and credentials: never publish under upstream's identity or ship their updater. Versions follow the ecosystem's ordering: under SemVer `1.2.3-fork.1` sorts **below** `1.2.3` and `+fork.1` doesn't raise precedence; choose and document how consumers select our build. Never move a released tag or replace a published version's contents.

Compatibility needs scope and a baseline phrased to survive syncs ("from the recorded base onward"); "compatible with upstream" alone isn't a promise.

## 7. Own upkeep or stop pretending

A shipped fork needs an owner for upstream advisories, applicability triage (scanners can't tell if an upstream fix still applies to our changed tree), backports and releases. An independent project also owns roadmap, migration guide, tracker, release/signing and governance, scaled to size; a personal tool still needs a named maintainer and honest support policy. Settle naming/trademark conflicts early without dropping license notices.

Revisit the fork when upstream absorbs its purpose, upkeep exceeds value, or checks and releases stop. Propose returning upstream, narrowing scope, changing modes or archiving. Archiving, deleting refs, force-pushing and publishing are the operator's call.

## Messy forks

Read-only inventory first; separate observed state, recommended conventions and changes needing approval. Document before normalizing; preserve dirty work and public history; touch only the maintenance files the task needs. Close with: mode/base, patch burden, changes made, checks actually run, drift found, next action or open decision. Never turn doc cleanup into an unasked sync or release.
