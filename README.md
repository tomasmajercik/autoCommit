# autocommit

A small terminal tool that writes your git commit message for you.

It reads your staged changes (`git diff --staged`), asks Claude Haiku for a short one-line message in
[Simplified Technical English](https://www.asd-ste100.org/), and commits after you confirm.

```
$ autocommit
• Repository: /home/you/projects/calc
• Branch: main
! No files are staged. Changed files:
     M calc.py
    ?? README.md
? Select an action: Add all files (git add -A)
• All files are staged.

  Add sub function to calc.py and create README

? Commit with this message?  (↑/↓, enter)
❯ Commit
  Edit
  Regenerate
  Cancel
```

## Requirements

You need these 3 things before you install:

| Tool | Check | Install |
|------|-------|---------|
| git | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| Python 3.8+ | `python3 --version` | [python.org](https://www.python.org/downloads/) (macOS and most Linux distributions have it) |
| Claude Code | `claude --version` | `curl -fsSL https://claude.ai/install.sh \| bash` |

After you install Claude Code, run `claude` one time and log in. autocommit uses your Claude account.

## Install

### macOS / Linux

```sh
curl -fsSL https://raw.githubusercontent.com/tomasmajercik/autoCommit/main/install.sh | sh
```

### Windows

Open **Git Bash** (it comes with [Git for Windows](https://git-scm.com/download/win)) and run the same command.
PowerShell and CMD are not supported by the installer.

The installer copies one file to `~/.local/bin/autocommit`. If that folder is not in your `PATH`,
the installer tells you the line to add to your shell config (`~/.bashrc` or `~/.zshrc`).
Restart the terminal after that.

## Usage

In any folder of a git repository:

```sh
autocommit
```

1. It finds the repository root, also from a subfolder.
2. If no files are staged, it asks you to stage all files (`git add -A`) or exit.
   To commit only some files, exit and run `git add <files>` first.
3. It generates a commit message.
4. You select:
   - **Commit** – runs `git commit` with the message
   - **Edit** – change the message yourself
   - **Regenerate** – ask Claude for a new message
   - **Cancel** – stop; your staged files stay staged

Keys: `↑`/`↓` (or `j`/`k`, or number keys) to move, `Enter` to select, `q` or `Esc` to exit.

It also warns you about detached HEAD, a merge or rebase in progress, and very large diffs
(only the first 40,000 characters are sent).

### Use a different model

```sh
AUTOCOMMIT_MODEL=sonnet autocommit
```

## Update

Run the install command again.

## Uninstall

```sh
rm ~/.local/bin/autocommit
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `autocommit: command not found` | `~/.local/bin` is not in your `PATH`. Add `export PATH="$HOME/.local/bin:$PATH"` to `~/.bashrc` or `~/.zshrc` and restart the terminal. |
| `Claude Code CLI is not installed` | Install Claude Code (see Requirements). |
| `Claude returned an error` | Run `claude` one time and log in. |
| `Python 3.8+ is necessary` | Install Python 3. On Windows, select "Add Python to PATH" in the installer. |
| `curl: (22)` or `(56) ... 404` during install | Check your internet connection and try again in a few minutes. |
| The menu does not react to arrow keys (Windows) | Use Windows Terminal with Git Bash, or type the option number. |

## Privacy

Your staged diff is sent to Anthropic through your Claude Code account. Do not use it on code that you are not allowed to share.
