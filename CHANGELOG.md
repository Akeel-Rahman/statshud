# Changelog

All notable changes to **StatsHUD** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-10-21

### Added
- **Dedicated Temperature Row (`TMP`):** Full-width animated ASCII bar, creative status indicators, and live CPU package temperature readout.
- **Battery Monitoring Row (`BAT`):** Live percentage bar, charging detection (`[AC]`/`[BAT]`), and estimated runtime (`[2h15m]` or `[FULL]`).
- **Font Caching:** Single-instance `QFont` initialization with system `FixedFont` fallback.
- **About Info:** Version identifier displayed in right-click context menu.

### Performance
- **Idle Sleep:** Automatically stops the animation timer when system metrics converge, dropping idle CPU utilization to **0.0%**.
- **Adaptive Wake Thresholds:** Resumes animation loop only on meaningful load shifts (≥2% CPU, ≥1% memory/disk/temp) or active alerts.

### Changed
- **Installer:** Made desktop autostart an explicit opt-in via `./install.sh --autostart`.
- **Backward Compatibility:** Preserved original v1.0.0 theme palettes and configuration keys in `~/.config/statshud.json`.

---

## [1.0.0] - 2026-10-21

### Added
- Initial public release of StatsHUD.
- Wayland-safe persistent keep-above behavior via KWin window rules.
- 6 switchable cyber themes (Cyberpunk Neon, Matrix Green, Nord Frost, Amber CRT, Synthwave 80s, Dracula).
- 6 creative stat display modes (RPG Moods, Kaomoji, Fuel Cells, Audio VU, Cyber Hex, Classic Numeric).
- Dynamic 85% load-based opacity shift (45% idle → 88% alert) with glowing border.
- Real-time rolling Braille sparklines and hacker glyph spinners.
- 1-click user installation (`install.sh`) and removal (`uninstall.sh`) scripts without `sudo`.
