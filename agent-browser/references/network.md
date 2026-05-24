# Network Interception

Mock, block, inspect, and record network requests during browser automation.

## Mock responses

```bash
agent-browser network route "**/api/users" --body '{"users":[]}'   # stub JSON
agent-browser network route "**/config" --body '{"env":"test"}'    # stub config
```

## Block requests

```bash
agent-browser network route "**/analytics" --abort                 # block entirely
agent-browser network route "*" --abort --resource-type script    # block scripts only
agent-browser network route "*" --resource-type image,font --body ''  # stub images+fonts
```

The `--resource-type` flag accepts comma-separated types: `document`,
`stylesheet`, `image`, `media`, `font`, `script`, `texttrack`, `xhr`,
`fetch`, `eventsource`, `websocket`, `manifest`, `other`.

## Inspect traffic

```bash
agent-browser network requests                  # all tracked requests
agent-browser network requests --filter api     # filter by URL pattern
agent-browser network requests --clear          # clear the log
```

## Record HAR

```bash
agent-browser network har start                 # start recording
# ... perform actions ...
agent-browser network har stop /tmp/trace.har   # save HAR file
```

HAR files capture every request and response body, including auth headers
and bearer tokens. Don't share without redaction.

## Pre-navigation interception

To intercept requests that fire on the very first page load, use `open`
without a URL to get a clean browser, set up routes, then navigate:

```bash
agent-browser batch \
  '["open"]' \
  '["network","route","*","--abort","--resource-type","script"]' \
  '["navigate","http://localhost:3000/target"]'
```

This blocks scripts on the initial HTML request — useful for SSR-only
debugging or capturing fresh render state without client-side noise.

## Remove routes

```bash
agent-browser network unroute              # remove all routes
agent-browser network unroute "**/api/*"   # remove specific route
```
