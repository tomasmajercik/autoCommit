# autocommit

Generate a one-line commit message from the staged diff with Claude Haiku, then commit.

## Install

Requires: `git`, Python 3.8+, and [Claude Code](https://claude.ai/code) (logged in).

```sh
curl -fsSL https://raw.githubusercontent.com/tomasmajercik/autoCommit/main/install.sh | sh
```

Windows: run it in Git Bash.

## Use

```sh
autocommit
```

1. Finds the repo root from any subfolder.
2. If nothing is staged: asks to run `git add -A` or exit.
3. Generates a short message (ASD-STE100).
4. Menu: Commit / Edit / Regenerate / Cancel.

Use another model: `AUTOCOMMIT_MODEL=sonnet autocommit`

## Uninstall

```sh
rm ~/.local/bin/autocommit
```
