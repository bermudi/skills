---
name: forking-projects
description: >
  Use when creating, organizing, maintaining, or syncing a fork, cleaning up
  downstream patches, or turning a fork into an independent project. Applies
  consistent fork documentation, branch conventions, patch tracking, and
  maintenance rules without silently rewriting existing repositories.
---

# Forking projects

A fork should answer three questions without archaeology: **why does it
exist, what do we carry, and how do we keep it working?** These are defaults
for our repositories, not reasons to reorganize a working repo gratuitously.

## 1. Declare what kind of fork this is

Record the mode in root `FORK.md`:

- **Patch-carrying:** upstream still determines the product; we carry a
  small, justified set of changes. Success means less divergence and cheap
  syncs, ideally retiring the fork entirely.
- **Independent:** we own the direction, releases, security, and support.
  Upstream is lineage and a possible source of fixes, not our roadmap.
  State whether this is a divergent product or a succession of stewardship.

Painful merges do not automatically make a fork independent. Propose a mode
change explicitly, with the maintenance responsibilities it adds. Do not
silently stop syncing while continuing to promise upstream compatibility.

For a new fork, first consider whether a plugin, wrapper, upstream PR, or
package patch would solve the actual problem with less permanent upkeep.
Do not relitigate an established fork's existence on every small task.

## 2. Use predictable names, but don't rename blindly

For new forks, default to:

| Name | Role |
|---|---|
| `origin` remote | Our repository; normal push destination |
| `upstream` remote | Original project; fetch source, not our push destination |
| `main` branch | Our maintained product |
| `patch/<topic>` branch | Isolated change before integration |
| `sync/<upstream-version>` branch | Candidate upstream integration |

`upstream/main` is a remote-tracking ref, not our product branch. Upstream
may use a different branch name; inspect rather than assume.

A separate clean-mirror branch is optional, not another branch everyone must
maintain. If one exists, document it and never mix product commits into it.

For existing forks, inspect branch tracking, worktrees, release automation,
and actual consumers before proposing changes. Record the existing mapping
in `FORK.md`; migration is separate from documenting it. Remote URLs can
contain credentials: do not dump them into logs or reports.

## 3. Keep the maintenance record in the repository

Use [assets/FORK.md](assets/FORK.md) when creating or normalizing the fork's
record. Keep its patch inventory and sync log in that document until their
size justifies splitting them out. No parallel wiki as the source of truth.

- **`FORK.md`:** purpose, mode, maintainer, lineage, branch roles,
  compatibility promises, maintenance/release policy, and carried changes.
- **`UPSTREAM`:** the exact last fully integrated upstream ref and full
  commit ID. Use `ref: <tag-or-ref>` and `commit: <full-sha>` on separate
  lines. Resolve the ref; never guess the SHA.
- **README opening:** identify the fork, why it exists, where issues go,
  and link to `FORK.md`. Preserve upstream license and attribution notices.

For an independent project, `UPSTREAM` can remain the original base; record
later selective imports separately. Cherry-picking a fix is not integrating
all upstream changes through that commit.

Keep agent instructions short: point the repo's `AGENTS.md` at `FORK.md`
and the real test/release commands instead of duplicating fork policy.
Unknown facts stay explicitly unknown, not filled with invented owners,
passing checks, or maintenance dates.

## 4. Carry intentional patches, not an unexplained diff

- Prefix new carried-change commit subjects with `fork:`. One coherent
  behavior change per commit; no unrelated formatting or cleanup.
- Give each active patch a stable inventory ID, its purpose, touched areas,
  regression coverage, upstream issue/PR if any, and removal condition.
  Commit hashes alone are poor identifiers because private stacks change.
- Keep the inventory about **active behavior**, not every historical commit.
  A reverted patch is not still carried. Mark retired entries or remove
  them while retaining the retirement in the sync log.
