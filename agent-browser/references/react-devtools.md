# React DevTools and Web Vitals

First-class React introspection. Works on any React app — Next.js, Remix,
Vite+React, CRA, TanStack Start, React Native Web, etc.

Requires the React DevTools hook at launch. Without it, `react …` commands
error. `vitals` and `pushstate` work on any site regardless of framework.

```bash
agent-browser open --enable react-devtools http://localhost:3000
```

## Component tree

```bash
agent-browser react tree                    # full tree (depth id parent name columns)
agent-browser react inspect <fiberId>       # props, hooks, state, source location
```

## Re-render profiling

```bash
agent-browser react renders start           # begin recording re-renders
# ... interact with the app ...
agent-browser react renders stop            # print render profile
agent-browser react renders stop --json     # JSON output
```

## Suspense boundaries

```bash
agent-browser react suspense                # all boundaries + classifier
agent-browser react suspense --only-dynamic # hide "static" list
agent-browser react suspense --json         # JSON output
```

## Core Web Vitals

```bash
agent-browser vitals                        # LCP, CLS, TTFB, FCP, INP
agent-browser vitals http://localhost:3000  # navigate + measure
agent-browser vitals --json                 # JSON output
```

Also includes React hydration timing when a profiling build is detected.

## SPA navigation

```bash
agent-browser pushstate <url>    # client-side nav (auto-detects Next router)
```

Auto-detects `window.next.router.push` (triggers RSC fetch on Next.js),
falls back to `history.pushState` + popstate/navigate events for other
frameworks. Use instead of `open` for in-app navigation that shouldn't
trigger a full page load.
