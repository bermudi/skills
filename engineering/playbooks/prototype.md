# Prototype

**The prototype is a throwaway instrument for one decision.** The real build follows [feature](feature.md). Speed over polish: code quality does not matter, no tests, no abstractions. The rigor is in picking the right design cheaply. Propose variations the user didn't ask for.

1. Name the decision it exists to make: which layout, interaction or density, or for an empirical fork which behavior, timing or approach. No decision means no prototype.
2. When the design space is open, gather prior art and let the user pick directions before building. Skip when the direction is set.
3. Build in a scratch dir under `/tmp/`, outside production source. Visual: vanilla HTML/CSS/JS or the lightest stack that renders it. Behavioral or timing: the smallest script that exercises the question.
4. Comparing alternatives: put them behind one switcher (buttons or a key), each labelled ([exhaust-the-design-space](../principles/exhaust-the-design-space.md)).
5. Observe the thing you're deciding: screenshot each variant and drive it, or log the timing or output. The observation is the test.
6. Present alternatives, tradeoffs and a recommendation.

**Report:** variants explored, the evidence, tradeoffs, your recommendation, the scratch path. Say plainly that the prototype is throwaway.
