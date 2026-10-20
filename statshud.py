#!/usr/bin/env python3
"""
StatsHUD - Animated Cyber-Terminal Glass System Monitor for KDE Plasma / Linux
- Wayland-safe persistent keep-above (Qt.Window + KWin force rule)
- 6 Selectable Cyber Themes (Cyberpunk, Matrix, Nord, Amber CRT, Synthwave, Dracula)
- Continuous HSV dynamic load-based automatic coloring & ambient breathing
- Creative Stat Displays: RPG Moods, Kaomoji, Fuel Cells, Audio VU, Cyber Hex, Numeric
- Live rolling Braille sparkline, smooth eased bars, animated hacker spinner
- Auto clarity shift (45% -> 88%) + glowing alert border when load > 85%
"""

import sys
import os
import json
import time
import math
from collections import deque
import psutil

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QMenu
)

CONFIG_PATH = os.path.expanduser("~/.config/statshud.json")

DOTS_L = [0x40, 0x04, 0x02, 0x01]
DOTS_R = [0x80, 0x20, 0x10, 0x08]
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
PARTIAL_BLOCKS = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]

# --- THEME DEFINITIONS ---
THEMES = {
    "Cyberpunk Neon": {
        "bg": (13, 2, 33),
        "border": "#05d9e8",
        "fg": "#e0e0ff",
        "dim": "#5a5a8a",
        "accent": "#ff2a6d",
        "stops": [(0.0, "#05d9e8"), (0.5, "#d1f7ff"), (0.8, "#ff2a6d"), (1.0, "#ff003c")]
    },
    "Matrix Green": {
        "bg": (5, 16, 10),
        "border": "#00ff41",
        "fg": "#a3ffa3",
        "dim": "#005511",
        "accent": "#00ff41",
        "stops": [(0.0, "#00aa22"), (0.5, "#00ff41"), (0.8, "#66ff66"), (1.0, "#ffffff")]
    },
    "Nord Frost": {
        "bg": (46, 52, 64),
        "border": "#88c0d0",
        "fg": "#eceff4",
        "dim": "#4c566a",
        "accent": "#81a1c1",
        "stops": [(0.0, "#88c0d0"), (0.5, "#ebcb8b"), (0.8, "#d08770"), (1.0, "#bf616a")]
    },
    "Amber CRT": {
        "bg": (26, 15, 0),
        "border": "#ffb000",
        "fg": "#ffd066",
        "dim": "#804c00",
        "accent": "#ffb000",
        "stops": [(0.0, "#995500"), (0.5, "#ffb000"), (0.8, "#ff8800"), (1.0, "#ffe6a0")]
    },
    "Synthwave 80s": {
        "bg": (28, 18, 40),
        "border": "#ff6ad5",
        "fg": "#f9f871",
        "dim": "#664070",
        "accent": "#2de2e6",
        "stops": [(0.0, "#2de2e6"), (0.5, "#ff6ad5"), (0.8, "#ff3864"), (1.0, "#f9f871")]
    },
    "Dracula": {
        "bg": (30, 31, 41),
        "border": "#bd93f9",
        "fg": "#f8f8f2",
        "dim": "#6272a4",
        "accent": "#50fa7b",
        "stops": [(0.0, "#50fa7b"), (0.5, "#8be9fd"), (0.8, "#ffb86c"), (1.0, "#ff5555")]
    }
}

# --- CREATIVE STAT RENDERERS ---
def render_rpg_mood(pct):
    if pct < 25:
        return "[CHILL]   "
    elif pct < 50:
        return "[VIBING]  "
    elif pct < 70:
        return "[WORKIN]  "
    elif pct < 85:
        return "[COOKIN]  "
    else:
        return "[MELTDOWN]"

def render_kaomoji(pct):
    if pct < 25:
        return "( ˘ ³˘) "
    elif pct < 50:
        return "(＾◡＾) "
    elif pct < 70:
        return "(⊙_☉)   "
    elif pct < 85:
        return "( >_< ) "
    else:
        return "(╯°□°)╯ "

