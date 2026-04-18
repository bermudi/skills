---
name: child-process-supervisor
description: >
  ⚠️ WORK IN PROGRESS, DO NOT USE BEFORE FIXING.


  How to design and implement a child process supervisor for an agent runtime.
  Use this skill whenever you need to:
  - Design a system for spawning and managing child processes
  - Implement timeout handling for long-running or hung processes
  - Build PTY support for interactive shell sessions
  - Handle cross-platform process lifecycle (Unix/Windows)
  - Implement graceful shutdown and process tree termination
  - Design environment isolation for sandboxed execution
  - Map exit codes and signals to meaningful termination reasons

  This skill captures the architectural decisions, patterns, and edge cases
  discovered through building a production child process supervisor. It teaches
  HOW to think about these problems, not just what one specific implementation does.
---

# Child Process Supervisor

This skill teaches how to design and implement a child process supervisor for an
agent runtime. It captures the decisions, patterns, and gotchas you'll encounter
building something like ProcessSupervisor — a system that safely spawns, manages,
times out, and terminates external processes.

## Core Architecture

### The Problem You're Solving

Agent runtimes need to execute external commands: build scripts, REPLs, interactive
shells, long-running servers. You need to:
- Spawn processes with controlled environments
- Capture their output
- Enforce timeouts
- Handle crashes and hangs
- Terminate entire process trees (not just the immediate child)
- Support both interactive (PTY) and non-interactive modes

### Adapter Pattern for Spawn Modes

Use a **discriminated union** to separate non-interactive and interactive modes:

```typescript
type SpawnChildInput = {
  mode: "child";
  argv: string[];
  cwd?: string;
  env?: Record<string, string | undefined>;
  timeoutMs?: number;
  noOutputTimeoutMs?: number;
  stdinMode?: "inherit" | "pipe-open" | "pipe-closed";
  windowsVerbatimArguments?: boolean;
};

type SpawnPtyInput = {
  mode: "pty";
  ptyCommand: string;
  cwd?: string;
  env?: Record<string, string | undefined>;
  timeoutMs?: number;
  noOutputTimeoutMs?: number;
  cols?: number;
  rows?: number;
};

type SpawnInput = SpawnChildInput | SpawnPtyInput;
```

**Why discriminated union?** These modes have completely different requirements:
- `child` mode needs `argv`, `stdinMode`, `windowsVerbatimArguments`
- `pty` mode needs `ptyCommand`, `cols`, `rows`

Mixing these into one object leads to type pollution and confusion about what's
actually being used at runtime.

### When to Use Each Mode

| Mode | Use Case | Stdin Behavior |
|------|----------|----------------|
| `child` | Non-interactive commands, scripts, pipelines | Configurable |
| `pty` | Interactive shells, terminal-based tools, REPLs | EOF differs by platform |

**Rule of thumb:** If the user wants an interactive session or needs PTY features
(colors, line editing, window resize), use `pty`. Otherwise, use `child`.

---

## Timeout Semantics

Two independent timeout mechanisms serve different purposes:

### `timeoutMs` — Hard Kill After N ms

Kills the process after the absolute elapsed time. Use for operations that should
eventually be abandoned regardless of their progress.

```typescript
if (timeoutMs) {
  timeoutTimer = setTimeout(() => {
    requestCancel("overall-timeout");
  }, timeoutMs);
}
```

### `noOutputTimeoutMs` — Kill If Silent For N ms

Kills the process if no stdout/stderr output for the specified duration. Use for
detecting hung processes or infinite loops that produce no logging.

```typescript
const touchOutput = () => {
  if (!noOutputTimeoutMs || settled) return;
  if (noOutputTimer) clearTimeout(noOutputTimer);
  noOutputTimer = setTimeout(() => {
    requestCancel("no-output-timeout");
  }, noOutputTimeoutMs);
};

adapter.onStdout((chunk) => {
  // ... handle chunk ...
  touchOutput();  // Reset on ANY output
});
```

### How They Interact

**Key insight:** Both can be set simultaneously but operate independently:
- A noisy process survives `noOutputTimeoutMs` but dies at `timeoutMs`
- A silent process dies at `noOutputTimeoutMs` even if `timeoutMs` is much larger

### Timeout Validation

```typescript
function clampTimeout(value?: number): number | undefined {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    return undefined;
  }
  return Math.max(1, Math.floor(value));
}
```

Timeouts must be positive integers. Zero, negative, NaN, and Infinity are all
treated as "no timeout." Always validate at the boundary.

---

## Process Tree Termination

**Critical rule:** `child.kill()` only kills the immediate process. Child processes
and their descendants survive. You must kill the entire process tree.

### Unix: Signal the Process Group

