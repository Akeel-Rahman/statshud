#!/usr/bin/env python3
"""
StatsHUD - Animated Cyber-Terminal Glass System Monitor for KDE Plasma & Linux
- Wayland-safe persistent keep-above (Qt.Window + KWin force rule)
- 6 Selectable Cyber Themes (Cyberpunk, Matrix, Nord, Amber CRT, Synthwave, Dracula)
- Continuous HSV dynamic load-based automatic coloring & ambient breathing
- Creative Stat Displays: RPG Moods, Kaomoji, Fuel Cells, Audio VU, Cyber Hex, Numeric
- Live rolling Braille sparkline, smooth eased bars, animated hacker spinner
- Dynamic hardware monitors: Battery, CPU Package Temperature, Disks, Cores
- Ultra-low CPU idle sleep (<0.5% CPU when values are stable)
"""

__version__ = "1.0.1"

import sys
import os
import json
import time
import math
from collections import deque
import psutil

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontDatabase, QPen, QBrush
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
        "stops": [(0.0, "#00ff41"), (0.6, "#00ffaa"), (0.85, "#aaff00"), (1.0, "#ff3300")]
    },
    "Nord Frost": {
        "bg": (20, 24, 34),
        "border": "#88c0d0",
        "fg": "#eceff4",
        "dim": "#4c566a",
        "accent": "#81a1c1",
        "stops": [(0.0, "#88c0d0"), (0.5, "#81a1c1"), (0.8, "#ebcb8b"), (1.0, "#bf616a")]
    },
    "Amber CRT": {
        "bg": (24, 14, 2),
        "border": "#ffb000",
        "fg": "#ffe099",
        "dim": "#704800",
        "accent": "#ffcc00",
        "stops": [(0.0, "#ffb000"), (0.5, "#ffcc00"), (0.8, "#ff8800"), (1.0, "#ff2200")]
    },
    "Synthwave 80s": {
        "bg": (22, 11, 38),
        "border": "#f92aad",
        "fg": "#fbe5ff",
        "dim": "#693570",
        "accent": "#00f0ff",
        "stops": [(0.0, "#00f0ff"), (0.5, "#f92aad"), (0.8, "#ffdd00"), (1.0, "#ff0055")]
    },
    "Dracula": {
        "bg": (21, 20, 30),
        "border": "#bd93f9",
        "fg": "#f8f8f2",
        "dim": "#6272a4",
        "accent": "#50fa7b",
        "stops": [(0.0, "#50fa7b"), (0.5, "#8be9fd"), (0.8, "#ffb86c"), (1.0, "#ff5555")]
    }
}

# --- CREATIVE STAT DISPLAY MODES ---
def mode_rpg_mood(pct):
    if pct < 15.0: return "[CHILL]"
    elif pct < 35.0: return "[VIBING]"
    elif pct < 60.0: return "[WORKIN]"
    elif pct < 85.0: return "[COOKIN]"
    else: return "[MELTDOWN]"

def mode_kaomoji(pct):
    if pct < 15.0: return "( ˘ ³˘)"
    elif pct < 35.0: return "(＾◡＾)"
    elif pct < 60.0: return "(⊙_☉)"
    elif pct < 85.0: return "( >_< )"
    else: return "(╯°□°)╯"

def mode_fuel_cells(pct):
    total_cells = 6
    filled = int(round((pct / 100.0) * total_cells))
    return ("⚡" * filled) + ("·" * (total_cells - filled))

def mode_audio_vu(pct):
    bars = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    idx = min(len(bars) - 1, max(0, int((pct / 100.0) * (len(bars) - 1))))
    return f"[{bars[idx] * 4}]"

def mode_cyber_hex(pct):
    val = int((pct / 100.0) * 255)
    return f"0x{val:02X} / 0xFF"

def mode_numeric(pct):
    return f"{pct:4.1f}%"

DISPLAY_MODES = {
    "RPG Moods [CHILL / COOKIN]": mode_rpg_mood,
    "Kaomoji System Mood": mode_kaomoji,
    "Cyber Fuel Cells": mode_fuel_cells,
    "Audio VU Equalizer": mode_audio_vu,
    "Cyber Hex": mode_cyber_hex,
    "Classic Numeric %": mode_numeric
}

