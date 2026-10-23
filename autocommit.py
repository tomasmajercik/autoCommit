#!/usr/bin/env python3
"""autocommit - generate a short commit message from the staged diff with Claude."""

import os
import shutil
import subprocess
import sys
import threading
import time

VERSION = "0.1.0"
MODEL = os.environ.get("AUTOCOMMIT_MODEL", "haiku")
MAX_DIFF_CHARS = 40000

PROMPT = (
    "Write a git commit message for the staged diff on stdin. "
    "Use Simplified Technical English (ASD-STE100). "
    "Rules: one line only, max 72 characters, start with an imperative verb, "
    "keywords are OK, no period at the end, no quotes, no prefix, no explanation. "
    "Output only the message."
)

if os.name == "nt":
    os.system("")  # enable ANSI escape codes in the Windows console

UTF8 = (sys.stdout.encoding or "").lower().replace("-", "") == "utf8"
POINTER = "❯" if UTF8 else ">"
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏" if UTF8 else "|/-\\"


def c(code, text):
    return f"\x1b[{code}m{text}\x1b[0m" if sys.stdout.isatty() else text


def info(msg):
    print(c("36", "• ") + msg)


def warn(msg):
    print(c("33", "! ") + msg)


def die(msg, hint=None):
    print(c("31", "✗ " if UTF8 else "x ") + msg)
    if hint:
        print("  " + c("2", hint))
    sys.exit(1)


def git(*args, check=True):
    r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        die(f"git {' '.join(args)} failed.", r.stderr.strip())
    return r


# ---------- terminal UI ----------

def read_key():
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "")
    else:
        import select
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = os.read(fd, 1).decode(errors="ignore")
            if ch == "\x1b" and select.select([fd], [], [], 0.05)[0]:
                seq = os.read(fd, 2).decode(errors="ignore")
                return {"[A": "up", "[B": "down", "OA": "up", "OB": "down"}.get(seq, "")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    if ch == "\x03":
        raise KeyboardInterrupt
    if ch in ("\r", "\n"):
        return "enter"
    if ch in ("\x1b", "q"):
        return "quit"
    return {"k": "up", "j": "down"}.get(ch, ch)


