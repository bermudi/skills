# Review Consolidation Guide

You have N individual review reports from different AI models reviewing the same litespec change. Your job is to consolidate them into a single meta-review that captures the best insights from each, surfaces consensus, and produces actionable next steps.

---

## Structure

Produce the consolidated report in this exact structure:

### 1. Executive Summary

One paragraph per reviewer characterizing their "personality" and focus area. Who acted as the UX reviewer? Who caught spec drift? Who found architectural issues?

Example: "GLM-5.1 acted as a Product/UX Reviewer, focusing on user-facing interactions and edge-case UI states. DeepSeek-V4-Pro acted as a Spec & Compliance Reviewer, finding contradictions between documentation artifacts..."

### 2. Consensus Findings

Issues identified by **2+ reviewers**. These are the most objective flaws — if multiple independent reviewers agree, it's real.

For each consensus finding:
- What the issue is (specific, with file:line references)
- Which reviewers found it
- Severity (use the highest severity assigned by any reviewer)
- Recommended action (specific, actionable)

### 3. Unique Strengths & Divergent Findings

Per reviewer, what they **uniquely** caught that others missed. Group by reviewer with a brief characterization of their strength.

For each unique finding:
- What was found (with file:line)
- Why it matters
- Severity from the reviewer
- Your assessment: agree (include in action items) or disagree (note why)

### 4. Phase-by-Phase Comparison

A table comparing how each reviewer handled each review phase:

| Review Phase | Reviewer A | Reviewer B | Reviewer C |
|---|---|---|---|
| Adversarial (Edge Cases) | ... | ... | ... |
| Compliance (Spec & Code) | ... | ... | ... |
| Cross-Change Consistency | ... | ... | ... |
| Build & Archive Readiness | ... | ... | ... |

Brief one-liners per cell describing what the reviewer focused on.

### 5. Scoring Analysis

Compare the scorecards across reviewers. For each dimension:

- Which reviewers passed vs failed it
- Where they disagreed and why
- **Your verdict**: the strictest score in a dimension is usually the right one — leniency is more often a miss than severity is overcorrection

Present as a merged scorecard table with your final verdict column.

### 6. Conclusion & Recommended Actions

Prioritized list of actions derived from the meta-review, ordered by impact:

1. **Must fix** (consensus findings + agreed unique findings)
2. **Should fix** (warnings from any reviewer)
3. **Nice to have** (suggestions)

Tag each action with its source reviewer(s). This list is what the fix agent will consume.

---

## Heuristics

- **Weight consensus over novelty.** If 2 of 3 reviewers flag something, it's real.
- **Don't average scores.** Take the strictest score per dimension.
- **Preserve specifics.** File:line references, exact variable names, precise scenarios — these are the valuable parts. Don't flatten them into generalities.
- **Note contradictions.** If one reviewer says X is fine and another says X is broken, explain both perspectives and assess which is more convincing.
- **Don't invent findings.** If no reviewer mentioned something, don't add it. Your job is synthesis, not supplementary review.
- **Don't lose nuance.** If a reviewer gave a detailed adversarial trace with file:line anchors, preserve the key points — the fix agent needs them.
