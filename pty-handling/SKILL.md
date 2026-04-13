---
name: pty-handling
description: Pseudo-terminal (PTY) process management for interactive shell applications. Use when (1) spawning PTY sessions for terminal-based apps (e.g., coding agents, interactive CLIs, REPLs), (2) handling shell mode detection and command wrapping for zsh/bash, (3) managing process lifecycle with proper signal propagation, (4) implementing stdin/stdout/stderr streaming for PTY-controlled processes, (5) configuring PTY dimensions and environment isolation, or (6) debugging PTY-related errors like EBADF, ENOENT, or zombie processes.
---

# PTY Handling

PTY-based process management for interactive terminal applications.

## Core Concepts

A pseudo-terminal (PTY) creates a simulated terminal for processes that expect a terminal environment. Unlike plain child processes, PTY sessions:

- Merge stdout/stderr into a unified output stream
- Support ANSI escape codes and terminal features (cursor movement, colors)
- Enable interactive input (not just pipe-based)
- Are required for TUI applications and coding agents

## Spawning a PTY Process

### With node-pty (Node.js)

```typescript
import * as pty from "node-pty";
import os from "node:os";

const shell = os.platform() === "win32" ? "pwsh" : process.env.SHELL || "bash";

const ptyProcess = pty.spawn(shell, ["-c", command], {
  name: process.env.TERM || "xterm-256color",
  cols: 120,
  rows: 30,
  cwd: workingDir,
  env: envVars,
});

ptyProcess.onData((data) => {
  process.stdout.write(data);
});

ptyProcess.onExit(({ exitCode, signal }) => {
  console.log(`Exited: ${exitCode}, signal: ${signal}`);
});
```

### With Python (pyte + pty)

```python
import pty
import os
import sys

def spawn_pty(command):
    pid, fd = pty.fork()
    if pid == 0:
        # Child
        os.execvp(command, [command])
    else:
        # Parent
        import termios
        import struct
        import fcntl
        
        # Set terminal size
        winsize = struct.pack('HHHH', rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
        
        # Read output
        while True:
            try:
                data = os.read(fd, 1024)
                if not data:
                    break
                sys.stdout.write(data.decode())
            except OSError:
                break
```

## Shell Detection

Detect the current shell for proper command formatting:

```typescript
function detectShell(): { name: string; path: string; args: string[] } {
  const platform = process.platform;
  
  if (platform === "win32") {
    return {
      name: "pwsh",
      path: "pwsh",
      args: ["-NoProfile", "-NonInteractive", "-Command"],
    };
  }
  
  const shellPath = process.env.SHELL || "sh";
  const shellName = shellPath.split("/").pop() || "sh";
  
  // Fish shell rejects bashisms; prefer bash for compatibility
  if (shellName === "fish") {
    const bashPath = findExecutable("bash") || findExecutable("sh");
    if (bashPath) {
      return { name: "bash", path: bashPath, args: ["-c"] };
    }
  }
  
  return { name: shellName, path: shellPath, args: ["-c"] };
}

function findExecutable(name: string): string | undefined {
  const pathEnv = process.env.PATH || "";
  for (const dir of pathEnv.split(path.delimiter)) {
    const fullPath = path.join(dir, name);
    try {
      fs.accessSync(fullPath, fs.constants.X_OK);
      return fullPath;
    } catch {}
  }
  return undefined;
}
```

## Shell Wrapping for zsh

zsh glob expansion (`nonomatch`) causes errors with URLs containing `?`, `[]`, `*`:

```typescript
function wrapCommand(command: string, shellName: string): string {
  if (shellName === "zsh") {
    return `setopt nonomatch; ${command}`;
  }
  return command;
}

// Usage
const wrappedCommand = wrapCommand("curl https://example.com?foo=bar", "zsh");
```

## Process Lifecycle Management

### Spawn with Timeout

