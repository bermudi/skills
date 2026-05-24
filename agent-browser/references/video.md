# Video Recording

Capture browser automation as WebM video for debugging, documentation, or
CI evidence.

## Basic recording

```bash
agent-browser record start demo.webm
# ... perform actions ...
agent-browser record stop
```

## Commands

```bash
agent-browser record start ./output.webm      # start recording to file
agent-browser record stop                      # stop and save
agent-browser record restart ./take2.webm      # stop current + start new
```

## Best practices

Add short pauses between actions so the video is watchable:

```bash
agent-browser record start login-flow.webm
agent-browser open https://app.example.com/login
agent-browser wait 500                         # pause for visibility

agent-browser snapshot -i
agent-browser fill @e1 "demo@example.com"
agent-browser wait 300

agent-browser fill @e2 "password"
agent-browser wait 300

agent-browser click @e3
agent-browser wait --load networkidle
agent-browser wait 1000                        # show result

agent-browser record stop
```

Combine with screenshots for key frames:

```bash
agent-browser record start flow.webm
agent-browser open https://example.com
agent-browser screenshot ./screenshots/step1.png
agent-browser click @e1
agent-browser screenshot ./screenshots/step2.png
agent-browser record stop
```

## Error handling

Always stop recording in cleanup, even on failure:

```bash
cleanup() {
    agent-browser record stop 2>/dev/null || true
    agent-browser close 2>/dev/null || true
}
trap cleanup EXIT

agent-browser record start ./automation.webm
# ... automation steps ...
```

## Output format

- WebM (VP8/VP9 codec)
- Compatible with all modern browsers and video players
- Compressed but high quality
- Recording adds slight overhead to automation
