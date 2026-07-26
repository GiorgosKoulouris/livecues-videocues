"""Full-screen video output window for the projector / second display.

Plays a looping idle video when nothing is triggered; a Note-On swaps in the
mapped clip (interrupting whatever is playing), plays it once, then returns to
idle on end-of-media. :meth:`VideoWindow.return_to_idle` (the Status-page button
and Ctrl+B) drops back to that idle loop at any time. A black overlay stands in
for the idle video when none is configured.

The window's own placement — target display, windowed rect, and fullscreen —
is reported through :pyattr:`window_state_changed` so it can be persisted and
restored on the next run.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QRect, Qt, QTimer, QUrl, Signal
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

# Dragging/resizing emits a burst of move & resize events; wait this long after
# the last one before persisting the new placement.
_GEOMETRY_SAVE_DELAY_MS = 500
# A restored rect must overlap a connected screen by at least this much to be
# usable — otherwise the window would open somewhere the user can't reach it.
_MIN_VISIBLE_W = 120
_MIN_VISIBLE_H = 80


class VideoWindow(QWidget):
    """Output surface that can be parked on any screen, fullscreen or windowed.

    Fullscreen (via ``showFullScreen``) hides the window decorations on its own,
    so the window keeps a normal frame the rest of the time and stays resizable
    and movable when toggled out of fullscreen.
    """

    now_playing_changed = Signal(str)   # "Idle: ...", a clip name, or a problem
    view_changed = Signal(dict)         # zoom / offset_* / crop_* (see _view_dict)
    idle_state_changed = Signal(bool)   # True while the idle loop owns the output
    window_state_changed = Signal(dict) # screen / x / y / width / height / fullscreen

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Video Cues — Output")
        self.setStyleSheet("background-color: black;")
        self.resize(960, 540)

        self._screen_index = 0
        self._idle_path: Optional[Path] = None
        self._playing_clip = False

        # Window placement. ``_windowed_rect`` survives fullscreen so leaving it
        # restores the aligned window; ``_restoring`` suppresses the save that
        # Qt's own move/resize events would otherwise trigger while we position
        # the window ourselves.
        self._windowed_rect: Optional[QRect] = None
        self._fullscreen = False
        self._restoring = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(_GEOMETRY_SAVE_DELAY_MS)
        self._save_timer.timeout.connect(self._emit_window_state)

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

        # Black overlay shown when no idle video is configured; always covers the
        # whole window regardless of the video transform.
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
        if not self._playing_clip:
            if idle_changed or self._player.source().isEmpty():
                self.play_idle()

    def set_muted(self, muted: bool) -> None:
        self._audio.setMuted(muted)

    # ----- screen placement --------------------------------------------
    def show_on_screen(self, index: int) -> None:
        """Move the output to display ``index`` (the Edit-view dropdown).

        The saved windowed rect belongs to the display it was captured on, so
        switching displays re-centers there rather than reusing those
        coordinates. Fullscreen output stays fullscreen on the new display.
        """
        if index == self._screen_index:
            return
        self._screen_index = index
        self._windowed_rect = None
        self._restoring = True
        try:
            if self._fullscreen:
                self._show_fullscreen()
            else:
                self._show_windowed()
        finally:
            self._restoring = False
        self._schedule_state_save()

    def apply_window_state(self, state: dict) -> None:
        """Restore a saved placement (display, windowed rect, fullscreen).

        Falls back to a centered default window when the saved rect no longer
        lands on a connected display — an unplugged projector or a resolution
        change must never strand the output where it can't be reached.
        """
        self._restoring = True
        try:
            self._screen_index = _as_int(state.get("screen"), self._screen_index)
            width = _as_int(state.get("width"), 0)
            height = _as_int(state.get("height"), 0)
            rect = QRect(_as_int(state.get("x"), 0), _as_int(state.get("y"), 0), width, height)
            usable = width > 0 and height > 0 and _rect_is_reachable(rect)
            self._windowed_rect = rect if usable else None
            self._fullscreen = bool(state.get("fullscreen", False))
            if self._fullscreen:
                self._show_fullscreen()
            else:
                self._show_windowed()
        finally:
            self._restoring = False
        if not usable:
            # Persist whatever we fell back to, so the stale rect stops haunting
            # every launch.
            self._schedule_state_save()

    def window_state(self) -> dict:
        rect = self._windowed_rect or self.geometry()
        return {
            "screen": self._screen_index,
            "x": rect.x(),
            "y": rect.y(),
            "width": rect.width(),
            "height": rect.height(),
            "fullscreen": self._fullscreen,
        }

    def _schedule_state_save(self) -> None:
        """Coalesce a burst of move/resize events into a single save."""
        self._save_timer.start()

    def _emit_window_state(self) -> None:
        self.window_state_changed.emit(self.window_state())

    def _current_screen_index(self) -> int:
        """Index of the display the window currently sits on."""
        screen = self.screen()
        screens = QGuiApplication.screens()
        if screen is not None and screen in screens:
            return screens.index(screen)
        return self._screen_index

    def _target_screen(self):
        screens = QGuiApplication.screens()
        if not screens:
            return None
        index = max(0, min(self._screen_index, len(screens) - 1))
        return screens[index]

    def _show_fullscreen(self) -> None:
        self._fullscreen = True
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
        """Leave fullscreen and show the remembered window (or a centered one)."""
        self._fullscreen = False
        self.showNormal()
        rect = self._windowed_rect
        if rect is None:
            rect = self._default_rect()
            self._windowed_rect = rect
        if rect is not None:
            self.setGeometry(rect)
        self.raise_()
        self.activateWindow()

    def _default_rect(self) -> Optional[QRect]:
        """A centered window at 60% of the target display."""
        screen = self._target_screen()
        if screen is None:
            return None
        avail = screen.availableGeometry()
        w = int(avail.width() * 0.6)
        h = int(avail.height() * 0.6)
        x = avail.x() + (avail.width() - w) // 2
        y = avail.y() + (avail.height() - h) // 2
        return QRect(x, y, w, h)

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
        self._remember_placement()

    def moveEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().moveEvent(event)
        self._remember_placement()

    def _remember_placement(self) -> None:
        """Track the user's own moves/resizes, including onto another display."""
        if self._restoring:
            return
        changed = False
        # Never let a fullscreen geometry become the remembered windowed rect —
        # the intent flag is checked too, since it flips before the window state.
        if not (self._fullscreen or self.isFullScreen()):
            rect = self.geometry()
            if rect != self._windowed_rect:
                self._windowed_rect = rect
                changed = True
        index = self._current_screen_index()
        if index != self._screen_index:
            self._screen_index = index
            changed = True
        if changed:
            self._schedule_state_save()

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
        self.idle_state_changed.emit(True)

    def return_to_idle(self) -> None:
        """Drop any triggered clip and go back to the looping idle video.

        A no-op when the idle loop is already playing, so pressing the button
        twice doesn't restart the loop from the top.
        """
        idle_running = (
            not self._playing_clip
            and self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        )
        if not idle_running:
            self.play_idle()

    def trigger(self, clip_path: Path) -> None:
        """Interrupt whatever is playing and play ``clip_path`` once."""
        if not clip_path or not Path(clip_path).exists():
            # Leave the output as it is — the operator sees the problem in the
            # status line rather than losing whatever is on the projector.
            self.now_playing_changed.emit(f"Missing file: {clip_path}")
            return
        # A cue must never land on a closed output window.
        if not self.isVisible():
            self._reopen(resume_idle=False)
        self._black.hide()
        self._playing_clip = True
        self._player.setLoops(_ONCE)
        self._player.setSource(QUrl.fromLocalFile(str(clip_path)))
        self._player.play()
        self.now_playing_changed.emit(f"Playing: {Path(clip_path).name}")
        self.idle_state_changed.emit(False)

    def show_output(self) -> None:
        """(Re)open the output window on its saved display and resume the idle loop.

        Also raises it when it is merely buried behind another window, so the
        Status-page button always brings the output back.
        """
        self._reopen(resume_idle=True)

    def _reopen(self, resume_idle: bool) -> None:
        was_closed = not self.isVisible()
        self._restoring = True
        try:
            if self._fullscreen:
                self._show_fullscreen()
            else:
                self._show_windowed()
        finally:
            self._restoring = False
        if was_closed and resume_idle:
            # Closing stopped playback, so bring the idle loop back with it.
            self.play_idle()

    def toggle_fullscreen(self) -> None:
        # Suppressed while we drive the transition: Qt reports the fullscreen
        # geometry through move/resize events before the window state itself
        # flips, which would otherwise overwrite the windowed rect with it.
        self._restoring = True
        try:
            if self.isFullScreen():
                self._show_windowed()
            else:
                self._show_fullscreen()
        finally:
            self._restoring = False
        self._schedule_state_save()

    # ----- internal -----------------------------------------------------
    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        # A one-shot clip finished -> fall back to the looping idle video.
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self._playing_clip:
            self.play_idle()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self._player.stop()
        # Nothing is on the projector any more: report idle so the Return to Idle
        # button goes red, and forget the clip so reopening resumes the idle loop.
        self._playing_clip = False
        self.idle_state_changed.emit(True)
        self.now_playing_changed.emit("Output window closed")
        # Don't lose a placement change that is still inside the debounce window.
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._emit_window_state()
        super().closeEvent(event)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _as_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _rect_is_reachable(rect: QRect) -> bool:
    """True if enough of ``rect`` lands on a connected display to be usable."""
    for screen in QGuiApplication.screens():
        overlap = screen.availableGeometry().intersected(rect)
        if overlap.width() >= _MIN_VISIBLE_W and overlap.height() >= _MIN_VISIBLE_H:
            return True
    return False
