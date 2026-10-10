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

All native `pass-cli` usage runs as a scoped, audited Agent token in an isolated
session directory—never as the account owner's logged-in session.

## Choose the route before reading anything

| Need | Use |
| --- | --- |
| A program needs keys already in a configured encrypted snapshot | `pass-keys run PROFILE -- ./consumer`. Prefer this local route; no native Pass call or authentication guard. |
| A program needs another secret reference on demand | Guarded `pass-cli run` with a `pass://` reference. Native output masking stays enabled. |
| A requested config artifact needs a secret | Guarded `pass-cli inject` to an explicit file path. This writes secret material to disk. |
| An interactive login needs a current TOTP code | Guarded `pass-cli item totp`. The only value allowed into context—it expires in seconds. |

Agents never read secret values. If a task seems to require the value in
context, restructure it so the consuming process reads the secret itself. If
no restructuring avoids it, stop and ask bermudi to retrieve the value himself,
outside agent context. Do not put a resolved value in a shell command, source
file, commit, ticket, or final response.

`pass-keys run` exports the selected profile's keys to its child and **does not
mask stdout or stderr**. Use a consumer that will not print credentials. Never
use it for `printenv`, `env`, secret echoes, or diagnostic dumps in an agent tool
call. `pass-keys get PROFILE KEY_NAME` prints a secret: it is for an application
pipe only, never an agent tool call or a way to inspect a value.

Local `get`, `run`, and `status` use the encrypted per-profile snapshot without
calling native Pass, logging in, or refreshing on application launch. A
missing/locked/corrupt snapshot fails locally; do not add an online fallback.
`pass-keys status` reports local availability and refresh age without values.
A last-good snapshot may outlive token expiry or grant revocation; local use is
not a fresh remote access check. Explicit `pass-keys warm pi` is a task repair
or requested refresh, **not** an application-launch bootstrap.

Never use `pass-cli run --no-masking`. Never use `pass-cli item view`—it
prints the value (or whole item) to stdout, and once a secret has entered
context it has already leaked.

## Agent session is mandatory for native Pass

Agents never use the account owner's session. The native default session
belongs to the logged-in human account: an unguarded `pass-cli` call executes
with the owner's full access—every vault, no reason prompt, no audit trail—and
silently defeats the point of Agent tokens.

Every native `pass-cli` invocation runs behind this guard, in **Bash**, in the
same shell as the command it precedes (separate shell or tool calls do not
retain exports). Do not run it before local `pass-keys run` application launches.
Never enable shell tracing or dump the environment.

```bash
# --- native pass-cli Agent session guard ---
set +x
: "${HOME:?FATAL: HOME is not set}"
export PATH="$HOME/bin:$PATH"  # use the installed native pass-cli wrapper first

# Enumerate variable NAMES only; inherited login/session/key-provider overrides
# must not authenticate or steer this call. Never source a credential file.
for pass_cli_var in "${!PROTON_PASS_@}"; do
  unset "$pass_cli_var" || {
    printf '%s\n' 'FATAL: cannot clear inherited Proton Pass overrides' >&2
    exit 1
  }
done
unset pass_cli_var

# Canonicalize before mkdir/chmod: aliases and symlinks to the owner are refused.
pass_cli_session_dir="$(realpath -m -- "${PASS_CLI_AGENT_SESSION_DIR:-$HOME/.local/share/pass-cli-agent}")" || exit 1
pass_cli_owner_dir="$(realpath -m -- "$HOME/.local/share/proton-pass-cli")" || exit 1
if [[ "$pass_cli_session_dir" == "$pass_cli_owner_dir" ]]; then
  printf '%s\n' 'FATAL: refusing to use the owner session directory' >&2
  exit 1
fi
export PROTON_PASS_SESSION_DIR="$pass_cli_session_dir"
export PASS_CLI_AGENT_SESSION_DIR="$pass_cli_session_dir"
(umask 077; mkdir -p -m 700 -- "$PROTON_PASS_SESSION_DIR" &&
  chmod 700 -- "$PROTON_PASS_SESSION_DIR") || exit 1
unset pass_cli_session_dir pass_cli_owner_dir

# Keep info private. An ordinary Personal Access Token is NOT an Agent token.
if pass_cli_info="$(pass-cli info 2>/dev/null)" &&
   [[ "$pass_cli_info" == *'Personal Access Token'* &&
      "$pass_cli_info" == *'[Agent]'* ]]; then
  :
else
  unset pass_cli_info
  # Reuse pass-keys' authenticated scoped Agent lane and encrypted bootstrap.
  # This is an explicit task repair, never a launch-time fallback.
  if ! pass-keys warm pi >&2; then
    printf '%s\n' 'FATAL: Agent session repair failed; stop and resolve the reported error with the owner.' >&2
    exit 1
  fi
  if ! pass_cli_info="$(pass-cli info 2>/dev/null)" ||
     [[ "$pass_cli_info" != *'Personal Access Token'* ||
        "$pass_cli_info" != *'[Agent]'* ]]; then
    printf '%s\n' 'FATAL: selected session is not an Agent PAT after warm pi; its configured sessionDir may differ. Ask the owner to align it with PASS_CLI_AGENT_SESSION_DIR; no owner-session fallback.' >&2
    exit 1
  fi
fi
unset pass_cli_info

# --- the actual native command, with its own task-specific reason, goes here ---
```

