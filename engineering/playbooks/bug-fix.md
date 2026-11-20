# Bug fix

**Be scientific.** Every shipped line traces to runtime evidence. A belt-and-suspenders change that "might help" is a hypothesis, not a fix: it does not ship. When evidence refutes a hypothesis, revert what it motivated. Ship the smallest change the evidence justifies.

1. Reproduce it yourself on the real surface (the repo's `verify-*` skill, `agent-browser`, a `tmux` session, `curl`). Ask the user only with a specific reason you can't reach it, after driving it as far as it goes. If it won't reproduce, synthesize the trigger, tighten conditions, or instrument until it fires.
2. Binary-search the cause. List candidate hypotheses, seeded by a trace of the subsystem and `git log`/`git blame` for regression history. Each pass, take the split that cuts the most remaining space, get runtime evidence, eliminate. When state is unclear, add logging and read it as the code runs. Don't guess. Confirm the surviving mechanism with evidence before planning the fix ([fix-root-causes](../principles/fix-root-causes.md); after two failed fixes, [attack-the-premise](../principles/attack-the-premise.md)).
3. Plan the fix. Across a function boundary, settle the data shape first ([model-the-domain](../principles/model-the-domain.md)).
4. Verify on the same surface: the original repro now passes. "Inconclusive" or wrong surface is not a pass; flag it. Unit tests show branch behavior, not bug absence.
5. Commit the failing repro test before the fix when the bug has a cheap local test path ([sequence-verifiable-units](../principles/sequence-verifiable-units.md)). Skip it when the test would be expensive or unclear.

**Report:** what was broken, root cause, fix, how you verified. Paste failing-then-passing repro output verbatim.