- Prefer upstreamable changes and extension points. Track whether a patch
  was proposed, accepted, rejected, or deliberately kept local.
- Merge upstream into shared/public product history. Rebase only private,
  unshared stacks; do not rewrite published history to make it look tidy.
- Measure invasiveness and churn in patched areas, not just commit counts.
  Two changes to a core abstraction can cost more than twenty isolated ones.

An independent project's ordinary development does not need `fork:` on
every commit. Track inherited compatibility obligations and selective
upstream imports, not a fictional permanent patch stack.

## 5. Treat a sync as a maintenance event

Choose an explicit cadence and owner in `FORK.md`: weekly is a useful
starting point for a fast-moving tracked core, quarterly for pinned release
bases. Security fixes do not wait for the calendar.

Before integrating, review changes **since the recorded base**, especially
in patched areas. Prefer a stable upstream tag unless the fork explicitly
tracks development. Work on a candidate branch; don't turn an update request
into an unannounced change to the shipped branch.

Enable repository-local `rerere` when useful, but review replayed conflict
resolutions. A clean merge is not evidence of correct behavior. Never use
blanket `ours`, `theirs`, or union merging to hide semantic conflicts.

For a releasable sync:

- Run upstream checks and the fork's regression/conformance checks. The
  latter protect promises upstream does not make for us. Report checks
  that could not run; do not call an untested integration ready to ship.
- Audit each active patch: still needed, absorbed upstream, obsolete, or
  needing redesign? Reverse obsolete behavior without rewriting public
  history. Confirm upstream's replacement actually covers our use case.
- Advance `UPSTREAM` only to the fully integrated base. Update patch status,
  changelog, and sync log together: old/new base, conflicts, effort, checks,
  and unresolved problems. Record failed attempts without advancing the base.

Repeated semantic conflicts in core code are a design warning. Time-box the
sync and propose simplifying the patch, negotiating an extension point, or
formally changing modes rather than endlessly repairing the same seam.

## 6. Make shipped builds unambiguous

Document the build, install, and release path people actually use. Distinguish
our artifacts from upstream's; check package names, update URLs, issue links,
CI publish targets, and credentials before enabling inherited release jobs.
Do not accidentally publish under upstream's identity or ship their updater.

Package versions follow the ecosystem's ordering rules, not Git tag style.
Under SemVer, `1.2.3-fork.1` sorts **below** `1.2.3`; `+fork.1` does not
increase precedence. Choose and document how consumers select our build.
Never move a released tag or replace a published version's contents.

Compatibility is bounded: state supported versions, file/protocol/config
formats, exclusions, and the checks that enforce them. “Compatible with
upstream” without a version and scope is not a usable promise.

## 7. Own upkeep—or stop pretending

Every shipped fork needs an owner for upstream security advisories,
applicability triage, backports, and releases. Dependency scanners do not
determine whether an upstream code fix is still relevant to our changed tree.
Set response expectations and supported release lines appropriate to use.

An independent project also owns its roadmap, migration guide, issue tracker,
release/signing process, and contribution/governance rules appropriate to its
size. A personal tool need not invent a foundation; it still needs a named
maintainer and an honest support policy. Address naming/trademark conflicts
early without discarding license notices or provenance.

Revisit the fork when upstream absorbs its purpose, maintenance costs exceed
its value, or checks and releases stop happening. Propose returning upstream,
reducing scope, changing modes, or archiving honestly. Archiving, deleting
refs, force-pushing, and publishing remain explicit operator decisions.

## Applying this to a messy fork

Start with a read-only inventory. Separate **observed state**, **recommended
conventions**, and **changes requiring approval**. Document what exists before
attempting to normalize it; preserve dirty work and public history. Only
create or change the maintenance files relevant to the requested task.

Close with a short summary: mode/base, active patch burden, changes made,
checks actually run, and the next maintenance action or unresolved decision.
Do not turn documentation cleanup into an unsolicited sync or release.
