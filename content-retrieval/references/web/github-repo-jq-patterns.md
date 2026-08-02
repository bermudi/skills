# jq Patterns for `gh repo read-dir`

`read-dir --json` wraps entries under `.entries[]` — drill into that first, then
filter and project. These patterns cover the common cases.

## Just the subdirectory names

```bash
gh repo read-dir --repo cli/cli --json name,type \
  --jq '.entries[] | select(.type=="dir") | .name'
```

## Files with sizes, sorted descending

```bash
gh repo read-dir docs --repo cli/cli --json name,type,size \
  --jq '.entries[] | select(.type=="file") | "\(.size)\t\(.name)"'
```

## Anything executable

`modeOctal` is a **string**, not a number — quote the comparison:

```bash
gh repo read-dir script --repo cli/cli --json name,modeOctal \
  --jq '.entries[] | select(.modeOctal=="100755") | .name'
```

## Gotchas

- **`.entries[]` wrapper is required.** A bare `--jq '.[]'` returns nothing.
- **`mode` vs `modeOctal` are different types.** `mode` is a decimal integer
  (`33188`); `modeOctal` is a string (`"100644"`). Compare `modeOctal` with a
  string literal: `select(.modeOctal=="100755")`, not `==100755`.