```typescript
interface PtySession {
  pid: number;
  write: (data: string) => void;
  onData: (callback: (data: string) => void): void;
  onExit: (callback: (event: { exitCode: number; signal?: number }) => void): void;
  resize(cols: number, rows: number): void;
  kill(signal?: string): void;
}

async function spawnWithTimeout(
  command: string,
  options: {
    timeoutMs?: number;
    noOutputTimeoutMs?: number;
    cwd?: string;
    env?: Record<string, string>;
    cols?: number;
    rows?: number;
  } = {}
): Promise<{ exitCode: number | null; signal?: number; timedOut: boolean }> {
  const {
    timeoutMs = 180000,
    noOutputTimeoutMs,
    cwd = process.cwd(),
    env = process.env as Record<string, string>,
    cols = 120,
    rows = 30,
  } = options;
  
  return new Promise((resolve, reject) => {
    const ptyProcess = pty.spawn(process.env.SHELL || "bash", ["-c", command], {
      cwd,
      env,
      cols,
      rows,
    });
    
    let timedOut = false;
    let lastOutputTime = Date.now();
    let outputTimer: NodeJS.Timeout | null = null;
    let mainTimer: NodeJS.Timeout | null = null;
    
    if (noOutputTimeoutMs) {
      outputTimer = setInterval(() => {
        if (Date.now() - lastOutputTime > noOutputTimeoutMs) {
          timedOut = true;
          ptyProcess.kill("SIGKILL");
        }
      }, 1000);
    }
    
    mainTimer = setTimeout(() => {
      timedOut = true;
      ptyProcess.kill("SIGKILL");
    }, timeoutMs);
    
    ptyProcess.onData(() => {
      lastOutputTime = Date.now();
    });
    
    ptyProcess.onExit(({ exitCode, signal }) => {
      if (outputTimer) clearInterval(outputTimer);
      if (mainTimer) clearTimeout(mainTimer);
      resolve({ exitCode, signal, timedOut });
    });
  });
}
```

### Kill Process Tree

```typescript
import { spawn } from "node:child_process";

function killProcessTree(pid: number): void {
  if (process.platform === "win32") {
    spawn("taskkill", ["/F", "/T", "/PID", String(pid)], {
      stdio: "ignore",
      detached: true,
    });
  } else {
    try {
      // Kill entire process group
      process.kill(-pid, "SIGKILL");
    } catch {
      try {
        process.kill(pid, "SIGKILL");
      } catch {
        // Process already dead
      }
    }
  }
}
```

## PTY Dimensions

Set appropriate dimensions based on use case:

| Use Case | cols | rows |
|----------|------|------|
| Default / CI | 120 | 30 |
| Wide output (logs) | 200 | 50 |
| Narrow (mobile/small) | 80 | 24 |
| Full-screen app | 120 | 40 |

```typescript
ptyProcess.resize(200, 50); // Dynamically resize
```

## Common Errors

### EBADF: Bad file descriptor

**Cause**: File descriptor leaked or closed prematurely. Common when stdin/stdout/stderr handles are mishandled, or when running as a service/daemon where stdin is closed.

**Fix**:
```typescript
// Bad: stdin may be closed in daemon context
spawn("bash", ["-c", cmd], { stdio: "inherit" });

// Good: explicitly configure stdio
spawn("bash", ["-c", cmd], {
  stdio: ["ignore", "pipe", "pipe"]  // explicit, works in daemons
});
```

For node-pty, ensure proper cleanup:
```typescript
const pty = pty.spawn(...);
// Always dispose on exit
pty.onExit(() => pty.dispose());
// Or use cleanup wrapper
process.on("exit", () => pty.kill());
```

### ENOENT: Command not found

**Cause**: Shell executable not found, or command doesn't exist in PATH.

**Fix**:
```typescript
// Verify shell exists before spawning
const shellPath = process.env.SHELL;
if (!fs.existsSync(shellPath)) {
  throw new Error(`Shell not found: ${shellPath}`);
}

// Use absolute path for commands
const absCmd = path.resolve(cmd);
```

### PTY not available

**Cause**: node-pty native module not compiled for current platform/architecture.