On Unix, child processes inherit the parent's process group when spawned detached.
Use `kill(-pid, signal)` to signal the entire group:

```typescript
function killProcessTreeUnix(pid: number, graceMs: number): void {
  // Step 1: Graceful SIGTERM to process group
  try {
    process.kill(-pid, "SIGTERM");  // Negative pid = process group
  } catch {
    // Fall back to direct pid
    try {
      process.kill(pid, "SIGTERM");
    } catch {
      return;
    }
  }

  // Step 2: Wait grace period, then SIGKILL if still alive
  setTimeout(() => {
    if (isProcessAlive(-pid)) {
      process.kill(-pid, "SIGKILL");
      return;
    }
    if (!isProcessAlive(pid)) return;
    process.kill(pid, "SIGKILL");
  }, graceMs).unref();
}

function isProcessAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}
```

### Windows: taskkill with /T Flag

Windows `taskkill /T` includes child processes automatically:

```typescript
function runTaskkill(args: string[]): void {
  spawn("taskkill", args, {
    stdio: "ignore",
    detached: true,
    windowsHide: true,
  });
}

function killProcessTreeWindows(pid: number, graceMs: number): void {
  // Graceful first
  runTaskkill(["/T", "/PID", String(pid)]);

  // Force kill only if still alive after grace period
  setTimeout(() => {
    if (!isProcessAlive(pid)) return;
    runTaskkill(["/F", "/T", "/PID", String(pid)]);
  }, graceMs).unref();
}
```

### Grace Period Design

```typescript
const DEFAULT_GRACE_MS = 3000;
const MAX_GRACE_MS = 60_000;
```

Default 3 seconds lets processes:
- Flush output buffers
- Close connections
- Remove temp files
- Terminate their own children

Max 60 seconds prevents waiting forever on truly stuck processes.

---

## Output Handling

### Dual Path: Streaming + Retention

Output should flow through two paths simultaneously:

```typescript
let stdout = "";
let stderr = "";
const captureOutput = input.captureOutput !== false;

adapter.onStdout((chunk) => {
  if (captureOutput) {
    stdout += chunk;  // Accumulate for final result
  }
  input.onStdout?.(chunk);  // Stream to caller in real-time
  touchOutput();  // Reset noOutputTimeoutMs
});
```

**Why this design?**
- Accumulated strings give you complete output in `RunExit`
- Callback streaming lets callers implement progress indicators, live logs, etc.

### Output Buffer Type

```typescript
type RunExit = {
  reason: TerminationReason;
  exitCode: number | null;
  exitSignal: NodeJS.Signals | number | null;
  durationMs: number;
  stdout: string;
  stderr: string;
  timedOut: boolean;
  noOutputTimedOut: boolean;
};
```

Collect stdout and stderr as strings. Binary output should be base64-encoded if needed.

---

## Platform Edge Cases

### Windows EOF: Different Bytes

PTY EOF differs by platform:

```typescript
const eof = process.platform === "win32" ? "\x1a" : "\x04";
pty.write(eof);
```

| Platform | EOF Character | Notes |
|----------|--------------|-------|
| Unix | `\x04` (Ctrl+D) | Standard POSIX |
| Windows | `\x1a` (Ctrl+Z) | CP/M legacy |

**Why:** Windows console handles EOF differently. `\x1a` is the traditional CP/M
and DOS EOF character, still recognized by Windows command shells.

### Windows `.bat`/`.cmd` Spawning

Node.js 18.20.2+ (CVE-2024-27980) rejects spawning `.cmd`/`.bat` files directly:

```typescript
function isWindowsBatchCommand(command: string): boolean {
  const ext = path.extname(command).toLowerCase();
  return ext === ".cmd" || ext === ".bat";
}

// Wrap batch files with cmd.exe
if (isWindowsBatchCommand(command)) {
  spawn("cmd.exe", ["/d", "/s", "/c", command, ...args]);
}
```

### npm/npx on Windows

Windows npm/npx are `.cmd` files that cause `EINVAL` when spawned directly:

```typescript
function resolveNpmArgvForWindows(argv: string[]): string[] | null {
  const basename = path.basename(argv[0]).toLowerCase();
  if (!["npm", "npx"].includes(basename)) return null;

  const nodeDir = path.dirname(process.execPath);
  const cliName = basename === "npx" ? "npx-cli.js" : "npm-cli.js";
  const cliPath = path.join(nodeDir, "node_modules", "npm", "bin", cliName);

  if (fs.existsSync(cliPath)) {
    return [process.execPath, cliPath, ...argv.slice(1)];
  }
  return null;
}
```

**Alternative:** Fall back to spawning the `.cmd` directly — it works on unpatched
Node versions and in environments without the npm cli scripts.

### Service-Managed Runtimes

When running under systemd/launchd, detached processes break tree termination:

