"""Main control GUI: a Status view and an Edit view in a stacked widget."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, __version__
from .config import ALL_CHANNELS, Config
from .mapping_editor import MappingEditor
from .midi_engine import MidiEngine, note_name

_MAX_LOG_LINES = 500

# Shared metrics for the output-placement controls, so every button/gap matches.
_BTN_H = 28    # common control height (arrows, zoom, crop, spinbox, reset)
_SQ = 40       # square button width (arrows, crop +/-)
_WIDE = 76     # text button width (zoom in/out)
_GAP = 6       # spacing between rows / grid cells


class ControlWindow(QMainWindow):
    """Status + Edit UI. Emits :pyattr:`config_changed` when the user saves."""

    config_changed = Signal(object)       # Config
    test_note_requested = Signal(int)     # play this note's mapped clip
    return_to_idle_requested = Signal()   # stop the current clip, resume the idle loop
    show_output_requested = Signal()      # (re)open / raise the output window
    fullscreen_requested = Signal()
    closing = Signal()                    # control window closed -> quit the app
    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    pan_requested = Signal(float, float)  # (dx, dy) in steps: -left/+right, -up/+down
    crop_requested = Signal(str, int)     # (side, sign): +1 crop / -1 uncrop the side
    move_step_changed = Signal(float)     # per-click pan increment (fraction of window)
    zoom_step_changed = Signal(float)     # per-click zoom increment (fraction)
    reset_view_requested = Signal()

    def __init__(self, config: Config, engine: MidiEngine) -> None:
        super().__init__()
        self._config = config.copy()
        self._engine = engine

        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.resize(720, 560)

        self._stack = QStackedWidget(self)
        self._status_page = self._build_status_page()
        self._edit_page = self._build_edit_page()
        self._stack.addWidget(self._status_page)
        self._stack.addWidget(self._edit_page)
        self.setCentralWidget(self._stack)

        self.refresh_status_labels()

    # ================= Status page =====================================
    def _build_status_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)

        status_box = QGroupBox("Status", page)
        form = QFormLayout(status_box)
        self._lbl_midi = QLabel("—")
        self._lbl_device = QLabel("—")
        self._lbl_channel = QLabel("—")
        self._lbl_screen = QLabel("—")
        self._lbl_playing = QLabel("—")
        form.addRow("MIDI:", self._lbl_midi)
        form.addRow("Device:", self._lbl_device)
        form.addRow("Channel:", self._lbl_channel)
        form.addRow("Output display:", self._lbl_screen)
        form.addRow("Now playing:", self._lbl_playing)
        layout.addWidget(status_box)

        layout.addWidget(self._build_display_controls(page))

        log_box = QGroupBox("MIDI activity", page)
        log_layout = QVBoxLayout(log_box)
        self._log = QListWidget(log_box)
        log_layout.addWidget(self._log)
        layout.addWidget(log_box, stretch=1)

        buttons = QHBoxLayout()
        edit_btn = QPushButton("Edit Configuration", page)
        edit_btn.clicked.connect(self.enter_edit_mode)
        test_btn = QPushButton("Test Trigger (Ctrl+T)", page)
        test_btn.clicked.connect(self._test_first_mapping)
        # Kept on self so its colour can track the output state (red = idle).
        self._idle_btn = QPushButton("Return to Idle (Ctrl+B)", page)
        self._idle_btn.clicked.connect(self.return_to_idle_requested)
        show_btn = QPushButton("Show Output", page)
        show_btn.setToolTip("Reopen the output window if it was closed, or bring it to the front")
        show_btn.clicked.connect(self.show_output_requested)
        full_btn = QPushButton("Fullscreen (Ctrl+F)", page)
        full_btn.clicked.connect(self.fullscreen_requested)
        buttons.addWidget(edit_btn)
        buttons.addWidget(test_btn)
        buttons.addWidget(self._idle_btn)
        buttons.addWidget(show_btn)
        buttons.addWidget(full_btn)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return page

    def _build_display_controls(self, page: QWidget) -> QGroupBox:
        """Move / zoom / crop the video on the output display (persists in config)."""
        box = QGroupBox("Output position, zoom && crop", page)
        outer = QVBoxLayout(box)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(10)

        # Three top-aligned clusters separated by full-height dividers, so their
        # captions line up on a common baseline.
        clusters = QHBoxLayout()
        clusters.setSpacing(16)
        clusters.addWidget(self._build_move_pad(box), 0, Qt.AlignTop)
        clusters.addWidget(self._vline(box))
        clusters.addWidget(self._build_zoom_pad(box), 0, Qt.AlignTop)
        clusters.addWidget(self._vline(box))
        clusters.addWidget(self._build_crop_pad(box), 0, Qt.AlignTop)
        clusters.addStretch(1)
        outer.addLayout(clusters)

        # Reset on its own, separated from the adjustment controls.
        line = QFrame(box)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        outer.addWidget(line)
        reset_row = QHBoxLayout()
        reset = QPushButton("Reset view", box)
        reset.setFixedHeight(_BTN_H)
        reset.clicked.connect(self.reset_view_requested)
        reset_row.addStretch(1)
        reset_row.addWidget(reset)
        reset_row.addStretch(1)
        outer.addLayout(reset_row)
        return box

    def _cluster(self, parent: QWidget, title: str) -> tuple[QWidget, QVBoxLayout]:
        """A captioned column with consistent margins/spacing for one control group."""
        w = QWidget(parent)
        col = QVBoxLayout(w)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(_GAP)
        col.addWidget(self._caption(title, w))
        return w, col

    def _build_move_pad(self, parent: QWidget) -> QWidget:
        """Symmetric directional pad + configurable step, for panning the video."""
        w, col = self._cluster(parent, "Move")

        pad = QGridLayout()
        pad.setSpacing(_GAP)
        for c in range(3):
            pad.setColumnStretch(c, 1)  # equal columns keep the cross centred
        up, down = self._btn("↑", _SQ, w), self._btn("↓", _SQ, w)
        left, right = self._btn("←", _SQ, w), self._btn("→", _SQ, w)
        pad.addWidget(up, 0, 1, Qt.AlignCenter)
        pad.addWidget(left, 1, 0, Qt.AlignCenter)
        pad.addWidget(right, 1, 2, Qt.AlignCenter)
        pad.addWidget(down, 2, 1, Qt.AlignCenter)
        up.clicked.connect(lambda: self.pan_requested.emit(0.0, -1.0))
        down.clicked.connect(lambda: self.pan_requested.emit(0.0, 1.0))
        left.clicked.connect(lambda: self.pan_requested.emit(-1.0, 0.0))
        right.clicked.connect(lambda: self.pan_requested.emit(1.0, 0.0))
        col.addLayout(pad)

        # Configurable step size (percent of the output, per click), centred
        # under the pad.
        self._move_step, step_row = self._step_control(
            w, self._config.move_step * 100.0, 0.5, 50.0, self._on_move_step_changed
        )
        col.addLayout(step_row)
        return w

    def _build_zoom_pad(self, parent: QWidget) -> QWidget:
        w, col = self._cluster(parent, "Zoom")
        zoom_in = self._btn("+  In", _WIDE, w)
        zoom_out = self._btn("−  Out", _WIDE, w)
        zoom_in.clicked.connect(self.zoom_in_requested)
        zoom_out.clicked.connect(self.zoom_out_requested)
        col.addWidget(zoom_in)
        col.addWidget(zoom_out)
        # Configurable per-click zoom increment (percent), centred under the buttons.
        self._zoom_step, step_row = self._step_control(
            w, self._config.zoom_step * 100.0, 1.0, 100.0, self._on_zoom_step_changed
        )
        col.addLayout(step_row)
        col.addStretch(1)
        return w

    def _step_control(self, parent, value_pct, minimum, maximum, on_changed):
        """A centred 'Step  [n %]' row driving a percentage spinbox."""
        box = QDoubleSpinBox(parent)
        box.setRange(minimum, maximum)
        box.setSingleStep(0.5)
        box.setDecimals(1)
        box.setSuffix(" %")
        box.setFixedHeight(_BTN_H)
        box.setValue(value_pct)
        box.valueChanged.connect(on_changed)
        row = QHBoxLayout()
        row.setSpacing(_GAP)
        row.addStretch(1)
        row.addWidget(QLabel("Step", parent))
        row.addWidget(box)
        row.addStretch(1)
        return box, row

    def _build_crop_pad(self, parent: QWidget) -> QWidget:
        """A row per action (crop / uncrop), a column per edge."""
        w, col = self._cluster(parent, "Crop edges")
        grid = QGridLayout()
        grid.setSpacing(_GAP)
        sides = [("Top", "top"), ("Bottom", "bottom"), ("Left", "left"), ("Right", "right")]
        for c, (label, _side) in enumerate(sides):
            grid.addWidget(self._caption(label, w), 0, c + 1, Qt.AlignCenter)
        grid.addWidget(QLabel("Crop", w), 1, 0, Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(QLabel("Uncrop", w), 2, 0, Qt.AlignRight | Qt.AlignVCenter)
        for c, (_label, side) in enumerate(sides):
            crop = self._btn("+", _SQ, w)
            uncrop = self._btn("−", _SQ, w)
            crop.clicked.connect(lambda _=False, s=side: self.crop_requested.emit(s, 1))
            uncrop.clicked.connect(lambda _=False, s=side: self.crop_requested.emit(s, -1))
            grid.addWidget(crop, 1, c + 1, Qt.AlignCenter)
            grid.addWidget(uncrop, 2, c + 1, Qt.AlignCenter)
        col.addLayout(grid)
        col.addStretch(1)
        return w

    @staticmethod
    def _btn(text: str, width: int, parent: QWidget) -> QPushButton:
        b = QPushButton(text, parent)
        b.setFixedSize(width, _BTN_H)
        return b

    @staticmethod
    def _caption(text: str, parent: QWidget) -> QLabel:
        # Bold, default text colour so it stays legible on light *and* dark
        # themes (the previous palette(mid) was too low-contrast).
        lbl = QLabel(text, parent)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-weight: 600;")
        return lbl

    @staticmethod
    def _vline(parent: QWidget) -> QFrame:
        line = QFrame(parent)
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    # ================= Edit page =======================================
    def _build_edit_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)

        settings_box = QGroupBox("Settings", page)
        form = QFormLayout(settings_box)

        self._edit_video_root = QLineEdit(page)
        root_row = QHBoxLayout()
        root_browse = QPushButton("Browse…", page)
        root_browse.clicked.connect(self._browse_video_root)
        root_row.addWidget(self._edit_video_root)
        root_row.addWidget(root_browse)
        form.addRow("Video root folder:", _wrap(root_row))

        self._edit_idle = QLineEdit(page)
        idle_row = QHBoxLayout()
        idle_browse = QPushButton("Browse…", page)
        idle_browse.clicked.connect(self._browse_idle)
        idle_row.addWidget(self._edit_idle)
        idle_row.addWidget(idle_browse)
        form.addRow("Idle (loop) video:", _wrap(idle_row))

        self._edit_device = QComboBox(page)
        dev_row = QHBoxLayout()
        dev_refresh = QPushButton("Refresh", page)
        dev_refresh.clicked.connect(self._reload_devices)
        dev_row.addWidget(self._edit_device, stretch=1)
        dev_row.addWidget(dev_refresh)
        form.addRow("MIDI device:", _wrap(dev_row))

        self._edit_channel = QComboBox(page)
        self._edit_channel.addItem("All channels", ALL_CHANNELS)
        for ch in range(1, 17):
            self._edit_channel.addItem(f"Channel {ch}", ch)
        form.addRow("MIDI channel:", self._edit_channel)

        self._edit_screen = QComboBox(page)
        form.addRow("Output display:", self._edit_screen)

        self._edit_muted = QCheckBox("Mute video audio", page)
        form.addRow("Audio:", self._edit_muted)

        layout.addWidget(settings_box)

        map_box = QGroupBox("Note → Video mappings", page)
        map_layout = QVBoxLayout(map_box)
        self._mapping_editor = MappingEditor(self._edit_video_root.text, map_box)
        self._mapping_editor.test_requested.connect(self.test_note_requested)
        map_layout.addWidget(self._mapping_editor)
        layout.addWidget(map_box, stretch=1)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save", page)
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel", page)
        cancel_btn.clicked.connect(self._cancel)
        buttons.addStretch(1)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)
        return page

    # ================= External updates ================================
    def set_config(self, config: Config) -> None:
        self._config = config.copy()
        self.refresh_status_labels()
        # Keep the step spinboxes in sync without re-emitting their signals.
        for box, value in (
            (self._move_step, self._config.move_step),
            (self._zoom_step, self._config.zoom_step),
        ):
            box.blockSignals(True)
            box.setValue(value * 100.0)
            box.blockSignals(False)

    def _on_move_step_changed(self, percent: float) -> None:
        self._config.move_step = percent / 100.0
        self.move_step_changed.emit(self._config.move_step)

    def _on_zoom_step_changed(self, percent: float) -> None:
        self._config.zoom_step = percent / 100.0
        self.zoom_step_changed.emit(self._config.zoom_step)

    def set_midi_status(self, connected: bool, detail: str) -> None:
        self._lbl_midi.setText(("● Connected — " if connected else "○ ") + detail)
        self._lbl_midi.setStyleSheet("color: #2e7d32;" if connected else "color: #c62828;")

    def append_activity(self, line: str) -> None:
        self._log.addItem(line)
        while self._log.count() > _MAX_LOG_LINES:
            self._log.takeItem(0)
        self._log.scrollToBottom()

    def set_now_playing(self, text: str) -> None:
        self._lbl_playing.setText(text)

    def set_output_idle(self, idle: bool) -> None:
        """Colour the Return to Idle button red while no clip is on the output.

        Follows the real output state, so a trigger that fails (missing file)
        correctly leaves the button red.
        """
        self._idle_btn.setStyleSheet(
            "background-color: #c62828; color: white; font-weight: 600;" if idle else ""
        )

    def refresh_status_labels(self) -> None:
        self._lbl_device.setText(self._config.midi_device or "—")
        ch = self._config.midi_channel
        self._lbl_channel.setText("All" if ch == ALL_CHANNELS else str(ch))
        self._lbl_screen.setText(self._describe_screen(self._config.output_screen))

    # ================= Mode switching ==================================
    def enter_edit_mode(self) -> None:
        self._populate_edit_fields()
        self._stack.setCurrentWidget(self._edit_page)

    def _cancel(self) -> None:
        self._stack.setCurrentWidget(self._status_page)

    def _save(self) -> None:
        # Start from the live config and overwrite only what this form owns, so
        # settings the Edit view doesn't show (view transform, window placement)
        # survive a save.
        new_config = self._config.copy()
        new_config.video_root = self._edit_video_root.text().strip()
        new_config.idle_video = self._edit_idle.text().strip()
        new_config.midi_device = self._edit_device.currentText().strip()
        new_config.midi_channel = self._edit_channel.currentData()
        new_config.output_screen = self._edit_screen.currentData() or 0
        new_config.audio_muted = self._edit_muted.isChecked()
        new_config.mappings = self._mapping_editor.to_mappings()
        self._config = new_config
        self.refresh_status_labels()
        self._stack.setCurrentWidget(self._status_page)
        self.config_changed.emit(new_config.copy())

    # ================= Edit field population ===========================
    def _populate_edit_fields(self) -> None:
        cfg = self._config
        self._edit_video_root.setText(cfg.video_root)
        self._edit_idle.setText(cfg.idle_video)
        self._reload_devices(select=cfg.midi_device)
        ch_index = self._edit_channel.findData(cfg.midi_channel)
        self._edit_channel.setCurrentIndex(max(0, ch_index))
        self._reload_screens(select=cfg.output_screen)
        self._edit_muted.setChecked(cfg.audio_muted)
        self._mapping_editor.load(cfg.mappings)

    def _reload_devices(self, select: Optional[str] = None) -> None:
        if select is None:
            select = self._edit_device.currentText()
        self._edit_device.clear()
        devices = self._engine.available_devices()
        self._edit_device.addItems(devices)
        if select:
            idx = self._edit_device.findText(select)
            if idx >= 0:
                self._edit_device.setCurrentIndex(idx)
            else:
                # Keep a saved device name even if it's not currently present.
                self._edit_device.addItem(select)
                self._edit_device.setCurrentIndex(self._edit_device.count() - 1)

    def _reload_screens(self, select: int = 0) -> None:
        self._edit_screen.clear()
        for i, screen in enumerate(QGuiApplication.screens()):
            self._edit_screen.addItem(self._describe_screen(i), i)
        if self._edit_screen.count() == 0:
            self._edit_screen.addItem("Display 1", 0)
        idx = self._edit_screen.findData(select)
        self._edit_screen.setCurrentIndex(idx if idx >= 0 else 0)

    # ================= Browsing ========================================
    def _browse_video_root(self) -> None:
        start = self._edit_video_root.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select video root folder", start)
        if folder:
            self._edit_video_root.setText(folder)

    def _browse_idle(self) -> None:
        root = self._edit_video_root.text().strip()
        start = root or str(Path.home())
        selected, _ = QFileDialog.getOpenFileName(
            self, "Select idle video", start,
            "Video files (*.mp4 *.mov *.mkv *.avi *.m4v *.webm *.wmv);;All files (*)",
        )
        if not selected:
            return
        if root:
            try:
                selected = os.path.relpath(selected, root).replace(os.sep, "/")
            except ValueError:
                pass
        self._edit_idle.setText(selected)

    # ================= Misc ============================================
    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        """Closing the control window shuts the whole app down, output included."""
        self.closing.emit()
        super().closeEvent(event)

    def _test_first_mapping(self) -> None:
        if not self._config.mappings:
            self.append_activity("Test Trigger: no mappings configured")
            return
        first = sorted(self._config.mappings)[0]
        self.append_activity(f"Test Trigger: {note_name(first)} ({first})")
        self.test_note_requested.emit(first)

    @staticmethod
    def _describe_screen(index: int) -> str:
        screens = QGuiApplication.screens()
        if 0 <= index < len(screens):
            geo = screens[index].geometry()
            name = screens[index].name() or f"Display {index + 1}"
            primary = " (primary)" if screens[index] == QGuiApplication.primaryScreen() else ""
            return f"{index}: {name} — {geo.width()}×{geo.height()}{primary}"
        return f"Display {index + 1} (not connected)"


def _wrap(layout) -> QWidget:
    w = QWidget()
    layout.setContentsMargins(0, 0, 0, 0)
    w.setLayout(layout)
    return w
