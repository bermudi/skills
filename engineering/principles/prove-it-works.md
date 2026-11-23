# Prove It Works

**When:** Apply after completing a task, before declaring done. Verify against the real artifact (run the feature, read the actual value, inspect the diff), not a proxy, self-report, or 'it compiles.'

Verify every output by checking the real thing directly: run the feature, read the actual value, inspect the diff. Proxies (file mtimes, self-reports, cached output, "it compiles") do not count. When a check fails, suspect the observation method before the system.

Drive each control by its own real input. A shortcut that shares part of the code path does not prove the button: the button's own handler can be wired wrong while the shortcut works. Click every button, scroll with a real wheel event, and read the effect back as a value after each. List in the report only what was driven this way.

Script the check when you can. A deterministic script that reruns the comparison beats a one-time look. Keep its output where the human can see it, and commit it only when the trail must be auditable later.
