# Refactoring

**The structure changes; the behavior does not.** If the cleanup reveals a missing feature or a real bug, split it out (a separate issue) and ship the structural change first against the pinned contract. A redesign is allowed, but name it and use [feature](feature.md).

1. Pin the behavior contract first: trace the subsystem, then write a characterization test, snapshot or equivalence harness that captures current behavior before any structure moves. Type check and lint are not a pin.
2. Name the structure the code is missing ([model-the-domain](../principles/model-the-domain.md)). Boring code stays when the shape is clear and local. The reshape must delete branches or invalid states, not add indirection.
3. Name the target shape: module layout, types and call graph as if built today ([foundational-thinking](../principles/foundational-thinking.md), [redesign-from-first-principles](../principles/redesign-from-first-principles.md)).
4. Subtract before you add: delete dead code, collapse one-caller wrappers, drop redundant validators and orphan references first ([subtract-before-you-add](../principles/subtract-before-you-add.md), [laziness-protocol](../principles/laziness-protocol.md)). A speculative cleanup that "might help" gets reverted.
5. Move in small behavior-preserving steps, each keeping the pin green. For API reshapes, migrate every caller and delete the old API in the same change ([migrate-callers-then-delete-legacy-apis](../principles/migrate-callers-then-delete-legacy-apis.md)). No shims, no parallel old and new paths. Check every rename against the files: renames miss usages in strings, prose and back-references. Non-trivial mechanical edits get a codemod or script ([build-the-lever](../principles/build-the-lever.md)).
6. Prove behavior is unchanged on the real artifact ([prove-it-works](../principles/prove-it-works.md)): for larger reshapes, a script that diffs old vs new outputs, a replayed baseline, or a smoke run on the real surface.
7. Confirm it's worth keeping: it must lower reader load somewhere ([minimize-reader-load](../principles/minimize-reader-load.md)). If not, revert it.
8. Commits in order: subtraction, then reshape, then follow-on cleanup, each green.

**Report:** the structure that changed, the pin, the equivalence proof, the reader-load change, what shipped and what got reverted. No new behavior.
