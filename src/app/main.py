"""Application entry point: wires config, MIDI engine, and the two windows."""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication

from . import APP_NAME
from .config import Config
from .paths import asset
from .control_window import ControlWindow
from .midi_engine import MidiEngine, note_name
from .theme import apply_theme
from .video_window import VideoWindow


class App:
    """Owns the live state and connects components together."""

    def __init__(self, qapp: QApplication) -> None:
        self.qapp = qapp
        self.config = Config.load()

        self.engine = MidiEngine()
        self.video = VideoWindow()
        self.control = ControlWindow(self.config, self.engine)

        self._connect_signals()
        self._install_hotkeys()

    # ----- wiring -------------------------------------------------------
    def _connect_signals(self) -> None:
        self.engine.note_on.connect(self._on_note_on)
        self.engine.midi_activity.connect(self.control.append_activity)
        self.engine.status_changed.connect(self.control.set_midi_status)

        self.video.now_playing_changed.connect(self.control.set_now_playing)

        self.video.idle_state_changed.connect(self.control.set_output_idle)
        self.video.window_state_changed.connect(self._on_window_state_changed)

        self.control.config_changed.connect(self._apply_config)
        self.control.test_note_requested.connect(self._play_note)
        self.control.return_to_idle_requested.connect(self.video.return_to_idle)
        self.control.show_output_requested.connect(self.video.show_output)
        self.control.fullscreen_requested.connect(self.video.toggle_fullscreen)
        self.control.closing.connect(self._on_control_closed)

        self.control.zoom_in_requested.connect(self.video.zoom_in)
        self.control.zoom_out_requested.connect(self.video.zoom_out)
        self.control.pan_requested.connect(self.video.pan)
        self.control.crop_requested.connect(self.video.crop)
        self.control.move_step_changed.connect(self._on_move_step_changed)
        self.control.zoom_step_changed.connect(self._on_zoom_step_changed)
        self.control.reset_view_requested.connect(self.video.reset_view)
        self.video.view_changed.connect(self._on_view_changed)

    def _install_hotkeys(self) -> None:
        # Application-wide so they fire whether the control or output window
        # has focus.
        # Modifier-based so a stray keypress during a show can't change the
        # output; Esc stays bare because leaving fullscreen must be reflexive.
        for key, slot in (
            ("Ctrl+B", self.video.return_to_idle),
            ("Ctrl+F", self.video.toggle_fullscreen),
            ("Ctrl+T", self.control._test_first_mapping),
            ("Esc", self._exit_fullscreen),
        ):
            sc = QShortcut(QKeySequence(key), self.control)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(slot)

    # ----- behaviour ----------------------------------------------------
    def _on_note_on(self, note: int, velocity: int) -> None:
        self._play_note(note)

    def _play_note(self, note: int) -> None:
        path = self.config.mapping_path(note)
        if path is None:
            self.control.append_activity(f"No mapping for {note_name(note)} ({note})")
            return
        self.video.trigger(path)

    def _apply_config(self, config: Config) -> None:
        self.config = config
        config.save()
        self.control.set_config(config)
        self.video.configure(config.idle_path(), config.audio_muted)
        # Only acts when the chosen display actually changed, so saving the Edit
        # form doesn't yank the output window back to a centered position.
        self.video.show_on_screen(config.output_screen)
        self.video.set_move_step(config.move_step)
        self.video.set_zoom_step(config.zoom_step)
        self.video.apply_view(config.view_dict())
        self.engine.connect_device(config.midi_device, config.midi_channel)

    def _on_view_changed(self, view: dict) -> None:
        """Persist live zoom/pan/crop adjustments made from the control window."""
        self.config.video_zoom = view["zoom"]
        self.config.video_offset_x = view["offset_x"]
        self.config.video_offset_y = view["offset_y"]
        self.config.video_crop_left = view["crop_left"]
        self.config.video_crop_right = view["crop_right"]
        self.config.video_crop_top = view["crop_top"]
        self.config.video_crop_bottom = view["crop_bottom"]
        self.config.save()
        self.control.set_config(self.config)

    def _on_window_state_changed(self, state: dict) -> None:
        """Persist where the operator left the output window (debounced upstream)."""
        self.config.apply_window_state(state)
        self.config.save()
        self.control.set_config(self.config)

    def _on_move_step_changed(self, step: float) -> None:
        """Persist the configurable Move increment and apply it live."""
        self.config.move_step = step
        self.video.set_move_step(step)
        self.config.save()

    def _on_zoom_step_changed(self, step: float) -> None:
        """Persist the configurable Zoom increment and apply it live."""
        self.config.zoom_step = step
        self.video.set_zoom_step(step)
        self.config.save()

    def _exit_fullscreen(self) -> None:
        if self.video.isFullScreen():
            self.video.toggle_fullscreen()

    # ----- lifecycle ----------------------------------------------------
    def start(self) -> None:
        self.control.show()
        self.video.configure(self.config.idle_path(), self.config.audio_muted)
        self.video.apply_window_state(self.config.window_state())
        self.video.set_move_step(self.config.move_step)
        self.video.set_zoom_step(self.config.zoom_step)
        self.video.apply_view(self.config.view_dict())
        self.engine.connect_device(self.config.midi_device, self.config.midi_channel)

    def _on_control_closed(self) -> None:
        """The control window is the app: closing it takes the output down too."""
        self.video.close()
        self.shutdown()
        self.qapp.quit()

    def shutdown(self) -> None:
        self.engine.disconnect_device()


def main() -> int:
    qapp = QApplication(sys.argv)
    qapp.setApplicationName(APP_NAME)
    qapp.setWindowIcon(QIcon(str(asset("app.ico"))))
    apply_theme(qapp)

    app = App(qapp)
    app.start()
    qapp.aboutToQuit.connect(app.shutdown)
    return qapp.exec()


if __name__ == "__main__":
    raise SystemExit(main())
