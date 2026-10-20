#!/usr/bin/env bash
set -e

echo "=== StatsHUD Uninstaller ==="

# Stop running instance
pkill -f statshud 2>/dev/null || true

PREFIX_BIN="${HOME}/.local/bin"
PREFIX_DATA="${HOME}/.local/share/statshud"
PREFIX_APP="${HOME}/.local/share/applications"
AUTOSTART_APP="${HOME}/.config/autostart"

echo "Removing installed files..."
rm -rf "${PREFIX_DATA}"
rm -f "${PREFIX_BIN}/statshud"
rm -f "${PREFIX_APP}/statshud.desktop"
rm -f "${AUTOSTART_APP}/statshud.desktop"

# Clean KWin rule if present
if command -v kwriteconfig6 &>/dev/null; then
    echo "Cleaning KWin rules..."
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --delete 2>/dev/null || true
    qdbus org.kde.KWin /KWin reconfigure 2>/dev/null || \
    busctl --user call org.kde.KWin /KWin org.kde.KWin reconfigure 2>/dev/null || true
fi

echo "=== Uninstallation Complete ==="
