# Feature

1. Trace the affected subsystem.
2. Name the data shape and its organizing structure before any logic: a state machine over scattered booleans, a table or registry over branching, a typed model over repeated shape assumptions ([foundational-thinking](../principles/foundational-thinking.md), [model-the-domain](../principles/model-the-domain.md)). Integrating into an existing design: [redesign-from-first-principles](../principles/redesign-from-first-principles.md).
3. Write the throughput checkpoint. Each item stays, with `n/a: <reason>` if it doesn't apply:
   - **Blocking first steps:** gates that run before any fan-out.
   - **Independent streams:** disjoint files, services or layers parallelize; shared writes serialize.
   - **Shared mutable state:** split the target first ([separate-before-serializing-shared-state](../principles/separate-before-serializing-shared-state.md)); serialize only for a real invariant.
   - **Smallest safe decomposition:** if one implementer is best, say why.
4. Implement with a specific scope: file paths, the named shape, success criteria. Novel interaction or architecture with no precedent: prototype 2–3 shapes first ([exhaust-the-design-space](../principles/exhaust-the-design-space.md), [prototype](prototype.md)).
5. Verify on the matching surface ([prove-it-works](../principles/prove-it-works.md)). "Inconclusive" or wrong surface is not a pass; flag it.
6. Small ordered commits, each one verified before the next ([sequence-verifiable-units](../principles/sequence-verifiable-units.md)).

**Report:** what you built, what you chose and why, the throughput checkpoint, open decisions. Tables for design alternatives.