The private `info` check is authentication, not discovery. Sessions expire, so
repair is routine, but **both** `Personal Access Token` and `[Agent]` must be
present; a plain PAT is not enough. During repair, `pass-keys warm pi` verifies
the profile's configured expected named Agent identity using its existing Go
authentication path. The guard then rechecks the **selected** session's Agent
role, not the owner's account. A profile's explicit `sessionDir` can override
the environment for warm; if the selected session still fails verification,
stop and have the owner align the directories—never silently switch sessions.

Bootstrap PATs are encrypted Secret Service records selected by `patKey`.
Never read, print, or parse those records, write a new JWT/keyring parser, or
source `~/.pass-cli-env`. The legacy plaintext PAT files were deleted with
the owner's approval on 2026-10-10; do not recreate them. Inherited
`PROTON_PASS_*` variables are stripped, not sourced from another file.

Warm's authentication/network failures are reported by the core as public-safe
errors; keep its operational output on stderr, do not inspect raw login output
or credentials to diagnose them. Missing credentials, an expired/revoked PAT,
or unavailable/locked secure storage require owner repair. Do not enable the
insecure filesystem key provider or fall back to the owner session. Item- or
vault-not-found and permission errors need scoped discovery or an owner access
change, not repeated re-authentication.

## Discover precise identifiers

Discovery exposes item metadata, so list only the scope needed for the task.
Use JSON when parsing it. After the guard, attach a non-empty reason describing
**this actual access**, not an inherited or blanket reason. Use a command-local
`PROTON_PASS_AGENT_REASON` assignment (at most 300 characters, no secrets) for
each native data-access call. The guard clears inherited reasons; set the
reason on the actual command **after** it. Warm supplies its own per-access
reasons through the core.

```bash
PROTON_PASS_AGENT_REASON="Locate the vault for the requested deployment credential" \
  pass-cli vault list --output json
PROTON_PASS_AGENT_REASON="Find the token item for the requested deployment" \
  pass-cli item list --vault-name "Vault Name" --output json
```

Once found, prefer the vault share ID and item ID for automation. Names are
convenient for an interactive one-off, but duplicate vault or item names can
resolve to the wrong object.

## Give a process a secret without exposing it

For known snapshot keys, use the configured profile whose environment-variable
names the consumer expects. No Native Pass guard is needed for this local read:

```bash
pass-keys run PROFILE -- ./consumer
```

For other references needed on demand, use guarded native `pass-cli run`. It
replaces field-level references only for the child and masks resolved values in
its output by default. Never ask the child to print secrets even with masking.

```bash
export DEPLOY_TOKEN='pass://SHARE_ID/ITEM_ID/token'
PROTON_PASS_AGENT_REASON="Authenticate the deployment requested by the user" \
  pass-cli run -- ./deploy.sh
```

For project configuration, keep only references in a gitignored env file:

```dotenv
DATABASE_PASSWORD=pass://SHARE_ID/ITEM_ID/password
```

```bash
PROTON_PASS_AGENT_REASON="Connect the requested server to its database" \
  pass-cli run --env-file .env.secrets -- ./start-server
```

A native TOTP reference resolves to the current code. Use `?totp=uri` only when
the task explicitly requires the underlying `otpauth://` URI, and pass it only
to the consumer, never into context. Do not treat a cached snapshot as a source
of current TOTP codes.

## Render a requested configuration file

`inject` materializes secrets. Only use it when the task explicitly needs that
file, choose an explicit output path, and keep the default `0600` permissions.
Never write the result to stdout.

```yaml
# app-config.yaml.template
api_token: '{{ pass://SHARE_ID/ITEM_ID/token }}'
```

```bash
PROTON_PASS_AGENT_REASON="Render the service configuration requested by the user" \
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
PROTON_PASS_AGENT_REASON="Identify the available fields for the requested deployment token" \
  pass-cli item list --output json --vault-name "Vault Name"
```

The JSON payload carries only `title`, `item_type`, IDs, and timestamps.
`--show-secrets` would embed full item content, but pass-cli refuses it in
Agent sessions—do not try to work around that guard (e.g. via the owner's
session).

For an interactive login that needs a one-time code, `pass-cli item totp`
prints the current TOTP value. This is the one sanctioned read: the code
dies within seconds. Use it immediately, never log, store, or repeat it.

An Agent-token `item totp` call requires a non-empty reason (at most 300
characters). State the concrete task purpose; never include a secret in the
reason. Run after the native guard:

```bash
PROTON_PASS_AGENT_REASON="Complete the interactive login requested by the user" \
  pass-cli item totp --share-id ID --item-id ID
```

## Audit boundary

The account owner can inspect Agent accesses with:

```bash
pass-cli agent monitor "agent-name" --output json
```

`agent monitor` requires the owner's session, so agents do not run it—ask the
owner to inspect the trail. Cached reads do not create a new native access;
source accesses are audited during explicit warm. Do not create, renew,
delete, grant, or revoke Agents/PATs, or use `pass-keys add`/`drop` to change
items or permissions as part of a secret retrieval task. Ask the owner to
provision the narrowest possible, expiring viewer access—ideally to the single
required item—when access is missing.

## Quick reference

Local routes (no native guard, no launch-time warm):

```bash
pass-keys status
pass-keys run PROFILE -- ./consumer
```

Native routes require the guard and a concrete per-call reason as above:
metadata-only `vault list` / `item list`, masked `run`, explicit-file `inject`,
and current-code `item totp`. `info` is a private authentication check, not a
secret read. Repair uses `pass-keys warm pi` with operational output on stderr;
never use a credential file or the owner session as a fallback.
