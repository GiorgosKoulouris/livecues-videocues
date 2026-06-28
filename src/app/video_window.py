"""Full-screen video output window for the projector / second display.

Plays a looping idle video when nothing is triggered; a Note-On swaps in the
mapped clip (interrupting whatever is playing), plays it once, then returns to
idle on end-of-media. A black overlay implements blackout.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QLabel, QWidget

_INFINITE = QMediaPlayer.Loops.Infinite
_ONCE = QMediaPlayer.Loops.Once

# View-transform limits / steps (zoom is multiplicative, pan/crop are a fraction
# of the window size per step).
_ZOOM_MIN = 0.2
_ZOOM_MAX = 5.0
_OFFSET_LIMIT = 2.0
# Per-click Zoom increment, as a fraction (0.10 = ±10% per click). The default
# matches the old fixed 1.1× factor; the user can change it from the Status page.
_ZOOM_STEP_DEFAULT = 0.10
_ZOOM_STEP_MIN = 0.01
_ZOOM_STEP_MAX = 1.0
_CROP_STEP = 0.05
_CROP_MAX = 0.9  # never crop a side away entirely
# Per-click Move (pan) increment, as a fraction of the window size. The default
# is intentionally fine; the user can change it from the Status page.
_MOVE_STEP_DEFAULT = 0.02
_MOVE_STEP_MIN = 0.005
_MOVE_STEP_MAX = 0.5


class VideoWindow(QWidget):
    """Output surface that can be parked on any screen, fullscreen or windowed.

    Fullscreen (via ``showFullScreen``) hides the window decorations on its own,
    so the window keeps a normal frame the rest of the time and stays resizable
    and movable when toggled out of fullscreen.
    """

    now_playing_changed = Signal(str)  # "Idle", a clip name, or "Blackout"
    view_changed = Signal(dict)        # zoom / offset_* / crop_* (see _view_dict)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Video Cues — Output")
        self.setStyleSheet("background-color: black;")
        self.resize(960, 540)

        self._screen_index = 0
        self._idle_path: Optional[Path] = None
        self._playing_clip = False
        self._blacked_out = False

        # Output placement of the video within the window (projector alignment).
        self._zoom = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._crop_left = 0.0
        self._crop_right = 0.0
        self._crop_top = 0.0
        self._crop_bottom = 0.0
        self._move_step = _MOVE_STEP_DEFAULT
        self._zoom_step = _ZOOM_STEP_DEFAULT

        self._audio = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio)

        # The video widget is positioned manually (see _apply_geometry) so it can
        # be zoomed/panned/cropped; it's clipped to the window. The expanding
        # aspect mode makes the video *fill* the widget (cover) instead of
        # letterboxing, so the default view leaves no black bars.
        self._video = QVideoWidget(self)
        self._video.setStyleSheet("background-color: black;")
        self._video.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        self._player.setVideoOutput(self._video)

        # Black overlay shown on top for blackout / when no idle video is set;
        # always covers the whole window regardless of the video transform.
        self._black = QLabel(self)
        self._black.setStyleSheet("background-color: black;")
        self._black.raise_()
        self._black.hide()

        self._player.mediaStatusChanged.connect(self._on_media_status)

    # ----- configuration -----------------------------------------------
    def configure(self, idle_path: Optional[Path], muted: bool) -> None:
        self._audio.setMuted(muted)
        new_idle = idle_path if (idle_path and idle_path.exists()) else None
        idle_changed = new_idle != self._idle_path
        self._idle_path = new_idle
        # Refresh idle playback if we're currently idle (or have nothing playing).
        if not self._playing_clip and not self._blacked_out:
            if idle_changed or self._player.source().isEmpty():
                self.play_idle()

    def set_muted(self, muted: bool) -> None:
        self._audio.setMuted(muted)

    # ----- screen placement --------------------------------------------
    def show_on_screen(self, index: int) -> None:
        """Remember the target display and (re)show on it.

        Opens windowed by default; if already fullscreen (e.g. the user changes
        the output display while fullscreen), it stays fullscreen.
        """
        self._screen_index = index
        if self.isFullScreen():
            self._show_fullscreen()
        else:
            self._show_windowed()

    def _target_screen(self):
        screens = QGuiApplication.screens()
        if not screens:
            return None
        index = max(0, min(self._screen_index, len(screens) - 1))
        return screens[index]

    def _show_fullscreen(self) -> None:
        screen = self._target_screen()
        if screen is None:
            self.showFullScreen()
            return
        self.setGeometry(screen.geometry())
        # Ensure the native window is associated with the target screen before
        # going fullscreen, otherwise it may fullscreen on the primary display.
        handle = self.windowHandle()
        if handle is not None:
            handle.setScreen(screen)
        self.showFullScreen()

    def _show_windowed(self) -> None:
        """Leave fullscreen and show a centered, resizable window."""
        self.showNormal()
        screen = self._target_screen()
        if screen is not None:
            avail = screen.availableGeometry()
            w = int(avail.width() * 0.6)
            h = int(avail.height() * 0.6)
            x = avail.x() + (avail.width() - w) // 2
            y = avail.y() + (avail.height() - h) // 2
            self.setGeometry(x, y, w, h)
        self.raise_()
        self.activateWindow()

    # ----- video transform (zoom / pan / crop) -------------------------
    def zoom_in(self) -> None:
        self._update(zoom=self._zoom * (1.0 + self._zoom_step))

    def zoom_out(self) -> None:
        self._update(zoom=self._zoom / (1.0 + self._zoom_step))

    def set_zoom_step(self, value: float) -> None:
        """Set the per-click Zoom increment (fraction, e.g. 0.10 = ±10%)."""
        self._zoom_step = _clamp(value, _ZOOM_STEP_MIN, _ZOOM_STEP_MAX)

    def pan(self, dx: float, dy: float) -> None:
        """Nudge the video by ``dx``/``dy`` steps (negative = left / up)."""
        self._update(
            offset_x=self._offset_x + dx * self._move_step,
            offset_y=self._offset_y + dy * self._move_step,
        )

    def set_move_step(self, value: float) -> None:
        """Set the per-click Move increment (fraction of window size)."""
        self._move_step = _clamp(value, _MOVE_STEP_MIN, _MOVE_STEP_MAX)

    def crop(self, side: str, sign: int) -> None:
        """Crop (``sign`` > 0) or uncrop (``sign`` < 0) one edge of the video.

        ``side`` is one of ``"left"``, ``"right"``, ``"top"``, ``"bottom"``.
        """
        delta = sign * _CROP_STEP
        attr = {
            "left": "crop_left",
            "right": "crop_right",
            "top": "crop_top",
            "bottom": "crop_bottom",
        }.get(side)
        if attr is None:
            return
        current = getattr(self, f"_{attr}")
        self._update(**{attr: current + delta})

    def reset_view(self) -> None:
        self._update(
            zoom=1.0, offset_x=0.0, offset_y=0.0,
            crop_left=0.0, crop_right=0.0, crop_top=0.0, crop_bottom=0.0,
        )

    def apply_view(self, view: dict) -> None:
        """Apply a saved transform without re-emitting :pyattr:`view_changed`."""
        self._update(emit=False, **{k: view[k] for k in self._view_dict() if k in view})

    def _update(self, *, emit: bool = True, **values) -> None:
        """Set any subset of transform fields (clamped), re-layout, and persist."""
        if "zoom" in values:
            self._zoom = _clamp(values["zoom"], _ZOOM_MIN, _ZOOM_MAX)
        if "offset_x" in values:
            self._offset_x = _clamp(values["offset_x"], -_OFFSET_LIMIT, _OFFSET_LIMIT)
        if "offset_y" in values:
            self._offset_y = _clamp(values["offset_y"], -_OFFSET_LIMIT, _OFFSET_LIMIT)
        for side in ("left", "right", "top", "bottom"):
            key = f"crop_{side}"
            if key in values:
                setattr(self, f"_{key}", _clamp(values[key], 0.0, _CROP_MAX))
        self._apply_geometry()
        if emit:
            self.view_changed.emit(self._view_dict())

    def _view_dict(self) -> dict:
        return {
            "zoom": self._zoom,
            "offset_x": self._offset_x,
            "offset_y": self._offset_y,
            "crop_left": self._crop_left,
            "crop_right": self._crop_right,
            "crop_top": self._crop_top,
            "crop_bottom": self._crop_bottom,
        }

    def _apply_geometry(self) -> None:
        w, h = self.width(), self.height()
        self._black.setGeometry(0, 0, w, h)
        # Per-side crop extends the video rect beyond that window edge so the
        # window clips it away; the opposite edge still reaches the window, so
        # the output stays fully covered (no black gap).
        left = -self._crop_left * w
        right = w + self._crop_right * w
        top = -self._crop_top * h
        bottom = h + self._crop_bottom * h
        # Zoom about the cropped rect's centre, then apply the pan offset.
        cx, cy = (left + right) / 2, (top + bottom) / 2
        vw = max(1, round((right - left) * self._zoom))
        vh = max(1, round((bottom - top) * self._zoom))
        x = round(cx - vw / 2 + self._offset_x * w)
        y = round(cy - vh / 2 + self._offset_y * h)
        self._video.setGeometry(x, y, vw, vh)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        self._apply_geometry()

    # ----- playback -----------------------------------------------------
    def play_idle(self) -> None:
        self._playing_clip = False
        if self._idle_path is not None:
            self._black.hide()
            self._player.setLoops(_INFINITE)
            self._player.setSource(QUrl.fromLocalFile(str(self._idle_path)))
            self._player.play()
            self.now_playing_changed.emit(f"Idle: {self._idle_path.name}")
        else:
            # No idle video configured -> show a plain black screen.
            self._player.stop()
            self._black.show()
            self._black.raise_()
            self.now_playing_changed.emit("Idle (black)")

    def trigger(self, clip_path: Path) -> None:
        """Interrupt whatever is playing and play ``clip_path`` once."""
        if not clip_path or not Path(clip_path).exists():
            self.now_playing_changed.emit(f"Missing file: {clip_path}")
            return
        self._blacked_out = False
        self._black.hide()
        self._playing_clip = True
        self._player.setLoops(_ONCE)
        self._player.setSource(QUrl.fromLocalFile(str(clip_path)))
        self._player.play()
        self.now_playing_changed.emit(f"Playing: {Path(clip_path).name}")

    def blackout(self, on: Optional[bool] = None) -> bool:
        """Toggle (or set) blackout. Returns the new blackout state."""
        self._blacked_out = (not self._blacked_out) if on is None else bool(on)
        if self._blacked_out:
            self._player.pause()
            self._black.show()
            self._black.raise_()
            self.now_playing_changed.emit("Blackout")
        else:
            self._black.hide()
            self.play_idle()
        return self._blacked_out

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self._show_windowed()
        else:
            self._show_fullscreen()

    # ----- internal -----------------------------------------------------
    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        # A one-shot clip finished -> fall back to the looping idle video.
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self._playing_clip:
            self.play_idle()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._player.stop()
        super().closeEvent(event)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))