def render_fuel_cells(pct):
    cells = 8
    filled = int(round((pct / 100.0) * cells))
    filled = max(0, min(cells, filled))
    return "⚡" * filled + "·" * (cells - filled)

def render_audio_vu(pct):
    bars = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    total = 8
    fill_score = (pct / 100.0) * total
    out = ""
    for i in range(total):
        if fill_score >= i + 1:
            out += "█"
        elif fill_score > i:
            sub = int((fill_score - i) * 8)
            out += bars[sub]
        else:
            out += " "
    return f"[{out}]"

def render_cyber_hex(pct):
    val = int((pct / 100.0) * 255)
    return f"0x{val:02X}   "

def render_numeric(pct):
    return f"{pct:5.1f}%"

DISPLAY_MODES = {
    "RPG Moods [CHILL / COOKIN]": render_rpg_mood,
    "Kaomoji Mood ( ˘ ³˘) / (>_<)": render_kaomoji,
    "Cyber Fuel Cells [⚡⚡···]": render_fuel_cells,
    "Audio VU Meter [ ▃▅█]": render_audio_vu,
    "Cyber Hex [0x..]": render_cyber_hex,
    "Standard Numeric (64.2%)": render_numeric
}

# --- COLORIZER / LERP ---
def _lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    h1, s1, v1, _ = c1.getHsvF()
    h2, s2, v2, _ = c2.getHsvF()
    if h1 < 0: h1 = h2
    if h2 < 0: h2 = h1
    dh = ((h2 - h1 + 0.5) % 1.0) - 0.5
    h = (h1 + dh * t) % 1.0
    s = s1 + (s2 - s1) * t
    v = v1 + (v2 - v1) * t
    return QColor.fromHsvF(h, s, v)

def get_gradient_color(stops, pct):
    t = max(0.0, min(1.0, pct / 100.0))
    for (p0, c0_hex), (p1, c1_hex) in zip(stops, stops[1:]):
        if t <= p1:
            local_t = (t - p0) / (p1 - p0 or 1.0)
            return _lerp_color(QColor(c0_hex), QColor(c1_hex), local_t)
    return QColor(stops[-1][1])

def make_braille_sparkline(vals):
    if len(vals) % 2 != 0:
        vals = [0.0] + list(vals)
    chars = []
    for a, b in zip(vals[::2], vals[1::2]):
        c = 0x2800
        na = min(4, max(0, int(round(a * 4))))
        nb = min(4, max(0, int(round(b * 4))))
        for i in range(na):
            c |= DOTS_L[i]
        for i in range(nb):
            c |= DOTS_R[i]
        chars.append(chr(c))
    return "".join(chars)

def render_ascii_bar(pct, width=12):
    pct = max(0.0, min(100.0, pct))
    fill = (pct / 100.0) * width
    full_blocks = int(fill)
    remainder = fill - full_blocks
    bar = "█" * full_blocks
    if full_blocks < width:
        p_idx = int(remainder * 8)
        bar += PARTIAL_BLOCKS[p_idx]
        bar += "░" * (width - full_blocks - 1)
    return f"▕{bar}▏"

def get_disk_stats():
    for path in [os.path.expanduser("~"), "/"]:
        try:
            st = os.statvfs(path)
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            used = total - free
            if total > 0:
                return {
                    "total_gib": total / (1024**3),
                    "used_gib": used / (1024**3),
                    "free_gib": free / (1024**3),
                    "percent": (used / total) * 100.0
                }
        except Exception:
            continue
    return {"total_gib": 1.0, "used_gib": 0.0, "free_gib": 1.0, "percent": 0.0}

