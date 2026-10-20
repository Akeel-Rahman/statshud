#!/usr/bin/env bash
set -e

echo "=== StatsHUD Installer ==="

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

# Check PySide6 and psutil
MISSING_DEPS=0
python3 -c "import PySide6" 2>/dev/null || MISSING_DEPS=1
python3 -c "import psutil" 2>/dev/null || MISSING_DEPS=1

if [ "$MISSING_DEPS" -eq 1 ]; then
    echo "Notice: Missing required Python libraries (PySide6 and/or psutil)."
    echo ""
    echo "Install them using your distribution's package manager:"
    echo "  Fedora:      sudo dnf install python3-pyside6 python3-psutil"
    echo "  Arch Linux:  sudo pacman -S python-pyside6 python-psutil"
    echo "  Ubuntu/Deb:  sudo apt install python3-pyside6 python3-psutil"
    echo ""
    echo "Or via pip:"
    echo "  pip install --user PySide6 psutil"
    echo ""
    read -p "Continue installation anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

PREFIX_BIN="${HOME}/.local/bin"
PREFIX_DATA="${HOME}/.local/share/statshud"
PREFIX_APP="${HOME}/.local/share/applications"

mkdir -p "${PREFIX_BIN}" "${PREFIX_DATA}" "${PREFIX_APP}"

echo "Installing files to ${PREFIX_DATA}..."
cp "$(dirname "$0")/statshud.py" "${PREFIX_DATA}/statshud.py"
chmod +x "${PREFIX_DATA}/statshud.py"

ln -sf "${PREFIX_DATA}/statshud.py" "${PREFIX_BIN}/statshud"

echo "Installing desktop launcher..."
cp "$(dirname "$0")/statshud.desktop" "${PREFIX_APP}/statshud.desktop"

# KDE Plasma KWin rule configuration
if command -v kwriteconfig6 &>/dev/null; then
    echo "Configuring KDE Plasma KWin rule (Always on Top)..."
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --key "Description" "StatsHUD always on top"
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --key "wmclass" "statshud"
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --key "wmclassmatch" 1
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --key "above" "true"
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --key "aboverule" 2
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --key "skiptaskbar" "true"
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --key "skiptaskbarrule" 2
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --key "skippager" "true"
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --key "skippagerrule" 2
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --key "skipswitcher" "true"
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --key "skipswitcherrule" 2
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --key "onalldesktops" "true"
    kwriteconfig6 --file kwinrulesrc --group "statshud-keepabove" --key "onalldesktopsrule" 2

    # Reload KWin rules if running
    qdbus org.kde.KWin /KWin reconfigure 2>/dev/null || \
    busctl --user call org.kde.KWin /KWin org.kde.KWin reconfigure 2>/dev/null || true
fi

echo ""
echo "=== Installation Complete! ==="
echo "Launch anytime with: statshud"
echo "Or find 'StatsHUD' in your Application Menu."
