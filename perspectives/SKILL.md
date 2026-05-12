---
name: perspectives
description: >
  Get three divergent takes on the same problem by running `pi` in parallel
  with three different model families, then reading and synthesizing the
  results. Use when the user wants to "take a second look", "step back",
  "rethink the whole thing", "no bad ideas", "no idea is too extreme",
  multiple opinions, a second/third opinion, or any open-ended brainstorming
  where divergent reasoning beats a single confident answer. Triggers on
  phrases like "give me 3 perspectives", "rethink this with fresh eyes",
  "what would different models say", "I want diverse takes", "second look at
  X", "challenge my thinking on Y". The script saves each perspective to its
  own file and prints the output directory so the calling agent can read,
  compare, and synthesize.
---

# Perspectives

Run the same prompt across **three different model families** in parallel,
then read the three outputs and synthesize. The whole point is *divergent*
thinking — three GPTs is not three perspectives, it's one perspective in a
trench coat.

## When to invoke

The user is asking you (or themselves) to step back. Signals:

- "Take a second look at X with what we know now"
- "I've grown skeptical of Y, rethink the whole thing"
- "There are no bad ideas, no idea is too extreme"
- "Give me 3 perspectives on …"
- "Challenge this design / brainstorm alternatives"
- Any open-ended architecture, strategy, or product question where you'd
  benefit from genuinely different priors

If the request is a concrete bug fix or a well-scoped task, this is the wrong
tool — just do the work.

## Workflow

1. **Capture the prompt to a file.** These prompts tend to be multi-paragraph
   with file references. Write it to `/tmp/perspectives-prompt.md` (or take
   the path the user already provided). `pi` resolves `@path/to/file` inside
   prompts as inlined file content, so referenced files (e.g. an
   `AgenticWiki/...` note) get pulled in by each model.

2. **Run the script:**
   ```bash
   scripts/perspectives.sh -f /tmp/perspectives-prompt.md
   ```
   This kicks off three `pi --print` runs in parallel, each with a different
   model, and writes their stdout/stderr to a fresh temp directory.

3. **Read each perspective.** When the script finishes it prints the output
   directory. Read each `*.txt` file in turn — they are the assistant's final
   answer for that model.

4. **Synthesize.** Identify points of agreement (likely robust), points of
   disagreement (the interesting tension), and any idea that only one model
   surfaced (often the most valuable signal). Present the synthesis to the
   user — don't just dump three transcripts.

## Default model trio

The script picks three families on purpose:

| Slot | Model                       | Family    |
|------|-----------------------------|-----------|
| 1    | `opencode-go/kimi-k2.6`     | Moonshot  |
| 2    | `deepseek/deepseek-v4-pro`  | DeepSeek  |
| 3    | `zai/glm-5.1`               | Z.ai/GLM  |

Override with `-m` if the user prefers other families, but **keep them from
different houses**. Three GLMs will agree with each other and you'll have
learned nothing.

```bash
scripts/perspectives.sh \
  -m poe-responses/Claude-Opus-4.7,poe-responses/GPT-5.4,opencode-go/kimi-k2.6 \
  -f /tmp/perspectives-prompt.md
```

See `pi --list-models` for what's available locally.

## Script options

```
scripts/perspectives.sh [-m a,b,c] [-o outdir] [-t thinking] [-f promptfile] [PROMPT...]
```

- `-m`  comma-separated list of exactly three `provider/model[:thinking]` patterns
- `-o`  output directory (default `/tmp/perspectives-<unix-timestamp>`)
- `-t`  thinking level applied to all three (`off|minimal|low|medium|high|xhigh`)
- `-f`  read prompt from a file (becomes `@file` arg to pi, so its contents are inlined)
- positional args  appended to the prompt verbatim
- `-h`  help

The script exits non-zero if any of the three runs failed; check the matching
`*.err` file in the output directory to see why.

## Output layout

```
/tmp/perspectives-1730764800/
├── README.md                          # the prompt + which model went where
├── 0_opencode-go_kimi-k2.6.txt        # assistant answer
├── 0_opencode-go_kimi-k2.6.err        # stderr (status, errors)
├── 0_opencode-go_kimi-k2.6.session/   # pi session dir, can be resumed
├── 1_deepseek_deepseek-v4-pro.txt
├── 1_deepseek_deepseek-v4-pro.err
├── 1_deepseek_deepseek-v4-pro.session/
├── 2_zai_glm-5.1.txt
├── 2_zai_glm-5.1.err
└── 2_zai_glm-5.1.session/
```

Each `.session/` directory is a normal `pi` session — if one perspective is
worth pulling on, you can drill into it with:

```bash
pi --session-dir /tmp/perspectives-.../1_deepseek_deepseek-v4-pro.session -c \
   "Expand on the third option you proposed."
```

## Notes & gotchas

- **Token cost is 3×.** That is the trade. Use this for hard, high-leverage
  questions — not for "rename this variable".
- **Tools are enabled by default.** Each model runs with the normal pi tool
  belt (read, bash, edit, etc.) so they can investigate the codebase
  themselves. If you want pure reasoning with no side effects, pass
  `--tools read,grep,find,ls` via shell-quoted append (edit the script if
  this becomes a regular need).
- **`@file` paths in the prompt are resolved by pi**, relative to pi's cwd
  when it runs. Use absolute paths in the prompt file to avoid surprises.
- **Sessions are kept** so you can resume any single perspective. Delete the
  output directory when you're done.
- **One model failing is fine.** The other two still produce useful
  perspectives; the script reports which slot failed and why.
