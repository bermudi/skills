# Glossary

Terms used across this repo's skills. Each skill remains self-contained; this is the shared vocabulary.

| Term | Meaning |
|---|---|
| Fusion | Collaboration policy: a lead agent keeps design, authority and review; a cheaper sidekick does implementation, checks and environment work; a clean-session verifier checks the accepted change. Works over Herdr or T3 Code. |
| Lead | The accountable agent: plans, settles design, owns authority actions (commits, pushes, PRs, secrets), reviews every landing point. |
| Sidekick | The cheaper execution agent: implements settled plans, verifies, repairs environments. Never holds authority actions. |
| Handoff / brief | One self-contained dispatched task: goal, asks, plan, tests, frozen inputs, constraints, verify commands, report path. |
| Landing point | Any report returning implementation — gets a full-diff review and an explicit verdict before the lead proceeds. |
| Frozen input | Lead-derived value or artifact path handed over as authoritative; the receiver reuses it, never recomputes it. |
| Settled | Decided by the lead before dispatch: interfaces, behaviour, test cases. Unsettled work is never dispatched. |