**Fix**:
```typescript
// Check availability before use
let pty;
try {
  pty = require("node-pty");
} catch (e) {
  // Fallback to script-based PTY or child_process
  console.warn("node-pty unavailable, using fallback");
}

// Or pre-check with platform validation
const supported = process.platform !== "win32" || process.arch === "x64";
```

### Zombie processes

**Cause**: Child processes not properly reaped after exit, or parent crashed before killing children.

**Fix**:
```typescript
// Always handle exit events
pty.onExit(({ exitCode }) => {
  cleanup();
  process.exit(exitCode || 0);
});

// Or use process supervision
const supervisor = createProcessSupervisor();
const run = await supervisor.spawn({ /* ... */ });

// Ensure cancellation propagates
process.on("SIGINT", () => run.cancel("signal"));
process.on("SIGTERM", () => run.cancel("signal"));
```

### EOF not sent / Process hangs

**Cause**: PTY EOF differs by platform. On Unix, `\x04` (Ctrl+D) closes input. On Windows, `\x1a` is needed.

**Fix**:
```typescript
function sendEof(pty: PtySession): void {
  const eof = process.platform === "win32" ? "\x1a" : "\x04";
  pty.write(eof);
}

// Or properly close by ending the channel
ptyProcess.kill(); // Let the process handle SIGKILL as EOF
```

### Shell glob expansion errors (zsh)

**Cause**: zsh `nonomatch` option causes `no matches found` errors for URLs with `?`, `[]`.

**Error**: `zsh: no matches found: https://example.com?query=value`

**Fix**: Wrap commands with `setopt nonomatch`:
```typescript
if (shellName === "zsh") {
  command = `setopt nonomatch; ${command}`;
}
```

### No output timeout not firing

**Cause**: Output detection interval too coarse, or output is being buffered.

**Fix**:
```typescript
// Use shorter polling interval
const checkInterval = setInterval(() => {
  if (Date.now() - lastOutput > noOutputTimeoutMs) {
    pty.kill("SIGKILL");
  }
}, 500); // Check every 500ms, not every second

// Ensure no buffering
ptyProcess.setEncoding("utf8");
```

### Signal handling inconsistencies

**Cause**: Different signals behave differently across platforms. SIGTERM may be ignored by some processes.

**Fix**:
```typescript
// Use SIGKILL for guaranteed termination (but can't be caught)
pty.kill("SIGKILL");

// For graceful shutdown, send SIGTERM then wait
pty.kill("SIGTERM");
setTimeout(() => {
  if (!exited) pty.kill("SIGKILL");
}, 5000);
```

## Service/Detached Mode

When running as a service (systemd, launchd), processes may not detach properly:

```typescript
function isServiceContext(): boolean {
  return Boolean(process.env.SERVICE_MARKER || process.env.GATEWAY_MODE);
}

// In service context, avoid detached mode
const detached = process.platform !== "win32" && !isServiceContext();

spawn(cmd, args, {
  detached,
  stdio: detached ? "pipe" : "ignore",
});
```

## Reference: Common Patterns

### Interactive REPL

```typescript
const pty = pty.spawn("node", ["-i"], { cols: 120, rows: 30 });

pty.onData((d) => process.stdout.write(d));

// Send input
pty.write("1 + 1\n");
pty.write(".exit\n");
```

### Long-running with progress

```typescript
const run = spawnWithTimeout("npm install", {
  timeoutMs: 300000,
  noOutputTimeoutMs: 60000,
});

run.output.on("data", (chunk) => {
  process.stdout.write(chunk);
  progress.update(chunk); // Update progress bar
});

const result = await run.exit;
console.log(`Done in ${result.durationMs}ms`);
```

### Interactive CLI (Claude Code, Codex)

```typescript
const agent = spawnWithTimeout("claude", ["--dangerously-skip-permissions"], {
  cols: 180,
  rows: 40,
  cwd: projectDir,
  env: { ...process.env, TERM: "xterm-256color" },
});

agent.output.on("data", renderTUI);

agent.input.write("Help me refactor this function\n");
agent.input.write("Use better naming\n");
agent.input.write("/y\n"); // Confirm
```