def load_config():
    cfg = {
        "x": 120,
        "y": 120,
        "idle_opacity": 0.45,
        "alert_opacity": 0.88,
        "theme": "Cyberpunk Neon",
        "display_mode": "RPG Moods [CHILL / COOKIN]",
        "auto_color": True,
        "refresh_ms": 1000
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg

def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


class TerminalStatsHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()

        # Eased metric percentages for butter-smooth animation
        self.target_cpu = 0.0
        self.eased_cpu = 0.0
        self.target_ram = 0.0
        self.eased_ram = 0.0
        self.target_disk = 0.0
        self.eased_disk = 0.0

        # Theme & Display Mode
        self.current_theme_name = self.cfg.get("theme", "Cyberpunk Neon")
        if self.current_theme_name not in THEMES:
            self.current_theme_name = "Cyberpunk Neon"
        self.theme = THEMES[self.current_theme_name]

        self.current_display_mode = self.cfg.get("display_mode", "RPG Moods [CHILL / COOKIN]")
        if self.current_display_mode not in DISPLAY_MODES:
            self.current_display_mode = "RPG Moods [CHILL / COOKIN]"
        self.render_stat = DISPLAY_MODES[self.current_display_mode]

        self.auto_color = self.cfg.get("auto_color", True)

        # Dynamic Opacity & Alert
        self.is_alert = False
        self.current_opacity = self.cfg.get("idle_opacity", 0.45)
        self.target_opacity = self.current_opacity
        self.glow_phase = 0.0
        self.ambient_pulse = 0.0

        # Readouts
        self.cpu_cores = psutil.cpu_count(logical=True) or 4
        self.ram_used_gib = 0.0
        self.ram_total_gib = 0.0
        self.disk_used_gib = 0.0
        self.disk_total_gib = 0.0
        self.disk_free_gib = 0.0

        # CPU sparkline history
        self.cpu_history = deque([0.0] * 28, maxlen=28)

        # UI state
        self.anim_frame = 0
        self.spinner_idx = 0
        self.cursor_blink = True
        self.drag_start_pos = None

        self.hover_btn = None
        self.btn_min_rect = QRectF(0, 0, 0, 0)
        self.btn_close_rect = QRectF(0, 0, 0, 0)

        self.setup_window()
        self.setup_timers()
        self.sample_stats()

    def setup_window(self):
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        # Qt.Window + Frameless + StaysOnTop
        flags = Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        self.setWindowTitle("StatsHUD")
        self.resize(350, 220)
        self.move(self.cfg.get("x", 120), self.cfg.get("y", 120))

    def setup_timers(self):
        # 10 FPS Animation Timer (low-CPU, energy-efficient)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.on_anim_tick)
        self.anim_timer.start(100)

        # Polling Timer for psutil stats
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.sample_stats)
        self.stats_timer.start(self.cfg.get("refresh_ms", 1000))

    def hideEvent(self, event):
        self.anim_timer.stop()
        self.stats_timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        if not self.anim_timer.isActive():
            self.anim_timer.start(100)
        if not self.stats_timer.isActive():
            self.stats_timer.start(self.cfg.get("refresh_ms", 1000))
        super().showEvent(event)

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized():
                self.anim_timer.stop()
                self.stats_timer.stop()
            else:
                if not self.anim_timer.isActive():
                    self.anim_timer.start(100)
                if not self.stats_timer.isActive():
                    self.stats_timer.start(self.cfg.get("refresh_ms", 1000))
        super().changeEvent(event)

    def on_anim_tick(self):
        self.anim_frame += 1

        # Smooth easing (adjusted for 100ms ticks)
        self.eased_cpu += (self.target_cpu - self.eased_cpu) * 0.35
        self.eased_ram += (self.target_ram - self.eased_ram) * 0.35
        self.eased_disk += (self.target_disk - self.eased_disk) * 0.35

        # Smooth opacity easing
        self.current_opacity += (self.target_opacity - self.current_opacity) * 0.30

        # Ambient breathing (speeds up with CPU load)
        breath_speed = 0.12 + 0.25 * (self.eased_cpu / 100.0)
        self.ambient_pulse = (self.ambient_pulse + breath_speed) % (2 * math.pi)

        # Alert pulse
        if self.is_alert:
            self.glow_phase = (self.glow_phase + 0.25) % (2 * math.pi)

        # Spinner update (advances every tick at 10 FPS)
        self.spinner_idx = (self.spinner_idx + 1) % len(SPINNER_FRAMES)

        # Blinking cursor
        if self.anim_frame % 15 == 0:
            self.cursor_blink = not self.cursor_blink

        self.update()

    def sample_stats(self):
        try:
            # CPU
            cpu_pct = psutil.cpu_percent(interval=None)
            self.target_cpu = cpu_pct
            self.cpu_history.append(cpu_pct / 100.0)

            # RAM
            vm = psutil.virtual_memory()
            self.target_ram = vm.percent
            self.ram_used_gib = (vm.total - vm.available) / (1024**3)
            self.ram_total_gib = vm.total / (1024**3)

            # Disk
            disk = get_disk_stats()
            self.target_disk = disk["percent"]
            self.disk_used_gib = disk["used_gib"]
            self.disk_total_gib = disk["total_gib"]
            self.disk_free_gib = disk["free_gib"]

            # Dynamic Clarity Shift & Alert Threshold
            peak_load = max(cpu_pct, vm.percent)
            if not self.is_alert and peak_load >= 85.0:
                self.is_alert = True
                self.target_opacity = self.cfg.get("alert_opacity", 0.88)
            elif self.is_alert and peak_load < 80.0:
                self.is_alert = False
                self.target_opacity = self.cfg.get("idle_opacity", 0.45)

        except Exception:
            pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # Base background with current dynamic opacity
        bg_rgb = self.theme["bg"]
        bg_alpha = int(max(0.15, min(0.98, self.current_opacity)) * 255)
        painter.setBrush(QBrush(QColor(bg_rgb[0], bg_rgb[1], bg_rgb[2], bg_alpha)))

        # Border styling:
        if self.is_alert:
            pulse = 0.5 + 0.5 * math.sin(self.glow_phase)
            border_col = QColor(255, 50, 50, int(150 + 105 * pulse))
            border_pen = QPen(border_col, 2)
        else:
            border_base = QColor(self.theme["border"])
            border_base.setAlpha(120)
            border_pen = QPen(border_base, 1)

        painter.setPen(border_pen)
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 8, 8)

        # Monospace Font
        font = QFont("Adwaita Mono", 10)
        font.setStyleHint(QFont.Monospace)
        painter.setFont(font)

        line_height = 20
        y = 24
        x = 16

        # Header Colors
        accent_color = QColor(self.theme["accent"])
        fg_color = QColor(self.theme["fg"])
        dim_color = QColor(self.theme["dim"])

        # --- Top Header Line ---
        spinner_char = SPINNER_FRAMES[self.spinner_idx]
        if self.is_alert:
            header_text = f"┌─ sys.hud [!] ALERT >85%"
            painter.setPen(QPen(QColor(255, 75, 75)))
        else:
            header_text = f"┌─ sys.hud [{spinner_char}]"
            painter.setPen(QPen(accent_color))
        painter.drawText(x, y, header_text)

        # Theme indicator / status
        theme_tag = f" [{self.current_theme_name[:5]}] "
        painter.setPen(QPen(dim_color))
        painter.drawText(x + 130, y, theme_tag)

        # Header Buttons: [─] [✕]
        self.btn_min_rect = QRectF(w - 68, y - 14, 22, 18)
        self.btn_close_rect = QRectF(w - 40, y - 14, 22, 18)

        # Minimize Button
        if self.hover_btn == "min":
            painter.fillRect(self.btn_min_rect, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 60))
        painter.setPen(QPen(accent_color if self.hover_btn != "min" else QColor(255, 255, 255)))
        painter.drawText(self.btn_min_rect, Qt.AlignCenter, "─")

        # Close Button
        if self.hover_btn == "close":
            painter.fillRect(self.btn_close_rect, QColor(255, 60, 80, 120))
        painter.setPen(QPen(QColor(255, 100, 100) if self.hover_btn != "close" else QColor(255, 255, 255)))
        painter.drawText(self.btn_close_rect, Qt.AlignCenter, "✕")

        # Divider
        y += line_height
        divider_pen = QPen(dim_color)
        painter.setPen(divider_pen)
        painter.drawText(x, y, "├" + "─" * 40)

        # --- Dynamic Colors for metrics ---
        if self.auto_color:
            cpu_color = get_gradient_color(self.theme["stops"], self.eased_cpu)
            ram_color = get_gradient_color(self.theme["stops"], self.eased_ram)
            disk_color = get_gradient_color(self.theme["stops"], self.eased_disk)
        else:
            cpu_color = fg_color
            ram_color = fg_color
            disk_color = fg_color

        # --- CPU Row ---
        y += line_height
        cpu_val = self.eased_cpu
        cpu_bar = render_ascii_bar(cpu_val, width=12)
        cpu_creative = self.render_stat(cpu_val)

        painter.setPen(QPen(dim_color))
        painter.drawText(x, y, "│")
        painter.setPen(QPen(fg_color))
        painter.drawText(x + 10, y, "CPU")
        painter.setPen(QPen(cpu_color))
        painter.drawText(x + 44, y, cpu_bar)
        painter.drawText(x + 155, y, cpu_creative)

        painter.setPen(QPen(dim_color))
        painter.drawText(x + 248, y, f"[{self.cpu_cores}T]")

        # --- CPU Sparkline Wave ---
        y += line_height - 2
        braille_str = make_braille_sparkline(list(self.cpu_history))
        painter.setPen(QPen(dim_color))
        painter.drawText(x, y, "│")
        painter.setPen(QPen(cpu_color))
        painter.drawText(x + 44, y, f"~ {braille_str}")
        painter.setPen(QPen(dim_color))
        painter.drawText(x + 205, y, "rolling wave")

        # --- RAM Row ---
        y += line_height + 2
        ram_val = self.eased_ram
        ram_bar = render_ascii_bar(ram_val, width=12)
        ram_creative = self.render_stat(ram_val)

        painter.setPen(QPen(dim_color))
        painter.drawText(x, y, "│")
        painter.setPen(QPen(fg_color))
        painter.drawText(x + 10, y, "MEM")
        painter.setPen(QPen(ram_color))
        painter.drawText(x + 44, y, ram_bar)
        painter.drawText(x + 155, y, ram_creative)

        painter.setPen(QPen(dim_color))
        painter.drawText(x + 248, y, f"{self.ram_used_gib:.1f}G")

        # --- STORAGE Row ---
        y += line_height
        disk_val = self.eased_disk
        disk_bar = render_ascii_bar(disk_val, width=12)
        disk_creative = self.render_stat(disk_val)

        painter.setPen(QPen(dim_color))
        painter.drawText(x, y, "│")
        painter.setPen(QPen(fg_color))
        painter.drawText(x + 10, y, "DSK")
        painter.setPen(QPen(disk_color))
        painter.drawText(x + 44, y, disk_bar)
        painter.drawText(x + 155, y, disk_creative)

        painter.setPen(QPen(dim_color))
        painter.drawText(x + 248, y, f"{self.disk_free_gib:.0f}G")

        # --- Bottom Status Bar ---
        y += line_height + 2
        curr_time = time.strftime("%H:%M:%S")
        cursor = "▌" if self.cursor_blink else " "

        painter.setPen(QPen(accent_color))
        painter.drawText(x, y, "└─ fedora@plasma")

        painter.setPen(QPen(fg_color))
        painter.drawText(w - 110, y, f"{curr_time} {cursor}")

    # Mouse & Drag
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position()
            if self.btn_min_rect.contains(pos):
                self.showMinimized()
                return
            if self.btn_close_rect.contains(pos):
                self.close()
                return

            wh = self.windowHandle()
            if wh and hasattr(wh, "startSystemMove") and wh.startSystemMove():
                return
            self.drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position()
        old_hover = self.hover_btn
        if self.btn_min_rect.contains(pos):
            self.hover_btn = "min"
        elif self.btn_close_rect.contains(pos):
            self.hover_btn = "close"
        else:
            self.hover_btn = None

        if old_hover != self.hover_btn:
            self.update()

        if self.drag_start_pos is not None and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPosition().toPoint() - self.drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.drag_start_pos is not None:
            self.drag_start_pos = None
            self.cfg["x"] = self.x()
            self.cfg["y"] = self.y()
            save_config(self.cfg)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        cur = self.cfg.get("idle_opacity", 0.45)
        if delta > 0:
            new_op = min(cur + 0.04, 0.95)
        else:
            new_op = max(cur - 0.04, 0.20)
        self.cfg["idle_opacity"] = round(new_op, 2)
        if not self.is_alert:
            self.target_opacity = self.cfg["idle_opacity"]
        save_config(self.cfg)
        self.update()
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        theme_fg = self.theme["fg"]
        theme_accent = self.theme["accent"]
        bg_rgb = self.theme["bg"]

        menu.setStyleSheet(f"""
            QMenu {{
                background-color: rgba({bg_rgb[0]}, {bg_rgb[1]}, {bg_rgb[2]}, 0.96);
                color: {theme_fg};
                border: 1px solid {theme_accent};
                font-family: 'Adwaita Mono', monospace;
                font-size: 11px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 5px 18px;
            }}
            QMenu::item:selected {{
                background-color: rgba(255, 255, 255, 0.15);
                color: #ffffff;
            }}
        """)

        # 1. Themes Submenu
        theme_menu = menu.addMenu("🎨 Themes")
        for t_name in THEMES:
            prefix = "● " if t_name == self.current_theme_name else "  "
            act = theme_menu.addAction(f"{prefix}{t_name}")
            act.triggered.connect(lambda chk=False, name=t_name: self.set_theme(name))

        # 2. Creative Display Modes Submenu
        disp_menu = menu.addMenu("✨ Display Mode (Instead of Numbers)")
        for m_name in DISPLAY_MODES:
            prefix = "● " if m_name == self.current_display_mode else "  "
            act = disp_menu.addAction(f"{prefix}{m_name}")
            act.triggered.connect(lambda chk=False, name=m_name: self.set_display_mode(name))

        # 3. Dynamic Color Toggle
        color_act = menu.addAction("✔ Auto Dynamic Colors" if self.auto_color else "  Auto Dynamic Colors")
        color_act.triggered.connect(self.toggle_auto_color)

        menu.addSeparator()

        # 4. Opacity Presets
        op_menu = menu.addMenu("Opacity Presets")
        for val in [0.35, 0.45, 0.60, 0.85]:
            act = op_menu.addAction(f"{int(val * 100)}%")
            act.triggered.connect(lambda chk=False, v=val: self.set_idle_opacity(v))

        # 5. Refresh Rate
        rate_menu = menu.addMenu("Refresh Rate")
        for ms, label in [(500, "0.5 sec"), (1000, "1.0 sec"), (2000, "2.0 sec")]:
            act = rate_menu.addAction(label)
            act.triggered.connect(lambda chk=False, val=ms: self.set_refresh_rate(val))

        menu.addSeparator()
        min_act = menu.addAction("Minimize [─]")
        min_act.triggered.connect(self.showMinimized)

        close_act = menu.addAction("Quit StatsHUD [✕]")
        close_act.triggered.connect(self.close)

        menu.exec(event.globalPos())

    def set_theme(self, name):
        if name in THEMES:
            self.current_theme_name = name
            self.theme = THEMES[name]
            self.cfg["theme"] = name
            save_config(self.cfg)
            self.update()

    def set_display_mode(self, name):
        if name in DISPLAY_MODES:
            self.current_display_mode = name
            self.render_stat = DISPLAY_MODES[name]
            self.cfg["display_mode"] = name
            save_config(self.cfg)
            self.update()

    def toggle_auto_color(self):
        self.auto_color = not self.auto_color
        self.cfg["auto_color"] = self.auto_color
        save_config(self.cfg)
        self.update()

    def set_idle_opacity(self, op):
        self.cfg["idle_opacity"] = op
        save_config(self.cfg)
        if not self.is_alert:
            self.target_opacity = op
        self.update()

    def set_refresh_rate(self, ms):
        self.cfg["refresh_ms"] = ms
        save_config(self.cfg)
        self.stats_timer.setInterval(ms)

    def closeEvent(self, event):
        self.cfg["x"] = self.x()
        self.cfg["y"] = self.y()
        save_config(self.cfg)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setDesktopFileName("statshud")
    app.setApplicationName("statshud")

    psutil.cpu_percent(interval=None)

    hud = TerminalStatsHUD()
    hud.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