```typescript
function isServiceManagedRuntime(): boolean {
  return Boolean(process.env.OPENCLAW_SERVICE_MARKER?.trim());
}

// In service mode, don't detach so the service manager can stop the full tree
const useDetached = process.platform !== "win32" && !isServiceManagedRuntime();
```

**Why it matters:** Detached processes don't belong to the parent's process group,
so `kill(-pid)` won't reach them.

### `windowsVerbatimArguments`

When `true`, Node.js passes arguments without parsing/quoting:

```typescript
const options: SpawnOptions = {
  // ...
  windowsVerbatimArguments: params.windowsVerbatimArguments,
};
```

Use when spawning through `cmd.exe /c` or when you need exact argument preservation.

---

## Environment Isolation

### What's Included in Child Env

```typescript
function toStringEnv(env?: Record<string, string | undefined>): Record<string, string> {
  if (!env) return {};
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(env)) {
    if (value === undefined) continue;  // undefined = excluded, not stringified
    out[key] = String(value);
  }
  return out;
}
```

**Key decision:** `undefined` values are dropped, not converted to strings. This
lets you explicitly control which environment variables the child sees.

### Inheritance Model

Choose one:

1. **Full inheritance** (pass nothing): Child gets entire `process.env`
2. **Partial isolation** (pass subset): Child gets base env + your overrides
3. **Full isolation** (pass empty): Child gets only what you provide

```typescript
function resolveCommandEnv(
  inputEnv?: Record<string, string | undefined>,
  baseEnv = process.env
): Record<string, string> {
  const merged = inputEnv ? { ...baseEnv, ...inputEnv } : { ...baseEnv };
  return Object.fromEntries(
    Object.entries(merged).filter(([, v]) => v !== undefined)
  );
}
```

### Interactive Prompt Suppression

For automated environments, suppress interactive prompts:

```typescript
function suppressNpmFund(env: Record<string, string>): void {
  const cmd = path.basename(argv[0] ?? "");
  if (cmd === "npm" || cmd === "npm.cmd" || cmd === "npm.exe" ||
      (cmd === "node" && argv.includes("npm-cli.js"))) {
    env.NPM_CONFIG_FUND = "false";
    env.npm_config_fund = "false";
  }
}
```

---

## Error Code Mapping

### Termination Reasons

```typescript
type TerminationReason =
  | "manual-cancel"    // User called cancel()
  | "overall-timeout"  // Exceeded timeoutMs
  | "no-output-timeout" // Silent for too long
  | "spawn-error"      // Failed to spawn
  | "signal"           // Killed by signal
  | "exit";            // Normal exit
```

### Exit Code Normalization

| Condition | reason | exitCode | Notes |
|-----------|--------|----------|-------|
| Normal exit | `"exit"` | 0-255 | |
| Signal killed | `"signal"` | `null` | `exitSignal` populated |
| Overall timeout | `"overall-timeout"` | 0-255 or `null` | |
| No-output timeout | `"no-output-timeout"` | 0-255 or `null` | |
| Spawn error | `"spawn-error"` | `null` | |
| Manual cancel | `"manual-cancel"` | `null` | |

### Timeout Exit Code Convention

```typescript
const normalizedCode =
  termination === "timeout" || termination === "no-output-timeout"
    ? code === 0 ? 124 : code  // 124 = standard timeout exit
    : code;
```

If a process times out and exits 0, normalize to **124** (standard convention,
same as GNU `timeout`).

### Common Error Codes

| Code | Meaning | What to Do |
|------|---------|------------|
| `ENOENT` | Command not found | Check `argv[0]`, PATH |
| `EACCES` | Permission denied | Check file permissions |
| `EBADF` | Bad file descriptor | Retry with `detached: false` |
| `EINVAL` | Invalid argument | Check Windows `.cmd` handling |
| `124` | Timeout | Process exceeded time limit |

---

## Spawn with Fallback

Detached spawn can fail on Unix with `EBADF` (file descriptor exhaustion).
Implement fallback:

```typescript
async function spawnWithFallback(
  argv: string[],
  options: SpawnOptions,
): Promise<{ child: ChildProcess; usedFallback: boolean }> {
  try {
    return { child: spawn(argv[0], argv.slice(1), options), usedFallback: false };
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code !== "EBADF") throw err;
    // Fall back to non-detached
    return { child: spawn(argv[0], argv.slice(1), { ...options, detached: false }), usedFallback: true };
  }
}
```

---

## PTY Zombie Prevention

PTYs can become zombies if the underlying process doesn't exit after being killed.
Use a force-kill fallback timer:

