---
name: pass-cli
description: >
  Safely retrieve Proton Pass secrets or inject them into a command or protected
  config file with pass-cli, always through a scoped, audited Agent-token
  session.
disable-model-invocation: false
---

# Pass CLI — Safe Secret Consumption

Use Proton Pass secrets by the least-exposing route. This skill covers finding
an accessible secret, passing it to a process, or rendering a requested local
config file. It does **not** administer vaults, shares, agents, or access
permissions: those are owner actions with a larger blast radius.

All `pass-cli` usage runs as a scoped, audited Agent token in an isolated
session directory—never as the account owner's logged-in session.

## Choose the route before reading anything

| Need | Use |
| --- | --- |
| A program needs a secret, but the agent does not | `pass-cli run` with a `pass://` reference. This is the default. |
| A requested config artifact needs a secret | `pass-cli inject` to an explicit file path. This writes secret material to disk. |
| An interactive login needs a TOTP code | `pass-cli item totp`. The only value allowed into context — it expires in seconds. |

Agents never read secret values. If a task seems to require the value in
context, that is a design smell: restructure it so the consuming process reads
the secret itself (`pass-cli run` / `inject`). If no restructuring avoids it,
stop and ask bermudi to retrieve the value himself, outside agent context.

Never use `pass-cli run --no-masking`. Never use `pass-cli item view` — it
prints the value (or whole item) to stdout, and once a secret has entered
context it has already leaked. Do not put a resolved value in a shell command,
source file, commit, ticket, or final response.

## Agent session is mandatory

Agents never use the account owner's session. The default session directory
belongs to the logged-in human account: an unguarded `pass-cli` call executes
with the owner's full access—every vault, no reason prompt, no audit trail—and
silently defeats the point of Agent tokens.

Every `pass-cli` invocation runs behind this guard, in the same shell as the
command it precedes (separate shell or tool calls do not retain exports):

```bash
# --- pass-cli Agent session guard ---
export PROTON_PASS_SESSION_DIR="${PASS_CLI_AGENT_SESSION_DIR:-$HOME/.local/share/pass-cli-agent}"

# Tripwire: never let the Agent session resolve to the owner's default directory.
case "$PROTON_PASS_SESSION_DIR" in
  "$HOME/.local/share/proton-pass-cli")
    printf '%s\n' 'FATAL: refusing to use the owner session directory' >&2
    exit 1 ;;
esac

(umask 077; mkdir -p "$PROTON_PASS_SESSION_DIR")

# A valid Agent session identifies itself as an access-token session.
# (Marker string below matches `pass-cli info` output in an Agent session;
# verify once from a live Agent session if info's wording changes.)
if ! pass-cli info 2>/dev/null | grep -q 'Personal Access Token'; then
  [ -r "$HOME/.pass-cli-env" ] || {
    printf '%s\n' 'FATAL: Agent credentials not provisioned; ask the owner for ~/.pass-cli-env.' >&2
    exit 1
  }
  . "$HOME/.pass-cli-env"   # owner-managed; never print, edit, or inspect it
  : "${PROTON_PASS_PAT:?FATAL: PROTON_PASS_PAT is not configured}"
  pass-cli logout --force 2>/dev/null || true   # discards a stale Agent session only
  PROTON_PASS_PERSONAL_ACCESS_TOKEN="$PROTON_PASS_PAT" pass-cli login || exit 1
  unset PROTON_PASS_PAT PROTON_PASS_PERSONAL_ACCESS_TOKEN
fi

# --- the actual pass-cli command runs here, in this same shell ---
```

The `info` check is authentication, not discovery: Agent sessions expire after
two hours, so re-login is a routine path, and the grep fails closed—a session
that would run as the owner's account stops the guard instead of proceeding.
Item-not-found, vault-not-found, and permission errors still need discovery or
an owner access change, not re-authentication.

If login fails with `invalid, expired or has been deleted`, the Agent token
itself is dead. Stop and ask the owner to renew it and update the env file;
never fall back to the owner session. Do not echo `$PROTON_PASS_PAT` or pass
it by a command-line flag, and never skip the guard because it seems like
overhead—an unguarded call silently runs as the owner.

If login fails because secure key storage is unavailable (common in a headless
container), stop and explain the error. The owner may deliberately choose the
documented `PROTON_PASS_KEY_PROVIDER=fs` fallback; do not enable it silently,
because it stores the local encryption key on disk.

## Discover precise identifiers

Discovery exposes item metadata, so list only the scope needed for the task.
Use JSON when parsing it.

```bash
pass-cli vault list --output json
pass-cli item list --vault-name "Vault Name" --output json
```

Once found, prefer the vault share ID and item ID for automation. Names are
convenient for an interactive one-off, but duplicate vault or item names can
resolve to the wrong object.

## Give a process a secret without exposing it

Use a field-level reference in an environment variable, then run the target as
a child process. `pass-cli` replaces the reference only for that child and
masks resolved values in its output by default.

```bash
export DEPLOY_TOKEN='pass://SHARE_ID/ITEM_ID/token'
pass-cli run -- ./deploy.sh
```

For project configuration, keep only references in a gitignored env file:

```dotenv
DATABASE_PASSWORD=pass://SHARE_ID/ITEM_ID/password
```

```bash
pass-cli run --env-file .env.secrets -- ./start-server
```

A TOTP reference resolves to the current code. Use `?totp=uri` only when the
task explicitly requires the underlying `otpauth://` URI.

## Render a requested configuration file

`inject` materializes secrets. Only use it when the task explicitly needs that
file, choose an explicit output path, and keep the default `0600` permissions.
Never write the result to stdout.

```yaml
# app-config.yaml.template
api_token: '{{ pass://SHARE_ID/ITEM_ID/token }}'
```

```bash
pass-cli inject \
  --in-file app-config.yaml.template \
  --out-file .runtime/app-config.yaml
```

Do not use `--force` unless the user has explicitly approved overwriting that
specific file. Treat the generated file as secret material: do not commit it.

## Discover structure without reading values

Field names, item types, and identifiers come from metadata, which never
contains secrets:

```bash
pass-cli item list --output json --vault-name "Vault Name"
```

The JSON payload carries only `title`, `item_type`, IDs, and timestamps.
`--show-secrets` would embed full item content, but pass-cli refuses it in
Agent sessions — do not try to work around that guard (e.g. via the owner's
session).

For an interactive login that needs a one-time code, `pass-cli item totp`
prints the current TOTP value. This is the one sanctioned read: the code
dies within seconds. Use it immediately, never log, store, or repeat it.

An Agent-token `item totp` call requires a non-empty reason (at most 300
characters). State the concrete task purpose; never include a secret in the
reason.

## Audit boundary

The account owner can inspect Agent accesses with:

```bash
pass-cli agent monitor "agent-name" --output json
```

`agent monitor` requires the owner's session, so agents do not run it—ask the
owner to inspect the trail. Do not create, renew, delete, grant, or revoke
Agents/PATs as part of a secret retrieval task. Ask the owner to provision the narrowest possible, expiring
viewer access—ideally to the single required item—when access is missing.

## Quick reference

Every invocation below runs behind the Agent session guard.

```bash
pass-cli vault list --output json
pass-cli item list --vault-name "Vault Name" --output json
pass-cli run --env-file .env.secrets -- ./command
pass-cli inject --in-file template --out-file .runtime/config
PROTON_PASS_AGENT_REASON="..." pass-cli item totp --share-id ID --item-id ID
pass-cli info
pass-cli test
```
