# Fork maintenance

<!-- Replace placeholders with observed facts or explicit decisions. Delete
     inapplicable sections. Mark unknowns; don't invent a maintenance history.

     Record only what no command can answer. If a fact can be derived from
     git, the code, or CI within a minute, say how to derive it instead of
     copying it here: copied state rots in days, agents act on it, and every
     copied value costs re-verification at every sync. -->

## Identity

- **Mode:** <patch-carrying | independent — divergent/succession>
- **Purpose:** <why this exists; why a plugin, wrapper, or upstream PR is insufficient>
- **Maintainer:** <person/team responsible for upkeep>
- **Upstream:** <public project URL, without credentials>
- **Original base:** <tag/ref and full commit ID>
- **Current integrated base:** see [`UPSTREAM`](UPSTREAM)
- **Issues/support:** <our tracker and support scope>

## Conventions that break the defaults

<!-- Only what a fresh clone would get wrong: non-default product branch
     name, merge-vs-rebase policy, push restrictions, required local setup
     that is git-ignored, published-vs-private refs. Not an inventory of
     remotes and branches — `git remote -v`, `git branch -vv` and
     `git for-each-ref` are the source of truth. -->

<Deviations from the defaults and why. State merge/rebase policy.>

## Compatibility contract

<!-- Promises, not measurements: the scope we agree to hold, the invariants
     a sync must preserve, and the entry points that enforce them. Re-derive
     any number from the tree at the moment you act on it. -->

- **Promised scope:** <upstream base range, protocol/wire behavior, supported platforms — and what is explicitly out of scope>
- **Invariants a sync must preserve:** <rule plus the reason it exists, e.g. "our protocol number stays strictly above upstream's latest released number, or mixed pairs misdecode">
- **Release gate:** <check entry points that must pass before shipping, e.g. `just check`, CI job `X`; note checks upstream does not run for us>

## Active changes

<!-- One row per coherent carried change. Stable IDs survive rebases; commit
     hashes do not, and `git log --grep '^fork:'` already lists them.
     "Verify with" is a command or test-name filter, so it fails loudly when
     the code moves. "Seam" is where a rebase will conflict and what must
     survive it — knowledge that exists nowhere else.
     Independent projects: replace with selective-import tracking if useful. -->

| ID | Why it exists / seam it touches | Verify with | Upstream status | Removal condition |
|---|---|---|---|---|
| P001 | <behavior and the abstraction it disturbs> | <test filter or command> | <local / proposed <link> / merged / rejected> | <when we stop carrying it> |

### Rebase tripwires

<!-- Per active change: the entry points to re-check, the conflict to
     expect, and the semantics that must survive. Name the seam, not a
     file inventory. -->

## Maintenance policy

- **Sync owner and cadence:** <who; the trigger — e.g. every upstream release, weekly — and tags vs development>
- **Sync procedure:** <stable steps; put the checks in the release gate instead of restating them>
- **Sync effort limit / escalation:** <when to stop and revisit the approach>
- **Security owner and advisory sources:** <who; where fixes are monitored>
- **Security response targets:** <by severity and deployment context>
- **Supported release lines / backports:** <scope>
- **Exit or mode-change conditions:** <what makes this fork unnecessary or unsustainable>

<!-- Deliberately no "last successful sync" or "next review date" fields:
     the log below is the record and the cadence above is the trigger. A
     date nobody re-derives is a stale line waiting to happen. -->

## Builds and releases

- **Release entry point:** <the workflow or target that produces shipped artifacts; anything inherited from upstream we must not use>
- **Package identity and update source:** <our names and endpoints; nothing may resolve to upstream's>
- **Version ordering:** <how consumers select our build over upstream's>
- **Approval boundary:** <what an agent may do alone; what needs the operator>
- **Changelog and signing:** <locations/process; never secret values>

## Independent-project responsibilities

<!-- Keep only for independent projects. Scale to the actual project size. -->

- **Direction / roadmap:** <owner and location>
- **Upstream relationship:** <selective imports, compatibility-only, or no tracking>
- **Governance / contributions:** <decision owner, contribution rules, maintainer access>
- **Migration guide:** <supported entry points, limitations, and rollback>
- **Naming, license, attribution:** <identity decisions and preserved obligations>

## Sync / import log

<!-- Append-only ledger of actual outcomes, not planned successes. Failed
     syncs belong here too, without advancing UPSTREAM. This is the one
     place SHAs, versions, and dates belong — they mean "as of then".
     One short entry per event; link a design note if it needs a page.
     For independent projects, distinguish selective imports from a fully
     integrated base. -->

### <date> — <old base → new base / selective import / failed attempt>

- **Conflicts and causes:** <areas and semantic problems>
- **Retired / changed:** <patches dropped, added, or redesigned>
- **Checks and results:** <what actually ran; failures and unrun checks>
- **Release:** <artifact/version, or not released>
- **Open question:** <remaining decision and owner, or none>
