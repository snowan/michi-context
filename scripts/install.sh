#!/usr/bin/env bash
set -euo pipefail

SETTINGS_FILE="$HOME/.claude/settings.json"

echo "michi-context: installing Claude Code hooks..."

if ! command -v michi-context &>/dev/null; then
    echo "Error: michi-context not found. Run: pip install -e . first" >&2
    exit 1
fi

MICHI_PATH=$(command -v michi-context)
echo "Found michi-context at: $MICHI_PATH"

if [ -f "$SETTINGS_FILE" ]; then
    cp "$SETTINGS_FILE" "${SETTINGS_FILE}.bak.$(date +%s)"
    echo "Backed up existing settings"
fi

mkdir -p "$(dirname "$SETTINGS_FILE")"

python3 - "$SETTINGS_FILE" "$MICHI_PATH" <<'PYTHON'
import json
import sys

settings_file = sys.argv[1]
michi_path = sys.argv[2]

try:
    with open(settings_file) as f:
        settings = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    settings = {}

hooks = settings.setdefault("hooks", {})

inject_cmd = f"{michi_path} inject --project $CWD"
hook_entry = {"type": "command", "command": inject_cmd}

session_start = hooks.get("SessionStart", [])
if isinstance(session_start, list):
    existing = [h for h in session_start if "michi-context" in h.get("command", "")]
    if not existing:
        session_start.append(hook_entry)
else:
    session_start = [hook_entry]
hooks["SessionStart"] = session_start

with open(settings_file, "w") as f:
    json.dump(settings, f, indent=2)

print(f"Hook installed: SessionStart → {inject_cmd}")
PYTHON

echo "Done! New Claude Code sessions will receive context from michi-context."
echo ""
echo "Optional: run 'michi-context daemon' in the background for auto-capture."