# --- COLOR GRADIENT INTERPOLATOR ---
def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_qcolor(rgb, alpha=255):
    return QColor(int(rgb[0]), int(rgb[1]), int(rgb[2]), alpha)

def get_gradient_color(stops, pct):
    t = max(0.0, min(1.0, pct / 100.0))
    if t <= stops[0][0]:
        return rgb_to_qcolor(hex_to_rgb(stops[0][1]))
    if t >= stops[-1][0]:
        return rgb_to_qcolor(hex_to_rgb(stops[-1][1]))

    for i in range(len(stops) - 1):
        s0, c0_hex = stops[i]
        s1, c1_hex = stops[i+1]
        if s0 <= t <= s1:
            local_t = (t - s0) / (s1 - s0)
            c0 = hex_to_rgb(c0_hex)
            c1 = hex_to_rgb(c1_hex)
            r = c0[0] + (c1[0] - c0[0]) * local_t
            g = c0[1] + (c1[1] - c0[1]) * local_t
            b = c0[2] + (c1[2] - c0[2]) * local_t
            return rgb_to_qcolor((r, g, b))
    return QColor(255, 255, 255)


def make_braille_sparkline(vals):
    chars = []
    if len(vals) % 2 != 0:
        vals = [0.0] + vals
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
        except Exception as e:
            sys.stderr.write(f"[StatsHUD] Failed to parse {CONFIG_PATH}: {e}\n")
    return cfg

def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"[StatsHUD] Failed to write {CONFIG_PATH}: {e}\n")


class TerminalStatsHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()

        # Cache font once
        self.font_main = QFont("Adwaita Mono", 9)
        if not self.font_main.exactMatch():
            self.font_main = QFontDatabase.systemFont(QFontDatabase.FixedFont)
            self.font_main.setPointSize(9)

        # Eased metric percentages
        self.target_cpu = 0.0
        self.eased_cpu = 0.0
        self.target_ram = 0.0
        self.eased_ram = 0.0
        self.target_disk = 0.0
        self.eased_disk = 0.0

        # Hardware sensors
        self.has_battery = False
        self.battery_pct = 100.0
        self.battery_plugged = True
        self.has_temp = False
        self.cpu_temp = 0.0

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

        flags = Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        self.setWindowTitle("StatsHUD")
        self.resize(350, 240)
        self.move(self.cfg.get("x", 120), self.cfg.get("y", 120))

    def setup_timers(self):
        # 10 FPS Animation Timer (idle sleep enabled)
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

        # Smooth easing
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

        # Spinner update
        self.spinner_idx = (self.spinner_idx + 1) % len(SPINNER_FRAMES)

        # Blinking cursor
        if self.anim_frame % 5 == 0:
            self.cursor_blink = not self.cursor_blink

        # --- IDLE SLEEP DETECTION (~0% CPU) ---
        diff_cpu = abs(self.target_cpu - self.eased_cpu)
        diff_ram = abs(self.target_ram - self.eased_ram)
        diff_disk = abs(self.target_disk - self.eased_disk)
        diff_op = abs(self.target_opacity - self.current_opacity)

        if (diff_cpu < 0.3 and diff_ram < 0.3 and diff_disk < 0.3 and diff_op < 0.01
                and not self.is_alert and not self.hover_btn):
            # Values converged: snap and stop animation timer to sleep CPU
            self.eased_cpu = self.target_cpu
            self.eased_ram = self.target_ram
            self.eased_disk = self.target_disk
            self.current_opacity = self.target_opacity
            self.anim_timer.stop()
            self.update()
            return

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

            # Battery Sensor
            try:
                bat = psutil.sensors_battery()
                if bat is not None:
                    self.has_battery = True
                    self.battery_pct = bat.percent
                    self.battery_plugged = bat.power_plugged
                else:
                    self.has_battery = False
            except Exception as e:
                if not hasattr(self, "_logged_bat_err"):
                    sys.stderr.write(f"[StatsHUD] Battery sensor error: {e}\n")
                    self._logged_bat_err = True
                self.has_battery = False

            # CPU Temperature Sensor
            try:
                temps = psutil.sensors_temperatures()
                t_val = None
                if temps:
                    for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                        if key in temps and temps[key]:
                            t_val = temps[key][0].current
                            break
                    if t_val is None:
                        for s_list in temps.values():
                            if s_list:
                                t_val = s_list[0].current
                                break
                if t_val is not None:
                    self.has_temp = True
                    self.cpu_temp = t_val
                else:
                    self.has_temp = False
            except Exception as e:
                if not hasattr(self, "_logged_temp_err"):
                    sys.stderr.write(f"[StatsHUD] Temperature sensor error: {e}\n")
                    self._logged_temp_err = True
                self.has_temp = False

            # Dynamic Clarity Shift & Alert Threshold
            peak_load = max(cpu_pct, vm.percent)
            if not self.is_alert and peak_load >= 85.0:
                self.is_alert = True
                self.target_opacity = self.cfg.get("alert_opacity", 0.88)
            elif self.is_alert and peak_load < 80.0:
                self.is_alert = False
                self.target_opacity = self.cfg.get("idle_opacity", 0.45)

            # Wake up animation loop if metrics moved noticeably or in alert
            if (abs(self.target_cpu - self.eased_cpu) >= 0.3 or
                    abs(self.target_ram - self.eased_ram) >= 0.3 or
                    abs(self.target_disk - self.eased_disk) >= 0.3 or
                    self.is_alert):
                if not self.anim_timer.isActive():
                    self.anim_timer.start(100)

            self.update()

        except Exception as e:
            if not hasattr(self, "_logged_stats_err"):
                sys.stderr.write(f"[StatsHUD] Stats sampling error: {e}\n")
                self._logged_stats_err = True

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setFont(self.font_main)

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
        painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 6, 6)

        # Colors from theme
        fg_color = QColor(self.theme["fg"])
        dim_color = QColor(self.theme["dim"])
        accent_color = QColor(self.theme["accent"])

        x = 12
        y = 20
        line_height = 18

        # --- Header ---
        spinner_char = SPINNER_FRAMES[self.spinner_idx] if self.anim_timer.isActive() else "•"
        if self.is_alert:
            header_text = f"┌─ sys.hud [!] ALERT >85%"
            painter.setPen(QPen(QColor(255, 75, 75)))
        else:
            header_text = f"┌─ sys.hud [{spinner_char}]"
            painter.setPen(QPen(accent_color))
        painter.drawText(x, y, header_text)

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
        painter.setPen(QPen(dim_color))
        painter.drawText(x, y, "├" + "─" * 40)

        # Dynamic Colors for metrics
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

        temp_str = f" {self.cpu_temp:.0f}°C" if self.has_temp else ""
        painter.setPen(QPen(dim_color))
        painter.drawText(x + 235, y, f"[{self.cpu_cores}T{temp_str}]")

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
        painter.drawText(x + 235, y, f"{self.ram_used_gib:.1f}G")

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
        painter.drawText(x + 235, y, f"{self.disk_free_gib:.0f}G")

        # --- Optional Battery Row ---
        if self.has_battery:
            y += line_height
            bat_bar = render_ascii_bar(self.battery_pct, width=12)
            bat_color = get_gradient_color(self.theme["stops"], 100.0 - self.battery_pct) if self.auto_color else fg_color
            painter.setPen(QPen(dim_color))
            painter.drawText(x, y, "│")
            painter.setPen(QPen(fg_color))
            painter.drawText(x + 10, y, "BAT")
            painter.setPen(QPen(bat_color))
            painter.drawText(x + 44, y, bat_bar)
            painter.drawText(x + 155, y, f"{self.battery_pct:.0f}%")
            ac_tag = "[AC]" if self.battery_plugged else "[BAT]"
            painter.setPen(QPen(dim_color))
            painter.drawText(x + 235, y, ac_tag)

        # --- Bottom Status Bar ---
        y += line_height + 2
        curr_time = time.strftime("%H:%M:%S")
        cursor = "▌" if (self.cursor_blink and self.anim_timer.isActive()) else " "

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
        # Wake up animation timer if sleeping
        if not self.anim_timer.isActive():
            self.anim_timer.start(100)

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

        if self.drag_start_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_start_pos = None
        event.accept()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        step = 0.05 if delta > 0 else -0.05
        cur = self.cfg.get("idle_opacity", 0.45)
        new_op = max(0.20, min(0.98, cur + step))
        self.set_idle_opacity(new_op)
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

        # About entry
        about_act = menu.addAction(f"StatsHUD v{__version__}")
        about_act.setEnabled(False)
        menu.addSeparator()

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
