"""Editable note -> video mapping table used by the Edit view."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .midi_engine import note_name, parse_note_name
from .theme import Key

_COL_NOTE = 0
_COL_NAME = 1
_COL_PATH = 2
_COL_ACTIONS = 3

_ROW_H = theme.KEY_H + 10   # a 36px field with 5px above and below
_PAD = 5


class MappingEditor(QWidget):
    """Rows of (note, name, relative video path, browse/test/remove)."""

    test_requested = Signal(int)  # note number

    def __init__(
        self,
        get_video_root: Callable[[], str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._get_video_root = get_video_root
        self._fields: Dict[QSpinBox, tuple] = {}  # row's spinbox -> (spin, path edit)

        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(
            ["Note", "Name", "Video file (relative to root)", ""]
        )
        for col in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(col)
            item.setFont(theme.legend_font(11))
            item.setForeground(QColor(theme.LEGEND_DIM))
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setHighlightSections(False)
        header.setSectionResizeMode(_COL_NOTE, QHeaderView.Fixed)
        header.setSectionResizeMode(_COL_NAME, QHeaderView.Fixed)
        header.setSectionResizeMode(_COL_PATH, QHeaderView.Stretch)
        header.setSectionResizeMode(_COL_ACTIONS, QHeaderView.Fixed)
        header.resizeSection(_COL_NOTE, 92)
        header.resizeSection(_COL_NAME, 80)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(_ROW_H)
        self.table.setMinimumHeight(30 + 2 * _ROW_H)
        self.table.setShowGrid(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setStyleSheet(
            f"QTableWidget::item {{ border-bottom: 1px solid {theme.LINE}; }}"
        )

        # Placed by the Edit page in its bottom row; owned by this editor.
        self.add_key = Key("Add mapping", self, glyph="plus")
        self.add_key.clicked.connect(lambda: self.add_row())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.table)

        # Empty state: say what the table is for instead of showing a blank box.
        self._empty = QLabel("No mappings yet. Add one to link a MIDI note to a video.", self.table.viewport())
        self._empty.setAlignment(Qt.AlignCenter)
        self._empty.setWordWrap(True)
        self._empty.setStyleSheet(f"color: {theme.LEGEND_DIM}; background: transparent;")
        veil = QVBoxLayout(self.table.viewport())
        veil.setContentsMargins(16, 0, 16, 0)
        veil.addWidget(self._empty)
        model = self.table.model()
        for sig in (model.rowsInserted, model.rowsRemoved, model.modelReset):
            sig.connect(self._sync_empty)
        self._sync_empty()

    def _sync_empty(self, *_args) -> None:
        self._empty.setVisible(self.table.rowCount() == 0)

    # ----- (de)serialisation -------------------------------------------
    def load(self, mappings: Dict[int, str]) -> None:
        self.table.setRowCount(0)
        self._fields.clear()
        for note in sorted(mappings):
            self.add_row(note, mappings[note])

    def to_mappings(self) -> Dict[int, str]:
        result: Dict[int, str] = {}
        for row in range(self.table.rowCount()):
            spin, path_edit = self._row_fields(row)
            if spin is None or path_edit is None:
                continue
            note = spin.value()
            path = path_edit.text().strip()
            if path:
                result[note] = path  # later rows win on duplicate notes
        return result

    # ----- row management ----------------------------------------------
    def add_row(self, note: int = 60, path: str = "") -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        spin = QSpinBox(self)
        spin.setRange(0, 127)
        spin.setValue(note)
        spin.setFont(theme.mono_font(13))
        spin.setAccessibleName("MIDI note number")

        name_edit = QLineEdit(note_name(note), self)
        name_edit.setFont(theme.mono_font(13))
        name_edit.setAlignment(Qt.AlignCenter)
        name_edit.setAccessibleName("Note name")
        name_edit.setToolTip("Note name, e.g. C3, F#2, Bb4 — stays in sync with the number")

        # Number -> name (always reflects the spin's value).
        spin.valueChanged.connect(lambda v, e=name_edit: e.setText(note_name(v)))
        # Name -> number (only when the typed name is valid; else revert).
        def _sync_name(s=spin, e=name_edit) -> None:
            parsed = parse_note_name(e.text())
            if parsed is None:
                e.setText(note_name(s.value()))
            else:
                s.setValue(parsed)
                e.setText(note_name(parsed))
        name_edit.editingFinished.connect(_sync_name)

        path_edit = QLineEdit(path, self)
        path_edit.setFont(theme.mono_font(13))
        path_edit.setPlaceholderText("path/to/clip.mp4")
        path_edit.setAccessibleName("Video file")

        browse = Key("Browse…", self)
        browse.clicked.connect(lambda _=False, pe=path_edit: self._browse(pe))
        test = Key("Test", self, glyph="play")
        test.setToolTip("Play this clip on the output now")
        test.clicked.connect(lambda _=False, s=spin: self.test_requested.emit(s.value()))
        remove = Key("", self, glyph="cross", variant="quiet", width=theme.KEY_H)
        remove.setAccessibleName("Remove mapping")
        remove.setToolTip("Remove this mapping")
        remove.clicked.connect(lambda _=False, w=spin: self._remove_row(w))

        actions = QWidget(self)
        a_layout = QHBoxLayout(actions)
        a_layout.setContentsMargins(_PAD, _PAD, _PAD, _PAD)
        a_layout.setSpacing(6)
        a_layout.addWidget(browse)
        a_layout.addWidget(test)
        a_layout.addWidget(remove)

        self.table.setCellWidget(row, _COL_NOTE, _padded(spin))
        self.table.setCellWidget(row, _COL_NAME, _padded(name_edit))
        self.table.setCellWidget(row, _COL_PATH, _padded(path_edit))
        self.table.setCellWidget(row, _COL_ACTIONS, actions)
        self.table.horizontalHeader().resizeSection(
            _COL_ACTIONS, actions.sizeHint().width()
        )
        self._fields[spin] = (spin, path_edit)

    def _row_fields(self, row: int):
        wrapper = self.table.cellWidget(row, _COL_NOTE)
        spin = wrapper.findChild(QSpinBox) if wrapper is not None else None
        return self._fields.get(spin, (None, None))

    def _remove_row(self, marker_widget: QWidget) -> None:
        for row in range(self.table.rowCount()):
            spin, _path = self._row_fields(row)
            if spin is marker_widget:
                self._fields.pop(spin, None)
                self.table.removeRow(row)
                return

    def _browse(self, path_edit: QLineEdit) -> None:
        root = self._get_video_root()
        start = root or str(Path.home())
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select video file",
            start,
            "Video files (*.mp4 *.mov *.mkv *.avi *.m4v *.webm *.wmv);;All files (*)",
        )
        if not selected:
            return
        path_edit.setText(self._relativise(selected, root))

    @staticmethod
    def _relativise(selected: str, root: str) -> str:
        """Store paths relative to the video root when possible, else absolute."""
        if not root:
            return selected
        try:
            return os.path.relpath(selected, root).replace(os.sep, "/")
        except ValueError:
            # Different drive on Windows -> keep absolute.
            return selected


def _padded(field: QWidget) -> QWidget:
    """Hold a cell editor with breathing room so the row line shows around it."""
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(_PAD, _PAD, _PAD, _PAD)
    lay.addWidget(field)
    return w