```typescript
const FORCE_KILL_WAIT_FALLBACK_MS = 4000;

function kill(signal: string = "SIGKILL"): void {
  pty.kill(signal);

  if (signal === "SIGKILL") {
    setTimeout(() => {
      settleWait({ code: null, signal });  // Resolve wait even if PTY didn't exit
    }, FORCE_KILL_WAIT_FALLBACK_MS).unref();
  }
}
```

Wait 4 seconds, then resolve the wait promise even if PTY hasn't emitted `onExit`.
This prevents callers from hanging forever on zombie PTYs.

---

## Adapter Interface

Define a common interface for both modes:

```typescript
interface SpawnProcessAdapter {
  pid?: number;
  stdin?: {
    write(data: string, cb?: (err?: Error | null) => void): void;
    end(): void;
    destroy?(): void;
    destroyed?: boolean;
  };
  onStdout(listener: (chunk: string) => void): void;
  onStderr(listener: (chunk: string) => void): void;
  wait(): Promise<{ code: number | null; signal: string | null }>;
  kill(signal?: string): void;
  dispose(): void;
}
```

This lets the supervisor work with either adapter without knowing which mode
was chosen.

---

## Common Implementation Patterns

### Pattern: ManagedRun

```typescript
type ManagedRun = {
  runId: string;
  pid?: number;
  startedAtMs: number;
  stdin?: { write, end, destroy, destroyed };
  wait(): Promise<RunExit>;
  cancel(reason?: TerminationReason): void;
};
```

### Pattern: Spawn with Lifecycle

```typescript
async function spawn(input: SpawnInput): Promise<ManagedRun> {
  const runId = crypto.randomUUID();
  const startedAtMs = Date.now();

  // 1. Validate input
  if (input.mode === "child" && input.argv.length === 0) {
    throw new Error("argv cannot be empty");
  }

  // 2. Create adapter (child or pty)
  const adapter = input.mode === "pty"
    ? await createPtyAdapter(...)
    : await createChildAdapter(...);

  // 3. Set up timeout timers
  // 4. Attach output listeners
  // 5. Return ManagedRun with wait() and cancel()

  return {
    runId,
    pid: adapter.pid,
    startedAtMs,
    stdin: adapter.stdin,
    wait: async () => {
      const result = await adapter.wait();
      adapter.dispose();
      return buildRunExit(result, startedAtMs);
    },
    cancel(reason = "manual-cancel") {
      adapter.kill("SIGKILL");
    },
  };
}
```

### Pattern: Graceful Shutdown

```typescript
function shutdown(signal: NodeJS.Signals): void {
  setForcedReason("signal");

  // SIGTERM to process group first
  if (process.platform === "win32") {
    spawn("taskkill", ["/T", "/PID", String(pid)]);
  } else {
    process.kill(-pid, "SIGTERM");
  }

  // Force kill after grace period
  setTimeout(() => {
    if (process.platform === "win32") {
      spawn("taskkill", ["/F", "/T", "/PID", String(pid)]);
    } else {
      process.kill(-pid, "SIGKILL");
    }
  }, DEFAULT_GRACE_MS).unref();
}
```

---

## Design Checklist

Before shipping a child process supervisor:

**Architecture**
- [ ] Discriminated union for spawn modes (child vs pty)?
- [ ] Common adapter interface that works for both modes?
- [ ] ProcessSupervisor singleton managing active runs?

**Timeouts**
- [ ] `timeoutMs` for absolute time limits?
- [ ] `noOutputTimeoutMs` for detecting silent hangs?
- [ ] Both timers operating independently?
- [ ] `clampTimeout()` validation at boundaries?

**Process Tree**
- [ ] Unix: `kill(-pid, SIGTERM)` to process group?
- [ ] Windows: `taskkill /T` to include children?
- [ ] Grace period before force kill?
- [ ] Force kill fallback after grace period?

**Output**
- [ ] Dual path: accumulated + streaming callbacks?
- [ ] `captureOutput` flag to control retention?
- [ ] `touchOutput()` resets noOutputTimeoutMs on any output?

**Platform**
- [ ] Windows EOF: `\x1a` vs Unix `\x04`?
- [ ] `.bat`/`.cmd` files wrapped with `cmd.exe /c`?
- [ ] npm/npx Windows shim to avoid EINVAL?
- [ ] Service-managed mode detection?

**Environment**
- [ ] `undefined` values dropped from env?
- [ ] Inheritance model documented and consistent?
- [ ] Interactive prompts suppressed for automation?

**Error Handling**
- [ ] All termination reasons mapped to exit codes?
- [ ] Timeout exit code normalized to 124?
- [ ] Signal 0 treated as "no signal"?
- [ ] EBADF fallback for detached spawn?

**PTY**
- [ ] Force-kill fallback timer to prevent zombie PTYs?
- [ ] PTY dimensions (cols/rows) configurable?
