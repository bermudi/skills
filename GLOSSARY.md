# Glossary

Terms used across this repo's skills. Each skill remains self-contained; this is the shared vocabulary.

| Term | Meaning |
|---|---|
| Fusion | Collaboration policy: a lead agent carries a task to a verified PR, keeping design, authority and review; a cheaper sidekick does implementation, checks and environment work; a clean-session verifier checks the accepted change. Works over Herdr or T3 Code. |
| Lead | The accountable agent: plans, settles design, owns authority actions (commits, pushes, PRs, secrets), reviews every landing point. |
| Sidekick | The cheaper execution agent: implements settled plans, verifies, repairs environments. Never holds authority actions. |
| Verifier | Clean-session agent (neither lead nor sidekick) that drives the accepted change live and returns a verdict with proof per finding. |
| Verdict | The verifier's one-line result: `PASS`, `PASS+NOTES` (no proven defect, notes the lead must answer) or `FAIL` (at least one proven finding). `verify-pr` posts it as a PR comment and as a `verify-pr` commit status on the checked commit (`success` or `failure`). |
| Verify skill | A repo's own `verify-<app>` skill: launch, doctor, drive, evidence, cleanup, plus a feature map. Made with `create-verification-skill`. |
| Handoff / brief | One self-contained dispatched task: goal, asks, plan, tests, frozen inputs, constraints, verify commands, report path. |
| Landing point | Any report returning implementation — gets a full-diff review and an explicit verdict before the lead proceeds. |
| Frozen input | Lead-derived value or artifact path handed over as authoritative; the receiver reuses it, never recomputes it. |
| Settled | Decided by the lead before dispatch: interfaces, behaviour, test cases. Unsettled work is never dispatched. |
| Playbook | One short step list in the `engineering` skill for a type of task (bug fix, feature, refactoring, perf, prototype, investigation). The lead picks one per task. |
| Principle | One short engineering rule in the `engineering` skill, read only when it applies. |
