"""
SoundWave Studio — مسجل صوت + محلل ذبذبات تفاعلي
=================================================
برنامج موحّد بواجهة Pygame:
  • وضع المحلل (Visualizer): أعمدة/موجات ملونة في الوقت الفعلي
  • وضع المسجّل (Recorder): تسجيل وحفظ ملفات WAV
  • قناة ميكروفون واحدة مشتركة — بدون تداخل

التثبيت:
    pip install pygame numpy sounddevice

التشغيل:
    python audio_visualizer.py

اختصارات:
    Tab / 1 / 2  - التبديل بين المحلل والمسجّل
    R            - بدء/إيقاف التسجيل
    M            - تبديل Blocks / Waves (وضع المحلل)
    F            - ملء الشاشة
    ESC          - خروج من ملء الشاشة أو إغلاق البرنامج
    UP/DOWN      - زيادة/تقليل حساسية الميكروفون
"""

import os
import subprocess
import sys
import threading
import time
import wave
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np
import pygame
import sounddevice as sd

# ─────────────────────────────────────────────
# إعدادات النافذة والعرض
# ─────────────────────────────────────────────
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FPS = 60
BG_COLOR = (0, 0, 0)

CONTROL_PANEL_HEIGHT = 100
PANEL_BG = (20, 20, 20)
PANEL_BORDER = (70, 70, 70)
TEXT_MAIN = (230, 230, 230)
TEXT_DIM = (150, 150, 150)
TEXT_KEY = (120, 200, 255)
TEXT_RECORD = (255, 80, 80)
TEXT_OK = (80, 220, 120)

BTN_COLORS = {
    "tab_visualizer": (45, 75, 130),
    "tab_recorder": (130, 75, 45),
    "toggle_mode": (45, 75, 130),
    "gain_down": (120, 55, 55),
    "gain_up": (55, 120, 70),
    "record": (180, 45, 45),
    "stop_record": (200, 60, 60),
    "open_folder": (70, 90, 120),
    "fullscreen": (120, 100, 45),
    "quit": (130, 50, 50),
}
BTN_HOVER_BOOST = 35
BTN_ACTIVE_BOOST = 55

# ─────────────────────────────────────────────
# إعدادات الشبكة (الأعمدة والمربعات)
# ─────────────────────────────────────────────
NUM_COLUMNS = 64
BLOCK_SIZE = 10
BLOCK_GAP = 2
COLUMN_GAP = 4

# ─────────────────────────────────────────────
# إعدادات الصوت
# ─────────────────────────────────────────────
SAMPLE_RATE = 44100
BLOCK_SAMPLES = 2048
CHANNELS = 1
RECORDINGS_DIR = Path(__file__).parent / "recordings"

# ─────────────────────────────────────────────
# إعدادات الحركة والحساسية
# ─────────────────────────────────────────────
RISE_SPEED = 1.0
FALL_SPEED = 0.08
GAIN_STEP = 0.15
GAIN_MIN = 0.1
GAIN_MAX = 8.0
GAIN_DEFAULT = 1.0
PEAK_CEILING = 0.65
PEAK_COMPRESSION = 0.75

# ─────────────────────────────────────────────
# أوضاع العرض
# ─────────────────────────────────────────────
APP_VISUALIZER = "visualizer"
APP_RECORDER = "recorder"

MODE_BLOCKS = "blocks"
MODE_WAVES = "waves"
WAVE_SMOOTH_POINTS = 320
WAVE_LINE_WIDTH = 3

# ─────────────────────────────────────────────
# مسطرة شدة الصوت
# ─────────────────────────────────────────────
METER_WIDTH = 76
METER_WIDTH_FULLSCREEN = 96
METER_RMS_TARGET = 0.22
METER_PEAK_FALL = 0.012
METER_UNIT = "RMS"
METER_SCALE_MAX = 100
METER_SCALE_STEP = 10

