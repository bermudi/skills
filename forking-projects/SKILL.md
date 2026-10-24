---
name: forking-projects
description: >
  Use when creating, organizing, maintaining, or syncing a fork, cleaning up
  downstream patches, or turning a fork into an independent project. 
---

# Forking projects

A fork should answer three questions without archaeology: **why does it
exist, what do we carry, and how do we keep it working?** These are defaults
for our repositories, not reasons to reorganize a working repo gratuitously.

The maintenance record holds decisions and pointers, never a copy of what
`git`, the code, or CI already answer — see “Write decisions, not a copy of
the repository” in section 3. Copied state goes stale in days, and agents
act on it.

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
and actual consumers before proposing changes. Record the conventions a
fresh clone would get wrong — product branch name, merge or rebase policy,
push restrictions, required local setup — in `FORK.md`. The full inventory
of remotes and branches belongs to `git`. Migration is separate from
documenting it. Remote URLs can contain credentials: do not dump them into
logs or reports.

## 3. Keep the maintenance record in the repository

Use [assets/FORK.md](assets/FORK.md) when creating or normalizing the fork's
record. Keep its patch inventory and sync log in that document until their
size justifies splitting them out. No parallel wiki as the source of truth.

- **`FORK.md`:** purpose, mode, maintainer, lineage, conventions that break
  the defaults, compatibility promises, maintenance/release policy, and the
  carried changes with their reasons.
- **`UPSTREAM`:** the exact last fully integrated upstream ref and full
  commit ID. Use `ref: <tag-or-ref>` and `commit: <full-sha>` on separate
  lines. Resolve the ref; never guess the SHA.
- **README opening:** identify the fork, why it exists, where issues go,
  and link to `FORK.md`. Preserve upstream license and attribution notices.

For an independent project, `UPSTREAM` can remain the original base; record
later selective imports separately. Cherry-picking a fix is not integrating
all upstream changes through that commit.

Keep agent instructions short: point the repo's `AGENTS.md` at `FORK.md` and
at the entry points that matter (`just check`, the release workflow), not at
their contents. Unknown facts stay explicitly unknown, not filled with
invented owners, passing checks, or maintenance dates.

### Write decisions, not a copy of the repository

Every line here is read at the start of an agent session, so a stale line
costs three times: tokens in every session, re-verification work at every
sync, and — worst — a claim an agent will act on. A document that mirrors
live state decays at the speed the repo commits. With agents committing
continuously, that is hours, not months.

The test for each line: **can a command answer this in under a minute?** If
yes, the document must not hold the answer. It records the command, the
stable handle, or the decision the answer feeds. Handles (`just check`, the
CI job name, `UPSTREAM`, a test-name filter) change slowly and fail loudly
when the repo moves. Copied values change fast and fail silently.

| Record in `FORK.md` — no file, ref, or tool holds it | Leave to the source of truth |
|---|---|
| Why the fork exists; why a plugin, wrapper, or upstream PR was not enough | Files a change touches, line numbers, constant values → `git log -p`, `grep` |
| Mode, and the responsibilities it adds | Branch, ref, remote, worktree inventories → `git branch -vv`, `git for-each-ref` |
| Promises and exclusions we choose to keep | Ahead/behind counts, dirty files, unpushed work → `git status -sb` |
| Per-change purpose, upstream status, removal condition | Commit SHAs, rebase lineage, tags → `git log`, `gh release list` |
| Traps and dead ends: what was tried, why it broke, why upstream declined | Test bodies, check-command expansions, CI step contents → the files |
| Cadence, owner, time-box, exit conditions, stated as *triggers* | “Pending” lists, “current” version pins, “byte-identical” claims, timings |

**Tense is the tell.** A present-tense claim about repository state is drift
on a timer; a dated statement of an event or a decision does not rot. Keep
SHAs, versions, dates, and counts in the sync log, where they mean “as of
then”, and out of status prose, where they claim “now”.

**Some recorded facts are decisions.** `UPSTREAM` stores a value the tree
cannot reveal: nothing else knows which upstream ref was integrated. Store
facts whose system of record *is* the document; point at everything else.
When the document and a command disagree, the command wins.

**Encode the invariant, not the value.** “Our integration markers stay
strictly above upstream’s latest *released* number and differ from any
master number with different content” survives dozens of syncs. “Integration
marker = 13” is wrong by the next release, and an equal number with
different content silently skips upgrades. The invariant tells the next
agent what to check; the value only says what was once true.

**Delete stale state; never refresh it.** A line claiming an unpushed
commit when the tree is clean, or naming a test that no longer exists, gets
deleted or demoted to a pointer — not updated in place. Refreshing renews
the subscription and hands the next agent the same bill. Two real cases,
both false within days of being written: an “unpushed work” item that had
already shipped as a release, and a “five upstream commits pending” list
that was seven. Neither needed recording; `git status -sb` and `git log
<base>..upstream/master` were already correct.

**A sync log is a ledger, not a diary.** One short entry per sync: old base
to new base, what conflicted and why, what retired, what ran, what shipped.
Failed attempts belong there too. If an entry needs a page, it is a design
note — link it instead. Knowledge needed for one task but not forever
belongs in a commit message or the session report, not in this record.

## 4. Carry intentional patches, not an unexplained diff

- Prefix new carried-change commit subjects with `fork:`. One coherent
  behavior change per commit; no unrelated formatting or cleanup.
- Give each active patch a stable inventory ID, the reason it exists, the
  seam it disturbs, a command or test filter that proves it is still alive,
  upstream issue/PR if any, and removal condition. Name the seam rather than
  listing touched files: a file list is stale by the next refactor, and
  `git log` already knows the paths. Commit hashes alone are poor
  identifiers because private stacks change.
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
into an unannounced change to the shipped branch. Treat the same session as
the moment to re-read `FORK.md` against the tree: delete or demote every
status claim the tree now contradicts. Do not spend the sync refreshing
copied state — that is how the drift got there.

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
  changelog, and sync log together: old base, new base, conflicts and their
  cause, retirements, checks, release, and unresolved problems. Note effort
  only where it informs the exit decision. Record failed attempts without
  advancing the base. Where the new base makes an invariant in the
  compatibility contract false, restate the invariant, don't patch a number.

Repeated semantic conflicts in core code are a design warning. Time-box the
sync and propose simplifying the patch, negotiating an extension point, or
formally changing modes rather than endlessly repairing the same seam.

## 6. Make shipped builds unambiguous

Document the build, install, and release path people actually use, by its
entry point — the workflow or target that produces shipped artifacts — not
by an expanded command line or a transcription of its inputs. Distinguish
our artifacts from upstream's; check package names, update URLs, issue links,
CI publish targets, and credentials before enabling inherited release jobs.
Do not accidentally publish under upstream's identity or ship their updater.

Package versions follow the ecosystem's ordering rules, not Git tag style.
Under SemVer, `1.2.3-fork.1` sorts **below** `1.2.3`; `+fork.1` does not
increase precedence. Choose and document how consumers select our build.
Never move a released tag or replace a published version's contents.

Compatibility is bounded: state the supported scope, file/protocol/config
formats, exclusions, and the checks that enforce them, in terms that survive
a sync ("from the recorded base onward", not a version number that goes
stale at the next release). “Compatible with upstream” without a version and
scope is not a usable promise.

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
checks actually run, drift found in the existing record, and the next
maintenance action or unresolved decision. Do not turn documentation cleanup
into an unsolicited sync or release.
