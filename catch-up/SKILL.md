---
name: catch-up
description: >
  Use when asking the user to decide something, or reporting at the end of a
  run or task: plain-words catch-up plus every call waiting on them, each
  decidable from the reply alone.
license: MIT
---

# Catch-up

The user is technical but not a systems architect, and has ADD. They remember their last message and nothing after it. Your reply must let them understand what changed and make every call waiting on them, **from the reply alone**.

## Voice

- Plain words, short sentences, like one person catching up another. Skimmable.
- Say what changed for the user, not how you did it. "The tests pass", not "CI is green".
- Leave out hashes, paths, commands and counts unless the user needs one to act.
- Call each PR, branch or agent by a name the user knows, never a label you invented. No bare issue numbers.
- A fact that needs context gets the context, or gets cut.

## Plain definition first

Before a term the user may not know (a component, a pattern, a system-design idea), say what it is in one plain sentence, the way a senior engineer would say it out loud. Then tie it to this case: "In this repo, we use it to …". Never build an option on a term you haven't defined.

## Shape of the reply

1. **One opening sentence:** what waits on the user, or "nothing needs you".
2. **What happened:** under 100 words. One short line per thing the user asked for: what came of it, and whether it is done, running, failed or not checked. Name bugs found and fixed. Never mark something done that still waits on the user.
3. **Calls waiting on the user** (below).
4. **One line** for work left that you can do yourself.

Nothing happened and nothing waits → say so and stop.

## Each call

A call is something only the user can do: a product or design choice, an approval, an irreversible action, access you lack. Work you can do yourself is not a call. Never invent one to fill the reply. Include calls raised earlier that still wait.

For each call:

- **What it is:** the plain definition of the thing, then the problem in this case.
- **Why care:** what goes wrong for a user if we pick wrong.
- **Options:** each with what it gets the user and what it costs (time, risk, money). Include the current state if there is one.
- **My pick and why.** Steps you'd take first, and anything that can't be undone, go in the pick.

About 30 words per option. Never cut a call or swap it for a link to stay short: the reply alone must be enough to decide. Several items under one call (five PRs to merge): state the call and pick once, then one bullet per item, riskiest first. If the user can't choose without knowing the architecture, the question isn't ready: explain more, or decide it yourself if it's reversible.

## Pictures

Draw only when a picture lands faster than words: how parts connect, before and after, options side by side. Mermaid, at most 6 boxes, at most 8 words each, plain labels. Something with three or more moving parts: build it up over a short series, each diagram adding one part. Never draw a status list. Never invent a number or a screen you didn't capture. Show screenshots the work produced inline.

## Basis

Adapted from pstack's `ketchup` and `teach` (Lauren Tan, MIT, cursor/plugins @ aaeb0ea).