def select(question, options):
    """Arrow-key menu. Returns the index of the selected option, or None on quit."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return select_plain(question, options)

    idx = 0
    out = sys.stdout
    out.write("\x1b[?25l")  # hide cursor
    try:
        first = True
        while True:
            if not first:
                out.write(f"\x1b[{len(options) + 1}A\x1b[J")
            first = False
            out.write(c("32", "? ") + c("1", question) + c("2", "  (↑/↓, enter)" if UTF8 else "  (up/down, enter)") + "\n")
            for i, opt in enumerate(options):
                out.write((c("36", f"{POINTER} {opt}") if i == idx else f"  {opt}") + "\n")
            out.flush()

            key = read_key()
            if key == "up":
                idx = (idx - 1) % len(options)
            elif key == "down":
                idx = (idx + 1) % len(options)
            elif key.isdigit() and 1 <= int(key) <= len(options):
                idx = int(key) - 1
                key = "enter"
            if key in ("enter", "quit"):
                out.write(f"\x1b[{len(options) + 1}A\x1b[J")
                answer = options[idx] if key == "enter" else "Exit"
                out.write(c("32", "? ") + c("1", question) + " " + c("36", answer) + "\n")
                return idx if key == "enter" else None
    except OSError:
        return select_plain(question, options)
    finally:
        out.write("\x1b[?25h")  # show cursor
        out.flush()


def select_plain(question, options):
    print(question)
    for i, opt in enumerate(options, 1):
        print(f"  {i}) {opt}")
    while True:
        ans = input("Number: ").strip()
        if ans.isdigit() and 1 <= int(ans) <= len(options):
            return int(ans) - 1


def edit(text):
    try:
        import readline
        readline.set_startup_hook(lambda: readline.insert_text(text))
        try:
            new = input(c("32", "? ") + c("1", "Message: ")).strip()
        finally:
            readline.set_startup_hook()
    except ImportError:  # Windows: no readline
        print(c("2", f"Current: {text}"))
        new = input(c("32", "? ") + c("1", "New message (empty = keep): ")).strip()
    return new or text


def with_spinner(label, fn):
    done = threading.Event()

    def spin():
        i = 0
        while not done.is_set():
            sys.stdout.write(f"\r{c('36', SPINNER[i % len(SPINNER)])} {label}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.08)
        sys.stdout.write("\r\x1b[K")
        sys.stdout.flush()

    t = threading.Thread(target=spin, daemon=True)
    if sys.stdout.isatty():
        t.start()
    try:
        return fn()
    finally:
        done.set()
        if t.is_alive():
            t.join()


# ---------- logic ----------

def preflight():
    if not shutil.which("git"):
        die("git is not installed.")
    if not shutil.which("claude"):
        die("Claude Code CLI is not installed.", "Install: curl -fsSL https://claude.ai/install.sh | bash")

    r = git("rev-parse", "--show-toplevel", check=False)
    if r.returncode != 0:
        die("This folder is not in a git repository.", os.getcwd())
    root = r.stdout.strip()
    os.chdir(root)
    info(f"Repository: {c('1', root)}")

    branch = git("branch", "--show-current").stdout.strip()
    if branch:
        info(f"Branch: {c('1', branch)}")
    else:
        warn("HEAD is detached. The commit will not be on a branch.")

    for name, label in (("MERGE_HEAD", "merge"), ("rebase-merge", "rebase"),
                        ("rebase-apply", "rebase"), ("CHERRY_PICK_HEAD", "cherry-pick")):
        path = git("rev-parse", "--git-path", name).stdout.strip()
        if os.path.exists(path):
            warn(f"A {label} is in progress.")
            break

    unmerged = git("diff", "--name-only", "--diff-filter=U").stdout.strip()
    if unmerged:
        die("There are unresolved merge conflicts.", unmerged.replace("\n", ", "))


def ensure_staged():
    staged = git("diff", "--staged", "--name-only").stdout.split("\n")
    staged = [f for f in staged if f]
    if staged:
        info(f"Staged files: {len(staged)}")
        return

    status = git("status", "--porcelain").stdout.rstrip()
    if not status:
        print("Nothing to commit. The working tree is clean.")
        sys.exit(0)

    lines = status.split("\n")
    warn("No files are staged. Changed files:")
    for line in lines[:15]:
        print("    " + c("2", line))
    if len(lines) > 15:
        print("    " + c("2", f"... and {len(lines) - 15} more"))

    if select("Select an action:", ["Add all files (git add -A)", "Exit"]) != 0:
        print("Stage files with: git add <files>")
        sys.exit(0)
    git("add", "-A")
    info("All files are staged.")


def staged_diff():
    stat = git("diff", "--staged", "--stat").stdout
    diff = git("diff", "--staged").stdout
    if len(diff) > MAX_DIFF_CHARS:
        warn(f"The diff is large ({len(diff)} chars). Only the first {MAX_DIFF_CHARS} are sent.")
        diff = diff[:MAX_DIFF_CHARS] + "\n[diff truncated]\n"
    return f"{stat}\n{diff}"


def generate(diff):
    def call():
        # Run outside the repo so Claude does not load project context.
        return subprocess.run(
            ["claude", "-p", "--model", MODEL, PROMPT],
            input=diff, capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=os.path.expanduser("~"),
        )

    r = with_spinner(f"Generating message with {MODEL}...", call)
    if r.returncode != 0:
        die("Claude returned an error.", (r.stderr or r.stdout).strip() or "Run 'claude' once to log in.")

    lines = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]
    if not lines:
        die("Claude returned an empty message.")
    return lines[0].strip("`\"' ").lstrip("-* ").strip()


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-v", "--version"):
            print(f"autocommit {VERSION}")
        else:
            print("Usage: autocommit\n\nStage changes (or let autocommit stage all), "
                  "generate a commit message with Claude, and commit.\n\n"
                  f"Env: AUTOCOMMIT_MODEL (default: haiku)")
        return

    preflight()
    ensure_staged()
    diff = staged_diff()
    msg = generate(diff)

    while True:
        print("\n  " + c("1;32", msg) + "\n")
        choice = select("Commit with this message?", ["Commit", "Edit", "Regenerate", "Cancel"])
        if choice == 0:
            break
        if choice == 1:
            msg = edit(msg)
        elif choice == 2:
            msg = generate(diff)
        else:
            print("Cancelled. Nothing is committed. Staged files stay staged.")
            return

    r = subprocess.run(["git", "commit", "-m", msg])
    if r.returncode != 0:
        die("git commit failed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write("\x1b[?25h\n")
        print("Cancelled.")
        sys.exit(130)