COLOR_BOTTOM = np.array([50, 220, 80], dtype=np.float32)
COLOR_MIDDLE = np.array([255, 220, 50], dtype=np.float32)
COLOR_TOP = np.array([220, 50, 255], dtype=np.float32)


def resource_path(relative: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return str(Path(__file__).parent / relative)


def set_app_icon() -> None:
    for name in ("assets/app_icon.png", "assets/app_icon.ico", "app_icon.ico"):
        icon_path = resource_path(name)
        if os.path.exists(icon_path):
            try:
                pygame.display.set_icon(pygame.image.load(icon_path))
            except pygame.error:
                pass
            return


def log_spaced_frequencies(num_bands: int, sample_rate: int, block_size: int) -> np.ndarray:
    nyquist = sample_rate / 2.0
    return np.logspace(np.log10(20), np.log10(nyquist), num_bands + 1)


def build_band_weights(num_bands: int, block_size: int, sample_rate: int) -> np.ndarray:
    freq_edges = log_spaced_frequencies(num_bands, sample_rate, block_size)
    fft_freqs = np.fft.rfftfreq(block_size, d=1.0 / sample_rate)
    weights = np.zeros((num_bands, len(fft_freqs)), dtype=np.float32)

    for i in range(num_bands):
        low, high = freq_edges[i], freq_edges[i + 1]
        mask = (fft_freqs >= low) & (fft_freqs < high)
        if np.any(mask):
            weights[i, mask] = 1.0

    row_sums = weights.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    weights /= row_sums
    return weights


def lerp_color(ratio: float) -> tuple[int, int, int]:
    ratio = float(np.clip(ratio, 0.0, 1.0))
    if ratio <= 0.5:
        t = ratio / 0.5
        color = COLOR_BOTTOM * (1.0 - t) + COLOR_MIDDLE * t
    else:
        t = (ratio - 0.5) / 0.5
        color = COLOR_MIDDLE * (1.0 - t) + COLOR_TOP * t
    return tuple(int(c) for c in color)


def save_wav(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    """Save float32 mono samples as 16-bit PCM WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class ControlButton:
    def __init__(self, rect: pygame.Rect, label: str, action: str):
        self.rect = rect
        self.label = label
        self.action = action


class SharedAudioEngine:
    """
    محرك صوت موحّد: قناة ميكروفون واحدة تغذّي المحلل والمسجّل معاً.
    """

    def __init__(self, sample_rate: int, block_size: int, channels: int):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.channels = channels
        self._viz_buffer = deque(maxlen=4)
        self._record_chunks: list[np.ndarray] = []
        self._viz_lock = threading.Lock()
        self._record_lock = threading.Lock()
        self.is_recording = False
        self._stream = None

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"[تحذير صوتي] {status}", file=sys.stderr)
        mono = indata[:, 0].copy() if indata.ndim > 1 else indata.copy()
        with self._viz_lock:
            self._viz_buffer.append(mono)
        if self.is_recording:
            with self._record_lock:
                self._record_chunks.append(mono)

    def start(self):
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            channels=self.channels,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_latest(self) -> np.ndarray | None:
        with self._viz_lock:
            if not self._viz_buffer:
                return None
            return self._viz_buffer[-1]

    def start_recording(self):
        with self._record_lock:
            self._record_chunks.clear()
        self.is_recording = True

    def stop_recording(self) -> np.ndarray | None:
        self.is_recording = False
        with self._record_lock:
            if not self._record_chunks:
                return None
            return np.concatenate(self._record_chunks)


class SoundWaveApp:
    """التطبيق الموحّد: محلل ذبذبات + مسجّل صوت."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("SoundWave Studio")
        set_app_icon()

        self.fullscreen = False
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()

        self.font_title = pygame.font.Font(None, 42)
        self.font_btn = pygame.font.Font(None, 22)
        self.font_info = pygame.font.Font(None, 20)
        self.font_meter = pygame.font.Font(None, 16)
        self.font_big = pygame.font.Font(None, 64)

        self.app_mode = APP_VISUALIZER
        self.display_mode = MODE_BLOCKS
        self.gain = GAIN_DEFAULT

        self.tab_buttons: list[ControlButton] = []
        self.control_buttons: list[ControlButton] = []

        self._recalc_layout(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.band_weights = build_band_weights(NUM_COLUMNS, BLOCK_SAMPLES, SAMPLE_RATE)

        self.levels = np.zeros(NUM_COLUMNS, dtype=np.float32)
        self.meter_level = 0.0
        self.meter_peak = 0.0

        self.audio = SharedAudioEngine(SAMPLE_RATE, BLOCK_SAMPLES, CHANNELS)
        self.audio.start()

        self.record_start_time: float | None = None
        self.last_saved_path: Path | None = None
        self.status_message = ""
        self.status_until = 0.0

    def _recalc_layout(self, width: int, height: int):
        self.window_width = width
        self.window_height = height

        panel_h = 0 if self.fullscreen else CONTROL_PANEL_HEIGHT
        self.viz_height = height - panel_h
        self.panel_rect = pygame.Rect(0, self.viz_height, width, panel_h)

        meter_w = METER_WIDTH_FULLSCREEN if self.fullscreen else METER_WIDTH
        self.viz_content_width = width - meter_w
        margin = 4 if self.fullscreen else 12
        avail_w = max(100, self.viz_content_width - margin * 2)
        avail_h = max(100, self.viz_height - margin * 2)

        if self.fullscreen:
            col_gap = max(2, avail_w // (NUM_COLUMNS * 10))
            block_size = max(4, (avail_w - (NUM_COLUMNS - 1) * col_gap) // NUM_COLUMNS)
            row_gap = max(1, block_size // 6)
        else:
            col_gap = COLUMN_GAP
            block_size = BLOCK_SIZE
            row_gap = BLOCK_GAP

        self.render_block_size = block_size
        self.render_col_gap = col_gap
        self.render_row_gap = row_gap
        self.max_blocks = max(1, avail_h // (block_size + row_gap))
        self.grid_width = NUM_COLUMNS * block_size + (NUM_COLUMNS - 1) * col_gap
        self.grid_height = self.max_blocks * block_size + (self.max_blocks - 1) * row_gap
        self.offset_x = margin + max(0, (self.viz_content_width - self.grid_width) // 2)
        self.offset_y = margin + max(0, (self.viz_height - self.grid_height) // 2)
        self.row_height = block_size + row_gap

        self.meter_rect = pygame.Rect(
            self.viz_content_width + 2,
            margin,
            meter_w - 4,
            self.viz_height - margin * 2,
        )
        label_col_w = 34 if self.fullscreen else 30
        self.meter_bar_rect = pygame.Rect(
            self.meter_rect.x + label_col_w,
            self.meter_rect.y + 30,
            20,
            self.meter_rect.height - 52,
        )

        if not self.fullscreen:
            self._layout_control_buttons()

    def _layout_control_buttons(self):
        margin = 8
        gap = 6
        panel_w = self.window_width

        tab_w = 130
        tab_h = 26
        self.tab_buttons = [
            ControlButton(pygame.Rect(margin, 6, tab_w, tab_h), "Visualizer", "tab_visualizer"),
            ControlButton(
                pygame.Rect(margin + tab_w + gap, 6, tab_w, tab_h),
                "Recorder",
                "tab_recorder",
            ),
        ]

        btn_y = 38
        btn_h = CONTROL_PANEL_HEIGHT - btn_y - 8

        if self.app_mode == APP_VISUALIZER:
            specs = [
                ("Mode [M]", "toggle_mode"),
                ("Gain -", "gain_down"),
                ("Gain +", "gain_up"),
                ("Record [R]", "toggle_record"),
                ("Full [F]", "fullscreen"),
                ("Exit", "quit"),
            ]
        else:
            specs = [
                ("Record [R]", "toggle_record"),
                ("Folder", "open_folder"),
                ("Visualizer", "tab_visualizer"),
                ("Full [F]", "fullscreen"),
                ("Exit", "quit"),
            ]

        btn_count = len(specs)
        btn_w = max(60, (panel_w - margin * 2 - gap * (btn_count - 1)) // btn_count)
        self.control_buttons = []
        x = margin
        for label, action in specs:
            rect = pygame.Rect(x, btn_y, btn_w, btn_h)
            self.control_buttons.append(ControlButton(rect, label, action))
            x += btn_w + gap

        self.panel_surface = pygame.Surface((panel_w, CONTROL_PANEL_HEIGHT))

    def _set_app_mode(self, mode: str):
        if mode not in (APP_VISUALIZER, APP_RECORDER):
            return
        self.app_mode = mode
        if not self.fullscreen:
            self._layout_control_buttons()

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            info = pygame.display.Info()
            self.screen = pygame.display.set_mode(
                (info.current_w, info.current_h), pygame.FULLSCREEN
            )
            self._recalc_layout(info.current_w, info.current_h)
        else:
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
            self._recalc_layout(WINDOW_WIDTH, WINDOW_HEIGHT)

    def _set_status(self, message: str, duration: float = 4.0):
        self.status_message = message
        self.status_until = time.time() + duration

    def _toggle_recording(self):
        if self.audio.is_recording:
            samples = self.audio.stop_recording()
            self.record_start_time = None
            if samples is None or len(samples) == 0:
                self._set_status("التسجيل فارغ — لم يُحفظ شيء")
                return
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = RECORDINGS_DIR / f"recording_{timestamp}.wav"
            try:
                save_wav(path, samples, SAMPLE_RATE)
                self.last_saved_path = path
                duration = len(samples) / SAMPLE_RATE
                self._set_status(
                    f"تم الحفظ: {path.name} ({format_duration(duration)})",
                    duration=6.0,
                )
            except OSError as exc:
                self._set_status(f"فشل الحفظ: {exc}")
        else:
            self.audio.start_recording()
            self.record_start_time = time.time()
            self._set_status("جاري التسجيل...", duration=2.0)

    def _open_recordings_folder(self):
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(RECORDINGS_DIR))
        except OSError:
            subprocess.Popen(["explorer", str(RECORDINGS_DIR)])

    def _recording_duration(self) -> float:
        if not self.audio.is_recording or self.record_start_time is None:
            return 0.0
        return time.time() - self.record_start_time

    def _process_audio(self):
        samples = self.audio.get_latest()
        if samples is None:
            return

        window = np.hanning(len(samples))
        windowed = samples * window
        spectrum = np.abs(np.fft.rfft(windowed))
        spectrum *= self.gain

        band_energies = self.band_weights @ spectrum
        band_energies = np.log1p(band_energies)
        if band_energies.max() > 0:
            targets = band_energies / band_energies.max()
            targets = np.power(targets, PEAK_COMPRESSION)
            targets *= PEAK_CEILING
        else:
            targets = np.zeros_like(band_energies)

        for i in range(NUM_COLUMNS):
            if targets[i] > self.levels[i]:
                self.levels[i] += (targets[i] - self.levels[i]) * RISE_SPEED
            else:
                self.levels[i] += (targets[i] - self.levels[i]) * FALL_SPEED

        self.levels = np.clip(self.levels, 0.0, 1.0)

        rms = float(np.sqrt(np.mean(samples ** 2))) * self.gain
        meter_target = float(np.clip(rms / METER_RMS_TARGET, 0.0, 1.0))
        if meter_target > self.meter_level:
            self.meter_level += (meter_target - self.meter_level) * RISE_SPEED
        else:
            self.meter_level += (meter_target - self.meter_level) * FALL_SPEED

        if self.meter_level >= self.meter_peak:
            self.meter_peak = self.meter_level
        else:
            self.meter_peak = max(self.meter_level, self.meter_peak - METER_PEAK_FALL)

    def _column_x_positions(self) -> np.ndarray:
        step = self.render_block_size + self.render_col_gap
        return self.offset_x + np.arange(NUM_COLUMNS) * step + self.render_block_size / 2.0

    def _build_smooth_wave_points(self) -> tuple[np.ndarray, np.ndarray, float]:
        xs = self._column_x_positions()
        center_y = self.offset_y + self.grid_height / 2.0
        amplitude = self.grid_height / 2.0
        ys = center_y - self.levels * amplitude
        smooth_pts = max(WAVE_SMOOTH_POINTS, int(self.viz_content_width * 0.6))
        x_smooth = np.linspace(xs[0], xs[-1], smooth_pts)
        y_smooth = np.interp(x_smooth, xs, ys)
        return x_smooth, y_smooth, center_y

    def _draw_blocks(self):
        bs = self.render_block_size
        col_step = bs + self.render_col_gap
        for col in range(NUM_COLUMNS):
            active_blocks = int(self.levels[col] * self.max_blocks)
            x = self.offset_x + col * col_step
            for row in range(self.max_blocks):
                block_index = self.max_blocks - 1 - row
                y = self.offset_y + row * self.row_height
                if block_index < active_blocks:
                    height_ratio = block_index / max(1, self.max_blocks - 1)
                    color = lerp_color(height_ratio)
                else:
                    color = (15, 15, 15)
                pygame.draw.rect(self.screen, color, pygame.Rect(x, y, bs, bs))

    def _draw_waves(self):
        x_smooth, y_upper, center_y = self._build_smooth_wave_points()
        y_lower = center_y + (center_y - y_upper)
        amplitude = self.grid_height / 2.0

        pygame.draw.line(
            self.screen,
            (25, 25, 25),
            (int(x_smooth[0]), int(center_y)),
            (int(x_smooth[-1]), int(center_y)),
            1,
        )

        for i in range(len(x_smooth) - 1):
            x0, x1 = int(x_smooth[i]), int(x_smooth[i + 1])
            if x1 <= x0:
                continue
            top_y0, top_y1 = y_upper[i], y_upper[i + 1]
            bot_y0, bot_y1 = y_lower[i], y_lower[i + 1]
            height_ratio = np.clip(
                (center_y - (top_y0 + top_y1) / 2.0) / max(amplitude, 1.0), 0.0, 1.0
            )
            color = lerp_color(height_ratio)
            polygon = [
                (x0, int(top_y0)),
                (x1, int(top_y1)),
                (x1, int(bot_y1)),
                (x0, int(bot_y0)),
            ]
            pygame.draw.polygon(self.screen, color, polygon)

        upper_points = [(int(x), int(y)) for x, y in zip(x_smooth, y_upper)]
        lower_points = [(int(x), int(y)) for x, y in zip(x_smooth, y_lower)]
        pygame.draw.aalines(self.screen, (255, 255, 255), False, upper_points, WAVE_LINE_WIDTH)
        pygame.draw.aalines(self.screen, (255, 255, 255), False, lower_points, WAVE_LINE_WIDTH)

    def _draw_level_meter(self):
        rect = self.meter_rect
        bar = self.meter_bar_rect

        pygame.draw.rect(self.screen, (16, 16, 16), rect)
        pygame.draw.rect(self.screen, PANEL_BORDER, rect, 1)
        pygame.draw.line(
            self.screen,
            PANEL_BORDER,
            (self.viz_content_width, 0),
            (self.viz_content_width, self.viz_height),
            2,
        )

        title = self.font_info.render(f"LEVEL ({METER_UNIT})", True, TEXT_DIM)
        scale_hint = self.font_meter.render(f"0 - {METER_SCALE_MAX}", True, TEXT_KEY)
        self.screen.blit(title, (rect.centerx - title.get_width() // 2, rect.y + 4))
        self.screen.blit(scale_hint, (rect.centerx - scale_hint.get_width() // 2, rect.y + 16))

        pygame.draw.rect(self.screen, (10, 10, 10), bar)
        pygame.draw.rect(self.screen, (55, 55, 55), bar, 1)

        fill_h = int(bar.height * self.meter_level)
        for i in range(fill_h):
            y = bar.bottom - 1 - i
            ratio = i / max(1, bar.height - 1)
            pygame.draw.line(
                self.screen,
                lerp_color(ratio),
                (bar.x + 1, y),
                (bar.right - 2, y),
            )

        if self.meter_peak > 0.02:
            peak_y = bar.bottom - int(bar.height * self.meter_peak)
            pygame.draw.line(
                self.screen,
                (255, 255, 255),
                (bar.x - 3, peak_y),
                (bar.right + 3, peak_y),
                2,
            )

        label_step = METER_SCALE_STEP if bar.height >= 280 else METER_SCALE_STEP * 2
        for mark in range(0, METER_SCALE_MAX + 1, METER_SCALE_STEP):
            tick_y = bar.bottom - int(bar.height * mark / METER_SCALE_MAX)
            major = mark % label_step == 0
            tick_len = 6 if major else 3
            pygame.draw.line(
                self.screen,
                (90, 90, 90) if major else (55, 55, 55),
                (bar.x - tick_len, tick_y),
                (bar.x - 1, tick_y),
            )
            if major:
                tick_label = self.font_meter.render(str(mark), True, TEXT_DIM)
                self.screen.blit(
                    tick_label,
                    (bar.x - 8 - tick_label.get_width(), tick_y - tick_label.get_height() // 2),
                )

        level_value = int(self.meter_level * METER_SCALE_MAX)
        value = self.font_info.render(f"{level_value} {METER_UNIT}", True, TEXT_MAIN)
        self.screen.blit(value, (rect.centerx - value.get_width() // 2, bar.bottom + 6))

    def _draw_recording_badge(self, x: int, y: int):
        if not self.audio.is_recording:
            return
        pulse = 0.5 + 0.5 * abs(np.sin(time.time() * 4.0))
        dot_color = (int(255 * pulse), int(60 * pulse), int(60 * pulse))
        pygame.draw.circle(self.screen, dot_color, (x + 8, y + 10), 7)
        label = self.font_info.render("REC", True, TEXT_RECORD)
        self.screen.blit(label, (x + 20, y + 2))

    def _draw_recorder_view(self):
        cx = self.viz_content_width // 2
        cy = self.viz_height // 2

        title = self.font_title.render("Audio Recorder", True, TEXT_MAIN)
        self.screen.blit(title, (cx - title.get_width() // 2, cy - 160))

        if self.audio.is_recording:
            timer_text = format_duration(self._recording_duration())
            timer_color = TEXT_RECORD
            status = "Recording..."
        else:
            timer_text = "00:00"
            timer_color = TEXT_DIM
            status = "Ready — press Record or [R]"

        timer = self.font_big.render(timer_text, True, timer_color)
        self.screen.blit(timer, (cx - timer.get_width() // 2, cy - 70))

        status_surf = self.font_info.render(status, True, TEXT_DIM)
        self.screen.blit(status_surf, (cx - status_surf.get_width() // 2, cy + 10))

        btn_radius = 48
        btn_color = (200, 50, 50) if self.audio.is_recording else (180, 40, 40)
        pygame.draw.circle(self.screen, btn_color, (cx, cy + 80), btn_radius)
        pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy + 80), btn_radius, 3)
        inner_label = "STOP" if self.audio.is_recording else "REC"
        inner = self.font_btn.render(inner_label, True, TEXT_MAIN)
        self.screen.blit(inner, (cx - inner.get_width() // 2, cy + 80 - inner.get_height() // 2))

        hint = self.font_info.render(
            "Files saved to ./recordings/  |  [R] toggle  |  Tab: switch view",
            True,
            TEXT_KEY,
        )
        self.screen.blit(hint, (cx - hint.get_width() // 2, cy + 155))

        if self.last_saved_path is not None:
            saved = self.font_info.render(f"Last: {self.last_saved_path.name}", True, TEXT_OK)
            self.screen.blit(saved, (cx - saved.get_width() // 2, cy + 180))

        if self.status_message and time.time() < self.status_until:
            msg = self.font_info.render(self.status_message, True, TEXT_OK)
            self.screen.blit(msg, (cx - msg.get_width() // 2, 24))

        self._draw_recording_badge(16, 12)

    def _draw_visualizer_view(self):
        if self.display_mode == MODE_BLOCKS:
            self._draw_blocks()
        else:
            self._draw_waves()
        self._draw_level_meter()
        self._draw_recording_badge(16, 12)

        if self.status_message and time.time() < self.status_until:
            msg = self.font_info.render(self.status_message, True, TEXT_OK)
            self.screen.blit(msg, (16, 36))

    def _draw_button(
        self,
        surface: pygame.Surface,
        button: ControlButton,
        mouse_pos: tuple[int, int],
        active: bool = False,
    ):
        base = BTN_COLORS.get(button.action, (60, 60, 60))
        hovered = button.rect.collidepoint(mouse_pos)
        boost = BTN_ACTIVE_BOOST if active else (BTN_HOVER_BOOST if hovered else 0)
        color = tuple(min(255, c + boost) for c in base)

        pygame.draw.rect(surface, color, button.rect)
        border = (255, 220, 120) if active else (220, 220, 220)
        pygame.draw.rect(surface, border, button.rect, 2)

        text = self.font_btn.render(button.label, True, TEXT_MAIN)
        tx = button.rect.centerx - text.get_width() // 2
        ty = button.rect.centery - text.get_height() // 2
        surface.blit(text, (tx, ty))

    def _draw_control_panel(self):
        self.panel_surface.fill(PANEL_BG)
        pygame.draw.line(self.panel_surface, PANEL_BORDER, (0, 0), (self.window_width, 0), 2)

        mouse_x, mouse_y = pygame.mouse.get_pos()
        local_mouse = (mouse_x, mouse_y - self.panel_rect.y)

        for tab in self.tab_buttons:
            self._draw_button(
                self.panel_surface,
                tab,
                local_mouse,
                active=(tab.action == f"tab_{self.app_mode}"),
            )

        mode_label = "Blocks" if self.display_mode == MODE_BLOCKS else "Waves"
        app_label = "Visualizer" if self.app_mode == APP_VISUALIZER else "Recorder"
        info_left = self.font_info.render(f"App: {app_label}  |  View: {mode_label}", True, TEXT_DIM)
        rec_info = ""
        if self.audio.is_recording:
            rec_info = f"  |  REC {format_duration(self._recording_duration())}"
        info_right = self.font_info.render(
            f"Gain: {self.gain:.2f}{rec_info}  |  Scale: 0-{METER_SCALE_MAX} {METER_UNIT}",
            True,
            TEXT_MAIN,
        )
        self.panel_surface.blit(info_left, (280, 10))
        self.panel_surface.blit(
            info_right,
            (self.window_width - info_right.get_width() - 12, 10),
        )

        for button in self.control_buttons:
            active = button.action == "toggle_record" and self.audio.is_recording
            self._draw_button(self.panel_surface, button, local_mouse, active=active)

        self.screen.blit(self.panel_surface, (0, self.panel_rect.y))

    def _handle_panel_click(self, pos: tuple[int, int]) -> bool:
        if not self.panel_rect.collidepoint(pos):
            return True

        local_pos = (pos[0], pos[1] - self.panel_rect.y)
        for tab in self.tab_buttons:
            if tab.rect.collidepoint(local_pos):
                self._set_app_mode(APP_VISUALIZER if tab.action == "tab_visualizer" else APP_RECORDER)
                return True

        for button in self.control_buttons:
            if button.rect.collidepoint(local_pos):
                return self._run_control_action(button.action)
        return True

    def _handle_recorder_click(self, pos: tuple[int, int]) -> bool:
        if self.app_mode != APP_RECORDER:
            return True
        cx = self.viz_content_width // 2
        cy = self.viz_height // 2 + 80
        if (pos[0] - cx) ** 2 + (pos[1] - cy) ** 2 <= 48 ** 2:
            self._toggle_recording()
        return True

    def _draw(self):
        viz_rect = pygame.Rect(0, 0, self.window_width, self.viz_height)
        self.screen.fill(BG_COLOR)
        self.screen.set_clip(viz_rect)

        if self.app_mode == APP_VISUALIZER:
            self._draw_visualizer_view()
        else:
            self._draw_recorder_view()
            self._draw_level_meter()

        self.screen.set_clip(None)

        if self.fullscreen:
            hint = self.font_info.render(
                "ESC: exit  |  Tab: mode  |  R: record  |  M: view  |  +/-: gain",
                True,
                TEXT_DIM,
            )
            self.screen.blit(hint, (10, 8))

        if not self.fullscreen:
            self._draw_control_panel()

        pygame.display.flip()

    def _run_control_action(self, action: str) -> bool:
        if action == "tab_visualizer":
            self._set_app_mode(APP_VISUALIZER)
        elif action == "tab_recorder":
            self._set_app_mode(APP_RECORDER)
        elif action == "toggle_mode":
            self.display_mode = (
                MODE_WAVES if self.display_mode == MODE_BLOCKS else MODE_BLOCKS
            )
        elif action == "gain_up":
            self.gain = min(GAIN_MAX, self.gain + GAIN_STEP)
        elif action == "gain_down":
            self.gain = max(GAIN_MIN, self.gain - GAIN_STEP)
        elif action == "toggle_record":
            self._toggle_recording()
        elif action == "open_folder":
            self._open_recordings_folder()
        elif action == "fullscreen":
            self._toggle_fullscreen()
        elif action == "quit":
            if self.fullscreen:
                self._toggle_fullscreen()
            else:
                return False
        return True

    def _handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self._handle_panel_click(event.pos):
                    return False
                self._handle_recorder_click(event.pos)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if not self._run_control_action("quit"):
                        return False
                elif event.key == pygame.K_f:
                    self._run_control_action("fullscreen")
                elif event.key == pygame.K_m:
                    if self.app_mode == APP_VISUALIZER:
                        self._run_control_action("toggle_mode")
                elif event.key == pygame.K_r:
                    self._toggle_recording()
                elif event.key == pygame.K_TAB:
                    self._set_app_mode(
                        APP_RECORDER if self.app_mode == APP_VISUALIZER else APP_VISUALIZER
                    )
                elif event.key == pygame.K_1:
                    self._set_app_mode(APP_VISUALIZER)
                elif event.key == pygame.K_2:
                    self._set_app_mode(APP_RECORDER)
                elif event.key in (pygame.K_UP, pygame.K_PLUS, pygame.K_EQUALS):
                    self._run_control_action("gain_up")
                elif event.key in (pygame.K_DOWN, pygame.K_MINUS):
                    self._run_control_action("gain_down")

        return True

    def run(self):
        running = True
        try:
            while running:
                running = self._handle_events()
                self._process_audio()
                self._draw()
                self.clock.tick(FPS)
        finally:
            if self.audio.is_recording:
                self.audio.stop_recording()
            self.audio.stop()
            pygame.quit()


def main():
    try:
        app = SoundWaveApp()
        app.run()
    except Exception as exc:
        import traceback

        error_text = traceback.format_exc()
        log_path = Path.home() / "soundwave_studio_error.log"
        log_path.write_text(error_text, encoding="utf-8")

        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0,
                f"{exc}\n\nDetails saved to:\n{log_path}",
                "SoundWave Studio Error",
                0x10,
            )
        except Exception:
            print(error_text, file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
