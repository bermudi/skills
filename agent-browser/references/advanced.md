# Advanced Configuration

Device emulation, proxy setup, CDP connections, extensions, init scripts,
and other flags for non-standard browser tasks.

## Device emulation

```bash
agent-browser set device "iPhone 14"          # emulate a mobile device
agent-browser set viewport 1920 1080          # set viewport size
agent-browser set viewport 1920 1080 2        # 2x retina
agent-browser set geo 37.7749 -122.4194       # set geolocation
agent-browser set offline on                  # toggle offline mode
agent-browser set media dark                  # dark mode
agent-browser set media light reduced-motion  # light + reduced motion
```

## CDP connections

Connect to an already-running Chrome via Chrome DevTools Protocol:

```bash
# Auto-discover any Chrome with remote debugging
agent-browser --auto-connect snapshot -i
agent-browser --auto-connect state save ./auth.json

# Connect to a specific port
agent-browser --cdp 9222 snapshot -i
agent-browser connect 9222                      # one-time attach
```

Use `--auto-connect` when you don't know the port, `--cdp <port>` when you
do. Common for: reusing auth from a user's browser, connecting to
Chrome in Docker, or debugging a CDP-speaking app.

**Security:** `--remote-debugging-port` exposes full browser control on
localhost. Only use on trusted machines.

## Extensions

```bash
# Load one or more Chrome extensions
agent-browser --extension ./uBlock open https://example.com
agent-browser --extension ./ext1 --extension ./ext2 open https://example.com
```

Also via env: `AGENT_BROWSER_EXTENSIONS="/ext1,/ext2"` or in
`agent-browser.json` config. Extensions from user and project configs
are merged (not replaced).

## Init scripts

Run JavaScript before any page loads:

```bash
# At launch
agent-browser open --init-script ./hook.js https://example.com

# At runtime (returns an identifier)
agent-browser addinitscript "window.myFlag = true"
agent-browser removeinitscript <identifier>
```

Also via env: `AGENT_BROWSER_INIT_SCRIPTS="/a.js,/b.js"`.

Use `--enable react-devtools` for the built-in React hook instead of
a custom init script.

## Proxy

```bash
# HTTP proxy
agent-browser --proxy "http://proxy.example.com:8080" open https://example.com

# SOCKS5 with auth
agent-browser --proxy "socks5://user:pass@proxy:1080" open https://example.com

# With bypass list
agent-browser --proxy "http://proxy:8080" \
  --proxy-bypass "localhost,*.internal.com" \
  open https://example.com
```

Env alternatives: `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`.

## Custom browser executable

```bash
agent-browser --executable-path /usr/bin/chromium open https://example.com
# Or via env:
# AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium
```

The `--engine lightpanda` flag uses Lightpanda (a lightweight Go-based
browser) instead of Chrome. No Chrome installation needed.

## HTTP headers

```bash
# Extra headers scoped to the URL's origin
agent-browser --headers '{"Authorization":"Bearer TOKEN"}' open https://api.example.com
# Or at runtime:
agent-browser set headers '{"X-Custom":"value"}'
```

## HTTP Basic Auth

```bash
agent-browser set credentials user pass
agent-browser open https://protected.example.com
```

## Configuration file

agent-browser reads `agent-browser.json` from:

1. `~/.agent-browser/config.json` — user-level defaults
2. `./agent-browser.json` — project-level overrides
3. Environment variables — override config
4. CLI flags — override everything

Example:

```json
{
  "headed": true,
  "proxy": "http://localhost:8080",
  "profile": "./browser-data"
}
```

Boolean flags accept `true`/`false` to override config:
`--headed false` disables `headed: true` from config.
