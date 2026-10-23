#!/bin/sh
# Install: curl -fsSL https://raw.githubusercontent.com/tomasmajercik/autoCommit/main/install.sh | sh
set -e

REPO="${AUTOCOMMIT_REPO:-tomasmajercik/autoCommit}"
BRANCH="${AUTOCOMMIT_BRANCH:-main}"
DIR="${AUTOCOMMIT_DIR:-$HOME/.local/bin}"
URL="https://raw.githubusercontent.com/$REPO/$BRANCH/autocommit.py"

# Find Python 3 (Windows often has only "python").
PY=""
for p in python3 python; do
  if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>/dev/null; then
    PY="$p"; break
  fi
done
[ -n "$PY" ] || { echo "Error: Python 3.8+ is necessary." >&2; exit 1; }

command -v git >/dev/null 2>&1 || echo "Warning: git is not installed."
command -v claude >/dev/null 2>&1 || echo "Warning: Claude Code CLI is not installed: curl -fsSL https://claude.ai/install.sh | bash"

mkdir -p "$DIR"
TMP="$(mktemp)"
curl -fsSL "$URL" -o "$TMP"
# Use the Python that we found.
{ echo "#!/usr/bin/env $PY"; tail -n +2 "$TMP"; } > "$DIR/autocommit"
rm -f "$TMP"
chmod +x "$DIR/autocommit"

echo "Installed: $DIR/autocommit"
case ":$PATH:" in
  *":$DIR:"*) echo "Run: autocommit" ;;
  *) echo "Add this to your shell config, then restart the terminal:"
     echo "  export PATH=\"$DIR:\$PATH\"" ;;
esac
