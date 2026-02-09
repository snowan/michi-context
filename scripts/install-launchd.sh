#!/usr/bin/env bash
set -euo pipefail

LABEL="com.michi-context.daemon"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"

if ! command -v michi-context &>/dev/null; then
    echo "Error: michi-context not found. Run: pip install -e . first" >&2
    exit 1
fi

MICHI_PATH=$(command -v michi-context)

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${MICHI_PATH}</string>
        <string>daemon</string>
        <string>--interval</string>
        <string>1800</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${HOME}/.michi-context/daemon.log</string>
    <key>StandardErrorPath</key>
    <string>${HOME}/.michi-context/daemon.err</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "michi-context daemon installed and started"
echo "  Plist: $PLIST"
echo "  Logs:  ~/.michi-context/daemon.log"
echo ""
echo "To stop: launchctl unload $PLIST"
