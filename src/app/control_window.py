"""Main control GUI: a Run tab and an Edit tab under the suite's top bar."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontMetrics, QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, __version__
from . import theme
from .config import ALL_CHANNELS, Config
from .mapping_editor import MappingEditor
from .midi_engine import MidiEngine, note_name
from .theme import Key, StateChip, Tab, Tick

_MAX_LOG_LINES = 500

# Shared metrics for the output-placement controls, so every key/gap matches.
_SQ = 40       # square key width (stepper keys)
_VAL_W = 76    # the recessed readout between a stepper's keys
_TOGGLE_W = 108  # Reset view / Crop Edit-Done keys share a width and right edge
_GAP = 6       # spacing between keys in a cluster
_PAGE = 16     # page side margin
_SECTION = 18  # space between sections
_OUT_H = 46    # the Output slot: the one thing that must read across a dark room

# now_playing_changed text prefix -> (shape, LED colour, state word, name colour)
_NOW_STATES = (
    ("Playing:", ("triangle", theme.LED_GREEN, "Playing", theme.SIGNAL)),
    ("Idle:", ("square", theme.LED_RED, "Idle on output", theme.LEGEND_DIM)),
    ("Idle (black)", ("square", theme.LED_RED, "Idle on output", theme.LEGEND_DIM)),
    ("Missing file:", ("ring", theme.WARN_AMBER, "Missing file", theme.WARN_AMBER)),
    ("Output window closed", ("ring", theme.WARN_AMBER, "Output closed", theme.LEGEND_DIM)),
)


class ControlWindow(QMainWindow):
    """Run + Edit UI. Emits :pyattr:`config_changed` when the user saves."""

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
        self._edit_snapshot: Optional[tuple] = None

        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.resize(760, 800)

        root = QWidget(self)
        col = QVBoxLayout(root)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        col.addWidget(self._build_bar(root))
        col.addWidget(self._build_tabs(root))

        self._stack = QStackedWidget(root)
        self._status_page = self._build_status_page()
        self._edit_page = self._build_edit_page()
        self._stack.addWidget(self._status_page)
        self._stack.addWidget(self._edit_page)
        col.addWidget(self._stack, stretch=1)
        self.setCentralWidget(root)

        self._select_tab(self._status_page)
        self.set_midi_status(False, "Connecting…")
        self.set_now_playing("")
        self.refresh_status_labels()
        self._refresh_view_readouts()

    # ================= Bar and tabs ====================================
    def _build_bar(self, parent: QWidget) -> QWidget:
        """Suite name at the left (LiveCues in Legend, VideoCues in Signal), MIDI state at the right."""
        bar = QFrame(parent)
        bar.setObjectName("bar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(_PAGE, 0, _PAGE, 0)
        row.setSpacing(12)
        bar.setFixedHeight(52)

        title = QLabel(
            f'LiveCues <span style="color:{theme.SIGNAL}">VideoCues</span>', bar
        )
        title.setFont(theme.ui_font(18, QFont.DemiBold))
        title.setTextFormat(Qt.RichText)
        row.addWidget(title)
        row.addStretch(1)

        self._midi_detail = QLabel("", bar)
        self._midi_detail.setFont(theme.mono_font(12))
        self._midi_detail.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self._midi_detail, stretch=0)
        self._midi_chip = StateChip(bar)
        row.addWidget(self._midi_chip)
        return bar

    def _build_tabs(self, parent: QWidget) -> QWidget:
        strip = QWidget(parent)
        strip.setAttribute(Qt.WA_StyledBackground, True)
        strip.setStyleSheet(f"background: {theme.CHASSIS}; border-bottom: 1px solid {theme.LINE};")
        row = QHBoxLayout(strip)
        row.setContentsMargins(_PAGE, 0, _PAGE, 0)
        row.setSpacing(0)
        self._tab_run = Tab("Run", strip)
        self._tab_edit = Tab("Edit", strip)
        self._tab_run.clicked.connect(self._request_run)
        self._tab_edit.clicked.connect(self.enter_edit_mode)
        row.addWidget(self._tab_run)
        row.addWidget(self._tab_edit)
        return strip

    def _select_tab(self, page: QWidget) -> None:
        self._stack.setCurrentWidget(page)
        self._tab_run.set_selected(page is self._status_page)
        self._tab_edit.set_selected(page is self._edit_page)

    # ================= Run page ========================================
    def _build_status_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(_PAGE, _PAGE, _PAGE, _PAGE)
        layout.setSpacing(8)

        # Output: what is on the projector, beside the key that clears it.
        layout.addWidget(theme.legend("Output", page))
        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        slot = QFrame(page)
        slot.setObjectName("slot")
        slot.setFixedHeight(_OUT_H)
        slot_row = QHBoxLayout(slot)
        slot_row.setContentsMargins(12, 0, 12, 0)
        slot_row.setSpacing(12)
        self._now_chip = StateChip(slot)
        self._now_name = QLabel("", slot)
        self._now_name.setFont(theme.mono_font(16, QFont.Medium))
        self._now_chip.align_baseline_to(self._now_name.font())
        self._now_name.setMinimumWidth(40)
        self._now_name.setStyleSheet("background: transparent; border: 0;")
        slot_row.addWidget(self._now_chip)
        slot_row.addWidget(self._now_name, stretch=1)
        out_row.addWidget(slot, stretch=1)
        # Kept on self so it can sink red while the idle loop owns the output.
        self._idle_btn = Key("Return to Idle", page, hint="Ctrl+B")
        self._idle_btn.clicked.connect(self.return_to_idle_requested)
        out_row.addWidget(self._idle_btn, 0, Qt.AlignVCenter)
        layout.addLayout(out_row)

        # Where the cues come from and go to.
        info = QGridLayout()
        info.setHorizontalSpacing(8)
        info.setVerticalSpacing(6)
        # Set on Edit, so plain values on the panel, not sunk slots: only the
        # Output slot is recessed on Run.
        self._lbl_device = self._plain_value(page)
        self._lbl_channel = self._plain_value(page)
        self._lbl_screen = self._plain_value(page)
        for c, (caption, lbl) in enumerate((
            ("MIDI device", self._lbl_device),
            ("Channel", self._lbl_channel),
            ("Output display", self._lbl_screen),
        )):
            info.addWidget(theme.legend(caption, page), 0, c)
            info.addWidget(lbl, 1, c)
        info.setColumnStretch(0, 3)
        info.setColumnStretch(1, 1)
        info.setColumnStretch(2, 3)
        layout.addSpacing(6)
        layout.addLayout(info)

        layout.addSpacing(_SECTION - 8)
        layout.addWidget(theme.rule(page))
        layout.addSpacing(_SECTION - 8)
        layout.addWidget(self._build_display_controls(page))

        layout.addWidget(theme.rule(page))
        layout.addSpacing(_SECTION - 8)
        layout.addWidget(theme.legend("MIDI activity", page))
        self._log = QListWidget(page)
        self._log.setObjectName("log")
        self._log.setFont(theme.mono_font(12))
        self._log.setFocusPolicy(Qt.NoFocus)
        self._log.setMinimumHeight(96)
        layout.addWidget(self._log, stretch=1)

        layout.addSpacing(4)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        show_btn = Key("Show Output", page)
        show_btn.setToolTip("Reopen the output window if it was closed, or bring it to the front")
        show_btn.clicked.connect(self.show_output_requested)
        full_btn = Key("Fullscreen", page, hint="Ctrl+F")
        full_btn.clicked.connect(self.fullscreen_requested)
        buttons.addStretch(1)
        buttons.addWidget(show_btn)
        buttons.addWidget(full_btn)
        layout.addLayout(buttons)
        return page

    @staticmethod
    def _plain_value(parent: QWidget) -> QLabel:
        """A read-only Mono value printed on the panel (no slot, so it can't look editable)."""
        lbl = QLabel("—", parent)
        lbl.setFont(theme.mono_font(13))
        lbl.setStyleSheet(f"color: {theme.LEGEND};")
        lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return lbl

    @staticmethod
    def _stepper(
        parent: QWidget, less_glyph: str, more_glyph: str, name: str, on_less, on_more
    ) -> tuple[QHBoxLayout, QLabel]:
        """One axis: a key, a recessed Mono readout and a key, flush as a single unit."""
        row = QHBoxLayout()
        row.setSpacing(0)
        row.setContentsMargins(0, 0, 0, 0)
        less = Key("", parent, glyph=less_glyph, width=_SQ)
        more = Key("", parent, glyph=more_glyph, width=_SQ)
        for key, label, handler in ((less, f"{name} less", on_less), (more, f"{name} more", on_more)):
            key.setAccessibleName(label)
            key.setToolTip(label)
            key.clicked.connect(handler)
        value = theme.readout("", parent)
        value.setAlignment(Qt.AlignCenter)
        value.setFixedWidth(_VAL_W)
        row.addWidget(less)
        row.addWidget(value)
        row.addWidget(more)
        return row, value

    def _refresh_view_readouts(self) -> None:
        c = self._config
        self._val_x.setText(f"{c.video_offset_x * 100:+.1f}%")
        self._val_y.setText(f"{c.video_offset_y * 100:+.1f}%")
        self._val_zoom.setText(f"{c.video_zoom * 100:.1f}%")
        crops = {side: getattr(c, "video_crop_" + side) * 100 for side in self._val_crop}
        for side, lbl in self._val_crop.items():
            lbl.setText(f"{crops[side]:.1f}%")
        # The closed Crop group still shows its values, in one line.
        if any(round(v, 1) for v in crops.values()):
            self._crop_summary.setText(
                "   ".join(f"{k.capitalize()} {v:.1f}%" for k, v in crops.items())
            )
        else:
            self._crop_summary.setText("None")

    def _toggle_crop(self) -> None:
        """Show / hide the four crop steppers (set-up work, closed during a show)."""
        open_ = not self._crop_body.isVisible()
        self._crop_body.setVisible(open_)
        self._crop_summary.setVisible(not open_)
        self._crop_toggle.setText("Done" if open_ else "Edit")
        self._crop_toggle.setAccessibleName("Hide crop controls" if open_ else "Edit crop")

    def _build_display_controls(self, page: QWidget) -> QWidget:
        """Move / zoom / crop the video on the output display (persists in config).

        Every axis is the same stepper; a hairline separates the three groups.
        Each Step sits right beside the stepper it governs. Crop is set-up
        work, so it stays closed (summary only) until asked for.
        """
        box = QWidget(page)
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        head = QHBoxLayout()
        head.addWidget(theme.legend("Output position, zoom & crop", box))
        head.addStretch(1)
        reset = Key("Reset view", box, variant="quiet", width=_TOGGLE_W)
        reset.setToolTip("Back to full-frame: no move, zoom or crop")
        reset.clicked.connect(self.reset_view_requested)
        head.addWidget(reset)
        outer.addLayout(head)

        def new_grid(parent_layout_cols: bool = True) -> QGridLayout:
            # Columns: group | axis | stepper | axis | stepper | step.
            g = QGridLayout()
            g.setHorizontalSpacing(8)
            g.setVerticalSpacing(_GAP)
            g.setContentsMargins(0, 0, 0, 0)
            # Pinned in both grids so the open Crop rows line up with those above.
            g.setColumnMinimumWidth(0, 56)
            g.setColumnMinimumWidth(1, 62)
            g.setColumnMinimumWidth(2, 2 * _SQ + _VAL_W)
            g.setColumnMinimumWidth(3, 62)
            g.setColumnMinimumWidth(4, 2 * _SQ + _VAL_W)
            g.setColumnStretch(6, 1)
            return g

        def group(g: QGridLayout, row: int, title: str) -> None:
            lbl = theme.legend(title, box, theme.LEGEND)
            lbl.setFont(theme.legend_font(12))
            g.addWidget(lbl, row, 0, Qt.AlignVCenter)

        def axis(g: QGridLayout, row: int, col: int, title: str) -> None:
            lbl = theme.legend(title, box)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            g.addWidget(lbl, row, col)

        def step_at(g, row, which, value, lo, hi, handler, tip):
            spin, srow = self._step_control(box, value, lo, hi, handler)
            spin.setToolTip(tip)
            holder = QHBoxLayout()
            holder.setContentsMargins(0, 0, 0, 0)
            holder.addSpacing(14)
            holder.addLayout(srow)
            g.addLayout(holder, row, 5)
            setattr(self, which, spin)

        grid = new_grid()
        pan = self.pan_requested.emit
        group(grid, 0, "Move")
        axis(grid, 0, 1, "X")
        row, self._val_x = self._stepper(
            box, "left", "right", "Move X", lambda: pan(-1.0, 0.0), lambda: pan(1.0, 0.0)
        )
        grid.addLayout(row, 0, 2)
        axis(grid, 0, 3, "Y")
        row, self._val_y = self._stepper(
            box, "up", "down", "Move Y", lambda: pan(0.0, -1.0), lambda: pan(0.0, 1.0)
        )
        grid.addLayout(row, 0, 4)
        step_at(grid, 0, "_move_step", self._config.move_step * 100.0, 0.5, 50.0,
                self._on_move_step_changed, "How far one click moves the picture")

        grid.addWidget(theme.rule(box), 1, 0, 1, 7)

        group(grid, 2, "Zoom")
        axis(grid, 2, 1, "Scale")
        row, self._val_zoom = self._stepper(
            box, "minus", "plus", "Zoom",
            self.zoom_out_requested.emit, self.zoom_in_requested.emit,
        )
        grid.addLayout(row, 2, 2)
        step_at(grid, 2, "_zoom_step", self._config.zoom_step * 100.0, 1.0, 100.0,
                self._on_zoom_step_changed, "How much one click zooms")

        # A little air under this rule so the Crop row centres between it and the
        # section rule below.
        grid.addWidget(theme.rule(box), 3, 0, 1, 7, Qt.AlignTop)
        grid.setRowMinimumHeight(3, 3)

        # Crop: a header line (summary + toggle), then the steppers when open.
        group(grid, 4, "Crop")
        self._crop_summary = QLabel("", box)
        self._crop_summary.setFont(theme.mono_font(13))
        self._crop_summary.setStyleSheet(f"color: {theme.LEGEND};")
        grid.addWidget(self._crop_summary, 4, 1, 1, 5, Qt.AlignVCenter)
        self._crop_toggle = Key("Edit", box, variant="quiet", width=_TOGGLE_W)
        self._crop_toggle.setAccessibleName("Edit crop")
        self._crop_toggle.setToolTip("Show or hide the four crop edges")
        self._crop_toggle.clicked.connect(self._toggle_crop)
        grid.addWidget(self._crop_toggle, 4, 5, 1, 2, Qt.AlignRight)  # flush with Reset view
        for r in (0, 2, 4):
            grid.setRowMinimumHeight(r, theme.KEY_H + 6)
        outer.addLayout(grid)

        self._crop_body = QWidget(box)
        body = new_grid()
        self._val_crop: dict[str, QLabel] = {}
        # The empty group column keeps its width but loses its 8px spacing; give it back
        # so these steppers sit exactly under Move's and Zoom's.
        body.setContentsMargins(8, 0, 0, 0)
        for r, c, side, label in (
            (0, 1, "top", "Top"), (0, 3, "bottom", "Bottom"),
            (1, 1, "left", "Left"), (1, 3, "right", "Right"),
        ):
            axis(body, r, c, label)
            row, value = self._stepper(
                self._crop_body, "minus", "plus", f"Crop {label.lower()}",
                lambda _=False, s=side: self.crop_requested.emit(s, -1),
                lambda _=False, s=side: self.crop_requested.emit(s, 1),
            )
            self._val_crop[side] = value
            body.addLayout(row, r, c + 1)
        self._crop_body.setLayout(body)
        self._crop_body.setVisible(False)
        outer.addWidget(self._crop_body)
        return box

    def _step_control(self, parent, value_pct, minimum, maximum, on_changed):
        """A 'STEP [n %]' row driving a percentage spinbox."""
        box = QDoubleSpinBox(parent)
        box.setRange(minimum, maximum)
        box.setSingleStep(0.5)
        box.setDecimals(1)
        box.setSuffix(" %")
        box.setFont(theme.mono_font(13))
        box.setFixedHeight(theme.KEY_H)
        box.setFixedWidth(_VAL_W + 12)
        box.setAlignment(Qt.AlignCenter)
        box.setValue(value_pct)
        box.valueChanged.connect(on_changed)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(theme.legend("Step", parent))
        row.addWidget(box)
        return box, row

    # ================= Edit page =======================================
    def _build_edit_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(_PAGE, _PAGE, _PAGE, _PAGE)
        layout.setSpacing(6)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(2, 1)

        def field(caption: str, widget: QWidget, row: int, col: int, extra: Optional[QWidget] = None, span: int = 1):
            grid.addWidget(theme.legend(caption, page), row, col, 1, span)
            if extra is None:
                grid.addWidget(widget, row + 1, col, 1, span)
            else:
                grid.addWidget(_wrap_row(widget, extra), row + 1, col, 1, span)

        self._edit_video_root = QLineEdit(page)
        self._edit_video_root.setFont(theme.mono_font(13))
        self._edit_video_root.setPlaceholderText("Folder that holds the clips")
        root_browse = Key("Browse…", page)
        root_browse.clicked.connect(self._browse_video_root)
        field("Video root folder", self._edit_video_root, 0, 0, root_browse, span=3)

        self._edit_idle = QLineEdit(page)
        self._edit_idle.setFont(theme.mono_font(13))
        self._edit_idle.setPlaceholderText("None: the output shows black between cues")
        idle_browse = Key("Browse…", page)
        idle_browse.clicked.connect(self._browse_idle)
        field("Idle (loop) video", self._edit_idle, 2, 0, idle_browse, span=3)

        grid.setRowMinimumHeight(4, 10)

        self._edit_device = QComboBox(page)
        self._edit_device.setPlaceholderText("No MIDI devices found")
        dev_refresh = Key("Refresh", page)
        dev_refresh.setToolTip("Look for MIDI devices again")
        dev_refresh.clicked.connect(self._reload_devices)
        field("MIDI device", self._edit_device, 5, 0, dev_refresh)

        self._edit_channel = QComboBox(page)
        self._edit_channel.addItem("All channels", ALL_CHANNELS)
        for ch in range(1, 17):
            self._edit_channel.addItem(f"Channel {ch}", ch)
        grid.setColumnMinimumWidth(1, 8)
        field("MIDI channel", self._edit_channel, 5, 2)

        self._edit_screen = QComboBox(page)
        field("Output display", self._edit_screen, 7, 0)

        self._edit_muted = Tick("Mute video audio", page)
        field("Audio", self._edit_muted, 7, 2)
        layout.addLayout(grid)

        layout.addSpacing(_SECTION - 6)
        layout.addWidget(theme.rule(page))
        layout.addSpacing(_SECTION - 6)
        layout.addWidget(theme.legend("Note → video mappings", page))
        self._mapping_editor = MappingEditor(self._edit_video_root.text, page)
        self._mapping_editor.test_requested.connect(self.test_note_requested)
        layout.addWidget(self._mapping_editor, stretch=1)

        layout.addSpacing(4)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self._mapping_editor.add_key)
        buttons.addStretch(1)
        cancel_btn = Key("Cancel", page)
        cancel_btn.setToolTip("Drop the changes and go back to Run")
        cancel_btn.clicked.connect(self._cancel)
        save_btn = Key("Save", page, variant="lit")
        save_btn.clicked.connect(self._save)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)
        return page

    # ================= External updates ================================
    def set_config(self, config: Config) -> None:
        self._config = config.copy()
        self.refresh_status_labels()
        self._refresh_view_readouts()
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
        """Bar state: a green disc when MIDI is open, an amber ring (and why) when not."""
        connecting = not connected and detail.startswith("Connecting")
        if connected:
            self._midi_chip.set_state("disc", theme.LED_GREEN, "MIDI connected", theme.LEGEND)
        elif connecting:
            self._midi_chip.set_state("ring", theme.LEGEND_DIM, "Connecting…", theme.LEGEND_DIM)
        else:
            self._midi_chip.set_state("ring", theme.WARN_AMBER, "MIDI offline", theme.WARN_AMBER)
        self._midi_chip.setToolTip(detail)
        # Connected: the device readout below already names the port. Offline:
        # say why, beside the state.
        shown = "" if connected or connecting else detail
        fm = QFontMetrics(self._midi_detail.font())
        self._midi_detail.setText(fm.elidedText(shown, Qt.ElideMiddle, 340))
        self._midi_detail.setToolTip(shown)
        self._midi_detail.setStyleSheet(f"color: {theme.LEGEND_DIM};")

    def append_activity(self, line: str) -> None:
        self._log.addItem(line)
        while self._log.count() > _MAX_LOG_LINES:
            self._log.takeItem(0)
        self._log.scrollToBottom()

    def set_now_playing(self, text: str) -> None:
        """Show what is on the output: a state shape and word, then the clip."""
        shape, colour, word, name_colour = ("ring", theme.LEGEND_DIM, "Waiting", theme.LEGEND_DIM)
        name = text
        for prefix, state in _NOW_STATES:
            if text.startswith(prefix):
                shape, colour, word, name_colour = state
                name = text[len(prefix):].strip()
                break
        if text == "Idle (black)":
            name = "black (no idle video set)"
        elif text == "Output window closed":
            name = "Show Output reopens it"
        self._now_chip.set_state(shape, colour, word, theme.LEGEND)
        self._now_name.setStyleSheet(f"color: {name_colour}; background: transparent; border: 0;")
        fm = QFontMetrics(self._now_name.font())
        width = max(80, self._now_name.width())
        self._now_name.setText(fm.elidedText(name, Qt.ElideMiddle, width))
        self._now_name.setToolTip(name)
        self._now_full = name

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        full = getattr(self, "_now_full", "")
        if full:
            fm = QFontMetrics(self._now_name.font())
            self._now_name.setText(fm.elidedText(full, Qt.ElideMiddle, max(80, self._now_name.width())))

    def set_output_idle(self, idle: bool) -> None:
        """Sink the Return to Idle key in LED red while no clip is on the output.

        Follows the real output state, so a trigger that fails (missing file)
        correctly leaves the key red.
        """
        self._idle_btn.set_sunk(idle)

    def refresh_status_labels(self) -> None:
        self._lbl_device.setText(self._config.midi_device or "None selected")
        ch = self._config.midi_channel
        self._lbl_channel.setText("All" if ch == ALL_CHANNELS else str(ch))
        self._lbl_screen.setText(self._describe_screen(self._config.output_screen))
        for lbl in (self._lbl_device, self._lbl_screen):
            lbl.setToolTip(lbl.text())
        # Nothing will fire without a device: say so in the warning hue.
        color = theme.LEGEND if self._config.midi_device else theme.WARN_AMBER
        self._lbl_device.setStyleSheet(f"color: {color};")

    # ================= Mode switching ==================================
    def enter_edit_mode(self) -> None:
        if self._stack.currentWidget() is self._edit_page:
            return
        self._populate_edit_fields()
        self._select_tab(self._edit_page)

    def _request_run(self) -> None:
        """Run tab: leave Edit, asking first when the form has unsaved changes."""
        if self._stack.currentWidget() is not self._edit_page:
            return
        if self._form_snapshot() == self._edit_snapshot:
            self._select_tab(self._status_page)
            return
        box = QMessageBox(self)
        box.setWindowTitle("Unsaved changes")
        box.setText("Save your configuration changes?")
        box.setInformativeText("Discard drops them and goes back to Run.")
        save = Key("Save", box, variant="lit")
        discard = Key("Discard", box)
        keep = Key("Keep editing", box)
        box.addButton(save, QMessageBox.AcceptRole)
        box.addButton(discard, QMessageBox.DestructiveRole)
        box.addButton(keep, QMessageBox.RejectRole)
        box.setDefaultButton(None)
        box.setEscapeButton(keep)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save:
            self._save()
        elif clicked is discard:
            self._cancel()
        else:
            self._tab_edit.set_selected(True)
            self._tab_run.set_selected(False)

    def _cancel(self) -> None:
        self._select_tab(self._status_page)

    def _form_config(self) -> Config:
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
        return new_config

    def _form_snapshot(self) -> tuple:
        c = self._form_config()
        return (
            c.video_root, c.idle_video, c.midi_device, c.midi_channel,
            c.output_screen, c.audio_muted, tuple(sorted(c.mappings.items())),
        )

    def _save(self) -> None:
        new_config = self._form_config()
        self._config = new_config
        self.refresh_status_labels()
        self._select_tab(self._status_page)
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
        self._edit_snapshot = self._form_snapshot()

    def _reload_devices(self, select: Optional[str] = None) -> None:
        if not select:
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


def _wrap_row(main: QWidget, extra: QWidget) -> QWidget:
    """A field with a key on its right, as one grid cell."""
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    row.addWidget(main, stretch=1)
    row.addWidget(extra)
    return w
