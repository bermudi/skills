# Perf

**Tie every fix to a measurement.** Don't read source instead of measuring.

1. Capture a baseline on the real surface. Vet it and each later number ([explain-the-number](../principles/explain-the-number.md)).
2. Trace the code to ground hypotheses. Don't claim a ceiling without running it. Try the mantras in order, cheapest first, and stop when one meets the target:
   1. Don't do it. Stop work whose result nothing uses.
   2. Do it, but don't do it again.
   3. Do it less.
   4. Do it later.
   5. Do it when they're not looking.
   6. Do it concurrently.
   7. Do it cheaper.
3. Plan the fix from the trace. Verify each attempt before the next ([sequence-verifiable-units](../principles/sequence-verifiable-units.md)). Capture a post-fix measurement.
4. Compare the artifacts with a script, not by eye. "Inconclusive" is not a pass; flag it.
5. Cite the measurement in the PR.

**Report:** baseline, post-fix number, delta, run count and spread, artifact path.
