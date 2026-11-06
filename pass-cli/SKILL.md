---
name: pass-cli
description: >
  Retrieve Proton Pass secrets or inject them into a command or config file
  with pass-cli, through a scoped, audited Agent-token session.
disable-model-invocation: false
---

# Pass CLI — safe secret consumption

Use secrets by the least-exposing route. Scope: find an accessible secret, hand it to a process, or render a requested config file. Not vault, share, agent or permission administration: those are owner actions.

## Rule zero: agents never read secret values

If a task seems to need the value in context, restructure it so the consuming process reads the secret. If that is impossible, stop and ask bermudi to fetch it outside agent context. Never put a resolved value in a command, source file, commit, ticket or reply. Once a secret enters context it has leaked.

## Choose the route

| Need | Route |
| --- | --- |
| Program needs keys already in a configured encrypted snapshot | `pass-keys run PROFILE -- ./consumer`. Local; no native Pass call, no guard. |
| Program needs another secret on demand | Guarded `pass-cli run` with a `pass://` reference (output masking stays on). |
| A requested config file needs a secret | Guarded `pass-cli inject` to an explicit path. Writes secret material to disk. |
| Interactive login needs a TOTP code | Guarded `pass-cli item totp`. The only value allowed into context; it dies in seconds. |

## pass-keys (local)

- `run` exports the profile's keys to its child and **does not mask stdout/stderr**: use consumers that don't print credentials; never for `env`, `printenv`, echoes or diagnostic dumps. `get PROFILE KEY` prints the secret: application pipes only, never an agent tool call.
- `get`, `run`, `status` read the encrypted snapshot locally: no native Pass call, no login, no refresh at launch. A missing/locked/corrupt snapshot fails locally; add no online fallback. `status` shows availability and age, never values.
- A last-good snapshot can outlive token expiry or revocation, so local use is not a fresh access check. `pass-keys warm pi` is for task repair or a requested refresh, never a launch bootstrap.
- Never `pass-cli run --no-masking`. Never `pass-cli item view` (prints the value or the whole item).

## Native pass-cli: Agent session guard (mandatory)

The default native session is the owner's: an unguarded call runs with full access, no reason prompt, no audit trail. Every native `pass-cli` call runs behind this guard, in Bash, **in the same shell** as the command (exports don't survive separate tool calls). No shell tracing, no environment dumps, and never before a `pass-keys run` launch.

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

The `info` check is authentication, not discovery. Sessions expire, so repair is routine, but **both** `Personal Access Token` and `[Agent]` must appear (a plain PAT is not enough). `pass-keys warm pi` verifies the profile's expected named Agent identity; the guard then rechecks the *selected* session. If a profile's `sessionDir` overrides the environment and verification still fails, stop and have the owner align the directories. Never switch sessions silently.

- Bootstrap PATs are encrypted Secret Service records chosen by `patKey`. Never read, print or parse them, never write a JWT/keyring parser, never source `~/.pass-cli-env` (legacy plaintext PAT files deleted 2026-10-10; don't recreate). Inherited `PROTON_PASS_*` vars are stripped, not sourced elsewhere.
- Keep warm's operational output on stderr; don't inspect raw login output or credentials to diagnose it. Missing credentials, an expired/revoked PAT, or unavailable/locked secure storage need owner repair. No insecure filesystem key provider, no owner-session fallback. Not-found and permission errors need scoped discovery or an owner access change, not re-authentication.

## Native calls

Every data-access call needs a command-local `PROTON_PASS_AGENT_REASON` (≤300 chars, no secrets) naming *this* access. The guard clears inherited reasons; set it on the command after the guard.

**Discovery** exposes metadata only (`title`, `item_type`, IDs, timestamps); list just the scope you need and use JSON:

```bash
PROTON_PASS_AGENT_REASON="Locate the vault for the requested deployment credential" \
  pass-cli vault list --output json
PROTON_PASS_AGENT_REASON="Find the token item for the requested deployment" \
  pass-cli item list --vault-name "Vault Name" --output json
```

Pin automation to `share_id` + item `id`. Names can collide, and **trashed items take part in title resolution**: a hidden trashed duplicate silently shadows the active item and keeps serving an old value that no re-login fixes (seen 2026-10-25). Diagnose with `item list <vault> --output json` (`state`, `modify_time`). `--show-secrets` is refused in Agent sessions; don't work around it.

**Run** (references resolve only for the child; output masked; still never have the child print secrets):

```bash
export DEPLOY_TOKEN='pass://SHARE_ID/ITEM_ID/token'
PROTON_PASS_AGENT_REASON="Authenticate the deployment requested by the user" \
  pass-cli run -- ./deploy.sh
# or keep only references in a gitignored env file: DATABASE_PASSWORD=pass://SHARE_ID/ITEM_ID/password
PROTON_PASS_AGENT_REASON="Connect the requested server to its database" \
  pass-cli run --env-file .env.secrets -- ./start-server
```

A TOTP reference resolves to the current code; use `?totp=uri` (the `otpauth://` URI) only when the task requires it, and only to the consumer. A cached snapshot is not a source of current codes.

**Inject** materializes secrets: only when the task needs that file, explicit output path, default `0600`, never stdout, no `--force` without approval for that specific file, never commit the result.

```bash
# template: api_token: '{{ pass://SHARE_ID/ITEM_ID/token }}'
PROTON_PASS_AGENT_REASON="Render the service configuration requested by the user" \
  pass-cli inject --in-file app-config.yaml.template --out-file .runtime/app-config.yaml
```

**TOTP** for an interactive login: use immediately; never log, store or repeat it.

```bash
PROTON_PASS_AGENT_REASON="Complete the interactive login requested by the user" \
  pass-cli item totp --share-id ID --item-id ID
```

## Audit and access

`pass-cli agent monitor "agent-name" --output json` needs the owner's session: ask the owner. Cached reads create no native access record; sources are audited during explicit warm. Never create, renew, delete, grant or revoke Agents/PATs, and never use `pass-keys add`/`drop` for permissions during retrieval. If access is missing, ask the owner for the narrowest expiring viewer access, ideally the single item.
