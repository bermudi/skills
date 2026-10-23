# Fork maintenance

<!-- Replace placeholders with observed facts or explicit decisions. Delete
     inapplicable sections. Mark unknowns; don't invent a maintenance history. -->

## Identity

- **Mode:** <patch-carrying | independent — divergent/succession>
- **Purpose:** <why this exists; why a lighter mechanism is insufficient>
- **Maintainer:** <person/team responsible for upkeep>
- **Upstream:** <public project URL, without credentials>
- **Original base:** <tag/ref and full commit ID>
- **Current integrated base:** see [`UPSTREAM`](UPSTREAM)
- **Issues/support:** <our tracker and support scope>

## Repository conventions

| Role | Remote / branch |
|---|---|
| Our repository | `origin` |
| Original project | `upstream` |
| Our product | `main` |
| Upstream development | <e.g. `upstream/main`> |
| Clean mirror, if needed | <ref, or none> |

<Existing exceptions and why they exist. State merge/rebase policy.>

## Compatibility contract

- **Supported upstream versions / formats / interfaces:** <specific scope>
- **Intentional differences and exclusions:** <what is not promised>
- **Conformance / regression checks:** <real commands or CI jobs>
- **Upstream checks:** <real commands or CI jobs>

## Active patches

<!-- Patch-carrying forks: one row per coherent active change. Stable IDs
     survive rebases. Link detailed design notes only where needed.
     Independent projects: replace with selective-import tracking if useful. -->

| ID | Purpose and touched areas | Commit/PR | Regression coverage | Upstream status/link | Removal condition |
|---|---|---|---|---|---|
| P001 | <behavior; paths> | <reference> | <test or explicit gap> | <local/proposed/merged/rejected> | <when we stop carrying it> |

## Maintenance policy

- **Sync owner and cadence:** <who; how often; tags vs development>
- **Last successful sync:** <date, or unknown>
- **Next review:** <date or explicit trigger>
- **Sync effort limit / escalation:** <when to stop and revisit the approach>
- **Security owner and advisory sources:** <who; where fixes are monitored>
- **Security response targets:** <by severity and deployment context>
- **Supported release lines / backports:** <scope>
- **Exit or mode-change conditions:** <what makes this fork unnecessary or unsustainable>

## Builds and releases

- **Build/install:** <commands and artifact location>
- **Package identity and update source:** <our names and endpoints>
- **Version ordering:** <how consumers select our build over upstream>
- **Release owner, cadence, and process:** <commands/workflow; approval boundary>
- **Changelog and signing:** <locations/process; never secret values>

## Independent-project responsibilities

<!-- Keep only for independent projects. Scale to the actual project size. -->

- **Direction / roadmap:** <owner and location>
- **Upstream relationship:** <selective imports, compatibility-only, or no tracking>
- **Governance / contributions:** <decision owner, contribution rules, maintainer access>
- **Migration guide:** <supported entry points, limitations, and rollback>
- **Naming, license, attribution:** <identity decisions and preserved obligations>

## Sync / import log

<!-- Append actual outcomes, not planned successes. Failed syncs belong here
     too, without advancing UPSTREAM. For independent projects distinguish
     selective imports from fully integrated bases. -->

### <date> — <old base → new base / selective import / failed attempt>

- **Changes and patch retirements:** <summary>
- **Conflicts / causes:** <areas and semantic problems>
- **Effort:** <time spent; observed, not guessed>
- **Checks and results:** <what actually ran; failures and unrun checks>
- **Release:** <artifact/version, or not released>
- **Open issues / next action:** <remaining work and owner>
