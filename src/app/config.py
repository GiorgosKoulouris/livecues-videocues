"""Persistent configuration.

Stored as JSON under :func:`app.paths.config_file`. The schema is intentionally
forgiving: unknown keys are ignored and missing keys fall back to defaults, so a
config written by an older build still loads.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Optional

from . import paths

# midi_channel == 0 means "listen on every channel"; 1..16 select one.
ALL_CHANNELS = 0


@dataclass
class Config:
    video_root: str = ""
    idle_video: str = ""               # relative to video_root (or absolute)
    midi_device: str = ""              # MIDI input port name as reported by mido
    midi_channel: int = ALL_CHANNELS   # 0 = all, 1..16
    output_screen: int = 0             # index into QGuiApplication.screens()
    audio_muted: bool = True
    # Output window placement, remembered across restarts. Width/height 0 means
    # "never saved" -> the window opens centered at a default size. The windowed
    # rect is kept even while fullscreen, so leaving fullscreen restores the
    # aligned window instead of re-centering it.
    window_x: int = 0
    window_y: int = 0
    window_width: int = 0
    window_height: int = 0
    output_fullscreen: bool = False
    # Output video placement (lets you align onto a projector). The video fills
    # the window by default (no black bars); these refine that placement:
    video_zoom: float = 1.0            # 1.0 = fill window; >1 zooms in further
    video_offset_x: float = 0.0        # pan, as a fraction of window width
    video_offset_y: float = 0.0        # pan, as a fraction of window height
    # Per-side crop, each a fraction of the window cut off that edge (0..1):
    video_crop_left: float = 0.0
    video_crop_right: float = 0.0
    video_crop_top: float = 0.0
    video_crop_bottom: float = 0.0
    # How far each Move (pan) click nudges the video, as a fraction of the
    # window size. User-configurable from the Status page.
    move_step: float = 0.02
    # How much each Zoom click scales the video, as a fraction (0.10 = ±10% per
    # click). User-configurable from the Status page.
    zoom_step: float = 0.10
    # note number (as string key in JSON) -> path relative to video_root
    mappings: Dict[int, str] = field(default_factory=dict)

    # ----- construction -------------------------------------------------
    @classmethod
    def default(cls) -> "Config":
        return cls()

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        base = cls()
        if not isinstance(data, dict):
            return base
        raw_maps = data.get("mappings", {}) or {}
        mappings: Dict[int, str] = {}
        if isinstance(raw_maps, dict):
            for k, v in raw_maps.items():
                try:
                    note = int(k)
                except (TypeError, ValueError):
                    continue
                if 0 <= note <= 127 and isinstance(v, str) and v.strip():
                    mappings[note] = v
        return cls(
            video_root=str(data.get("video_root", base.video_root)),
            idle_video=str(data.get("idle_video", base.idle_video)),
            midi_device=str(data.get("midi_device", base.midi_device)),
            midi_channel=_coerce_channel(data.get("midi_channel", base.midi_channel)),
            output_screen=_coerce_int(data.get("output_screen", base.output_screen), 0),
            audio_muted=bool(data.get("audio_muted", base.audio_muted)),
            window_x=_coerce_int(data.get("window_x", base.window_x), base.window_x),
            window_y=_coerce_int(data.get("window_y", base.window_y), base.window_y),
            window_width=_coerce_int(data.get("window_width", base.window_width), base.window_width),
            window_height=_coerce_int(data.get("window_height", base.window_height), base.window_height),
            output_fullscreen=bool(data.get("output_fullscreen", base.output_fullscreen)),
            video_zoom=_coerce_float(data.get("video_zoom", base.video_zoom), base.video_zoom),
            video_offset_x=_coerce_float(data.get("video_offset_x", base.video_offset_x), base.video_offset_x),
            video_offset_y=_coerce_float(data.get("video_offset_y", base.video_offset_y), base.video_offset_y),
            video_crop_left=_coerce_float(data.get("video_crop_left", base.video_crop_left), base.video_crop_left),
            video_crop_right=_coerce_float(data.get("video_crop_right", base.video_crop_right), base.video_crop_right),
            video_crop_top=_coerce_float(data.get("video_crop_top", base.video_crop_top), base.video_crop_top),
            video_crop_bottom=_coerce_float(data.get("video_crop_bottom", base.video_crop_bottom), base.video_crop_bottom),
            move_step=_coerce_float(data.get("move_step", base.move_step), base.move_step),
            zoom_step=_coerce_float(data.get("zoom_step", base.zoom_step), base.zoom_step),
            mappings=mappings,
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        # JSON object keys must be strings.
        d["mappings"] = {str(k): v for k, v in self.mappings.items()}
        return d

    # ----- persistence --------------------------------------------------
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        path = Path(path) if path else paths.config_file()
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return cls.from_dict(json.load(fh))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return cls.default()

    def save(self, path: Optional[Path] = None) -> None:
        path = Path(path) if path else paths.config_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write atomically so a crash mid-write can't corrupt the config.
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, sort_keys=True)
        tmp.replace(path)

    # ----- helpers ------------------------------------------------------
    def resolve(self, relative_or_abs: str) -> Optional[Path]:
        """Resolve a stored path (relative to video_root, or absolute) to a Path."""
        if not relative_or_abs:
            return None
        p = Path(relative_or_abs)
        if p.is_absolute():
            return p
        if self.video_root:
            return Path(self.video_root) / p
        return p

    def view_dict(self) -> dict:
        """The output-placement transform (zoom / pan / per-side crop)."""
        return {
            "zoom": self.video_zoom,
            "offset_x": self.video_offset_x,
            "offset_y": self.video_offset_y,
            "crop_left": self.video_crop_left,
            "crop_right": self.video_crop_right,
            "crop_top": self.video_crop_top,
            "crop_bottom": self.video_crop_bottom,
        }

    def window_state(self) -> dict:
        """Output-window placement (target display, windowed rect, fullscreen)."""
        return {
            "screen": self.output_screen,
            "x": self.window_x,
            "y": self.window_y,
            "width": self.window_width,
            "height": self.window_height,
            "fullscreen": self.output_fullscreen,
        }

    def apply_window_state(self, state: dict) -> None:
        """Store a placement reported by the output window."""
        self.output_screen = _coerce_int(state.get("screen", self.output_screen), self.output_screen)
        self.window_x = _coerce_int(state.get("x", self.window_x), self.window_x)
        self.window_y = _coerce_int(state.get("y", self.window_y), self.window_y)
        self.window_width = _coerce_int(state.get("width", self.window_width), self.window_width)
        self.window_height = _coerce_int(state.get("height", self.window_height), self.window_height)
        self.output_fullscreen = bool(state.get("fullscreen", self.output_fullscreen))

    def idle_path(self) -> Optional[Path]:
        return self.resolve(self.idle_video) if self.idle_video else None

    def mapping_path(self, note: int) -> Optional[Path]:
        rel = self.mappings.get(note)
        return self.resolve(rel) if rel else None

    def copy(self) -> "Config":
        return Config.from_dict(self.to_dict())


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_channel(value) -> int:
    ch = _coerce_int(value, ALL_CHANNELS)
    return ch if 0 <= ch <= 16 else ALL_CHANNELS
