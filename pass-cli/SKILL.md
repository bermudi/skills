---
name: pass-cli
description: >
  Retrieve secrets, credentials, and tokens from Proton Pass vaults via the
  pass-cli, including auth-error auto-recovery. Invoked explicitly.
disable-model-invocation: true
---

# Pass CLI — Secrets Retrieval

Retrieve credentials, tokens, and secrets from Proton Pass vaults. The CLI is
already installed and configured; you just need to keep your session alive.

## Session Health

Don't pre-check — just run your command. If it fails with an authentication
error (messages like "not authenticated", "session expired", "401", or
"invalid session"), use the Auto-Recovery flow below.

Do NOT re-auth for other failures ("item not found", "permission denied",
"vault not found") — those mean you have the wrong vault name or item title.

## Discovery

List what you have access to:

```bash
pass-cli vault list --output json       # All vaults
pass-cli share list --output json       # Vaults + direct shares
pass-cli item list --output json        # All accessible items
pass-cli item list --vault-name "Vault Name" --output json  # Items in a specific vault
```

Always use `--output json` when you need to parse results programmatically.

## Reading Secrets

Every read command **requires** the `PROTON_PASS_AGENT_REASON` environment
variable — a brief explanation of why you need this secret. It's mandatory.

### Read a full item

```bash
PROTON_PASS_AGENT_REASON="Need GitHub token to push release" \
  pass-cli item view --vault-name "Work" --item-title "GitHub PAT"
```

You can also address items by URI:

```bash
PROTON_PASS_AGENT_REASON="..." pass-cli item view "pass://SHARE_ID/ITEM_ID"
```

### Read a single field

```bash
PROTON_PASS_AGENT_REASON="Logging into admin dashboard" \
  pass-cli item view --vault-name "Work" --item-title "Admin Dashboard" --field password
```

Use `--field` when you only need one field (password, username, token, etc.)
to avoid exposing unrelated fields to context.

## Quick Reference

```bash
pass-cli info                                          # Session status
pass-cli vault list --output json                      # List vaults
pass-cli item list --vault-name <NAME> --output json   # Items in vault
pass-cli item view --vault-name <V> --item-title <T>   # Read full item
pass-cli item view ... --field <FIELD>                 # Read single field
pass-cli test                                          # API connectivity check
pass-cli logout --force                                # Kill stale session
```

## Auto-Recovery

If a command fails with an authentication error:

```bash
# Ensure the env file exists
if [ ! -f ~/.pass-cli-env ]; then
  echo "FATAL: ~/.pass-cli-env not found. Cannot re-authenticate."
  echo "Create it with: echo 'export PROTON_PASS_PAT=\"<your-token>\"' > ~/.pass-cli-env && chmod 600 ~/.pass-cli-env"
  exit 1
fi

source ~/.pass-cli-env

if [ -z "$PROTON_PASS_PAT" ]; then
  echo "FATAL: PROTON_PASS_PAT is empty in ~/.pass-cli-env. Cannot re-authenticate."
  exit 1
fi

pass-cli logout --force
export PROTON_PASS_SESSION_DIR="/tmp/pass-agent-$(date +%s)"
PROTON_PASS_PERSONAL_ACCESS_TOKEN="$PROTON_PASS_PAT" pass-cli login
pass-cli info  # confirm
```

Then retry the original command.

The PAT lives in `~/.pass-cli-env` (mode 600, never committed). This file is
sourced at recovery time — the token never appears in the skill text sent to the
model provider. Never echo `$PROTON_PASS_PAT`.

## Gotchas

- **Never echo the PAT.** It's sourced from `~/.pass-cli-env` at recovery time.
  Resolve `$PROTON_PASS_PAT` into the command, don't print it.
