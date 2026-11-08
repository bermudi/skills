# Glossary

Terms used across this repo's skills. Each skill remains self-contained; this is the shared vocabulary.

| Term | Meaning |
|---|---|
| Fusion | Collaboration policy: a lead agent keeps design, authority and review; a cheaper sidekick does implementation, verification and environment work. Transport-agnostic. |
| `fusion-herdr` | Fusion over Herdr: one persistent sidekick in a sibling pane. |
| `fusion-t3` | Fusion over T3 Code `delegate_task`: one fresh delegate per handoff; continuity is the filesystem and report files. |
| Lead | The accountable agent: plans, settles design, owns authority actions (commits, pushes, PRs, secrets), reviews every landing point. |
| Sidekick | The cheaper execution agent: implements settled plans, verifies, repairs environments. Never holds authority actions. |
| Handoff / brief | One self-contained dispatched task: goal, asks, plan, tests, frozen inputs, constraints, verify commands, report path. |
| Landing point | Any report returning implementation — gets a full-diff review and an explicit verdict before the lead proceeds. |
| Frozen input | Lead-derived value or artifact path handed over as authoritative; the receiver reuses it, never recomputes it. |
| Settled | Decided by the lead before dispatch: interfaces, behaviour, test cases. Unsettled work is never dispatched. |
| Delegate | In `fusion-t3`: one `delegate_task` child. Fresh context, ends with the handoff. |
| Yolo mode | In `fusion-herdr`: the sidekick harness's auto-approve launch mode, so execution never stalls on permission prompts. |
