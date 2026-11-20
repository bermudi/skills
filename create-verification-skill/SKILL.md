---
name: create-verification-skill
description: >
  Generate a repo's own verify-<app> skill: how to launch, drive and observe
  the real app the way a user does, plus a feature map. Use when a repo has
  no verify skill, or a verifier ran without one.
license: MIT
disable-model-invocation: true
---

# Create a verification skill

Write `verify-<app>`: the repo's scripted way to launch the real app, drive a feature the way a user does, and capture proof. Its reader is a cold agent mid-task (usually the fusion verifier) that has never seen the app. Give it exact commands, not explanations.

## 1. Interview the repo, not the user

Answer from the code. Ask only what you can't observe.

- **Surface:** what a user touches: web UI, CLI/TUI, desktop app, API, library. Several → pick the primary, list the rest.
- **Run:** the repo's own dev command first (scripts, Makefile, README). Ports, env vars, seed data, auth.
- **Drive:** existing harnesses first (Playwright specs, expect scripts, curl-able endpoints, debug ports). Then the generic ones: `agent-browser` for web and Electron, a `tmux` session the run starts itself for CLI/TUI, `curl` for services.
- **Observe:** screenshots, ARIA snapshots, terminal transcripts, response bodies, logs, exit codes, DB state.
- **Isolate:** can a second instance run beside the user's (ports, data dirs, profiles)? If not, the skill says so and refuses to drive a shared instance.

If the checkout doesn't build or start, fix that or report it exactly before you write anything: a skill written against a broken base teaches wrong steps. An unrelated missing asset that blocks startup (a static dir the API never serves, a sample config) may be created as marked verification scaffolding and removed in cleanup.

**Stop and ask the user first**, with your pick, before building:

- Anything that stands in for a real dependency (fake models, mock services, stub APIs). A stand-in can make a journey pass while proving nothing; often the better answer is a skill that says plainly what it can't prove.
- Real credentials or paid services. Never copy them from the real environment; models and providers are the user's to name.
- Product changes needed to make the repo drivable. Those are their own issue.

## 2. Write the skill

Path: `.agents/skills/verify-<app>/SKILL.md` (devin loads project skills from there; checked 2026-11-09), plus a link for Claude Code: `ln -s ../../.agents/skills/verify-<app> .claude/skills/verify-<app>`.

Frontmatter: `name: verify-<app>` and a description that names the app, the surface and when to use it. Ground every section in what the interview found; leave no placeholders.

- **Launch:** the exact command and its ready signal. Ready means usable, not "a process answers": a DB health check can pass while init scripts still run. Launch reaches a usable state from an empty data dir, migrations and seed data included. Include teardown. Short-lived CLI: build once, then run each drive in its own tmux session.
- **Doctor:** one read-only check: process up, right build, port owned by this run, auth valid. Run it first, and again after anything surprising.
- **Drive:** real selectors and commands from this repo, not examples. Stable handles (ARIA names, data attributes, prompt strings, routes) over coordinates and tab order.
- **Evidence:** what to capture and where it goes. Proof standards:
  - the real user path, not internal setters or test-only endpoints;
  - the action and the resulting state, not only the final screen;
  - side effects (files written, rows inserted, messages sent) as well as what is visible;
  - mocks only where a production boundary already isolates the external system;
  - for a dry-run or test mode, observe what it really skips (files, network, git refs). Some dry-runs still touch the network or open a browser.
- **Cleanup:** stop only what the run started, never by process name. Evidence survives cleanup, at a location the skill names.
- **Helpers:** every shipped script is executable, and the body shows how to call it.

## 3. Seed the feature map

Write `features/README.md` plus one file for each of the top 3–5 user-facing features (find them in routes, commands, menus, docs). Follow [the example](references/feature-map-example/): a README index, then per feature an H1 and one paragraph, then exactly `Sub-features`, `How to get to it (user POV)`, `Driving it with <harness>`, `Gotchas`.

- A journey whose precondition the seed data lacks fails, and the reason goes in `Gotchas`. Never weaken a journey to make it pass.
- A proof that drives one entry point is incomplete when the map lists others.

## 4. Prove it before handing it over

Run it once end to end: launch, doctor, drive one mapped feature, capture evidence, clean up, then confirm the evidence still exists. Run cleanup after every failed attempt too, so broken attempts don't strand processes and ports. A skill that was never run is a draft.

Proved it in a stand-in (a container for a VM, a local stack for a remote one)? List every setup step the real target won't get. Those stay unverified until a run on the target covers them.

## Keep it honest

The map rots when the app changes. When a drive disagrees with the map, sort it:

- The map describes it wrong → drift: fix the map.
- Working behaviour the harness can't drive → harness gap: fix the harness, and drive it live again before committing.
- The app is broken → a product finding, reported as one. Never edit the map to match a regression, and never edit product code from this skill.

## Basis

Adapted from pstack `create-verification-skill` and `maintain-verification-skill` (cursor/plugins @ 236e548, MIT, © 2026 Lauren Tan; see `LICENSE`). Changed: harness-neutral paths, local generic drivers, maintenance folded into one section, one map example instead of two.
