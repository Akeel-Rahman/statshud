# ⚡ StatsHUD

> **Animated Cyber-Terminal Glass System Monitor for KDE Plasma & Linux**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-41CD52.svg?logo=qt&logoColor=white)](https://qt.io)
[![Wayland](https://img.shields.io/badge/Display-Wayland%20%7C%20X11-orange.svg)](https://wayland.freedesktop.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**StatsHUD** is an ultra-lightweight, floating system monitor widget designed for modern Linux desktops (specifically optimized for KDE Plasma 6 Wayland and X11). It blends translucent frosted cyber-glass with animated terminal aesthetics, continuous HSV load-based color gradients, and creative non-numeric status displays.

---

## ✨ Features

- **🛡 Guaranteed Wayland Stay-On-Top:** Configured with KWin window rules to stay permanently pinned above existing and newly opened windows without focus-loss hiding.
- **🌫 Ultra-Translucent Idle Glass:** Defaults to 45% background opacity so content underneath remains fully readable.
- **🚨 Dynamic 85% Overload Alert:** When CPU or RAM hits 85%, the HUD automatically shifts from 45% to 88% crisp opacity with an animated pulsating alert border.
- **📈 Rolling Braille Sparklines:** Real-time rolling wave graph (`~ ⢀⣤⣾⣷⣄⠀`) rendering live CPU activity.
- **🌀 Animated Hacker Glyphs:** Rotating spinner and live pulsing terminal cursor.
- **🎨 6 Switchable Cyber Themes:**
  - `Cyberpunk Neon` (Electric cyan, neon pink, deep glass)
  - `Matrix Green` (Monochrome phosphor green)
  - `Nord Frost` (Arctic blues and blizzard white)
  - `Amber CRT` (Vintage retro terminal amber)
  - `Synthwave 80s` (Sunset violet, cyan, and sunny yellow)
  - `Dracula` (Vampire purple, toxic green, blood coral)
- **🕹 Creative Status Display Modes:**
  - 🎮 **RPG Moods:** `[CHILL]` → `[VIBING]` → `[WORKIN]` → `[COOKIN]` → `[MELTDOWN]`
  - 😸 **Kaomoji System Mood:** `( ˘ ³˘)` → `(＾◡＾)` → `(⊙_☉)` → `( >_< )` → `(╯°□°)╯`
  - ⚡ **Cyber Fuel Cells:** `⚡⚡······`
  - 🎚 **Audio VU Equalizer:** `[ ▂▃▄▅   ]`
  - 💻 **Cyber Hex:** `0x1F / 0x7A`
  - 🔢 **Classic Numeric:** `64.2%`
- **⚡ Energy Efficient:** Optimized event loop (<1% idle CPU) that automatically pauses animation repaints when minimized or hidden.

---

## 🚀 Installation

### 1. Prerequisites
Install `PySide6` and `psutil` using your distribution package manager:

**Fedora / RHEL:**
```bash
sudo dnf install python3-pyside6 python3-psutil
```

**Arch Linux:**
```bash
sudo pacman -S python-pyside6 python-psutil
```

**Ubuntu / Debian:**
```bash
sudo apt install python3-pyside6 python3-psutil
```

*(Alternatively via pip: `pip install --user PySide6 psutil`)*

---

### 2. Quick Install
Clone the repository and run the installer:
```bash
git clone https://github.com/Akeel-Rahman/statshud.git
cd statshud
chmod +x install.sh
./install.sh
```

Launch anytime from your application launcher or by running:
```bash
statshud
```

---

## 🕹 Controls & Shortcuts

| Action | Control |
|---|---|
| **Move Window** | Click and drag anywhere across the HUD |
| **Adjust Opacity** | Scroll mouse wheel over the widget (10% to 100%) |
| **Open Menu** | Right-click anywhere on the HUD |
| **Change Theme** | Right-click → **🎨 Themes** → Choose from 6 palettes |
| **Change Stat Mode** | Right-click → **✨ Display Mode** → Select RPG, Kaomoji, VU, etc. |
| **Toggle Auto-Color** | Right-click → Toggle dynamic load-based color gradient |
| **Minimize / Close** | `[─]` and `[✕]` buttons in the top-right header |

---

## 🗑 Uninstallation
To completely remove StatsHUD and its KWin rules:
```bash
cd statshud
chmod +x uninstall.sh
./uninstall.sh
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.
