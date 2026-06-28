"""Editable note -> video mapping table used by the Edit view."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QWidget,
)

from .midi_engine import note_name, parse_note_name

_COL_NOTE = 0
_COL_NAME = 1
_COL_PATH = 2
_COL_ACTIONS = 3


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

        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(
            ["Note #", "Note name", "Video file (relative to root)", ""]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(_COL_NOTE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(_COL_PATH, QHeaderView.Stretch)
        header.setSectionResizeMode(_COL_ACTIONS, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)

        add_btn = QPushButton("+ Add mapping", self)
        add_btn.clicked.connect(lambda: self.add_row())

        layout = QHBoxLayout()
        layout.addWidget(add_btn)
        layout.addStretch(1)

        from PySide6.QtWidgets import QVBoxLayout

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.table)
        outer.addLayout(layout)

    # ----- (de)serialisation -------------------------------------------
    def load(self, mappings: Dict[int, str]) -> None:
        self.table.setRowCount(0)
        for note in sorted(mappings):
            self.add_row(note, mappings[note])

    def to_mappings(self) -> Dict[int, str]:
        result: Dict[int, str] = {}
        for row in range(self.table.rowCount()):
            spin = self.table.cellWidget(row, _COL_NOTE)
            path_edit = self.table.cellWidget(row, _COL_PATH)
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

        name_edit = QLineEdit(note_name(note), self)
        name_edit.setAlignment(Qt.AlignCenter)
        name_edit.setFixedWidth(72)
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
        path_edit.setPlaceholderText("path/to/clip.mp4")

        browse = QPushButton("Browse…", self)
        browse.clicked.connect(lambda _=False, pe=path_edit: self._browse(pe))
        test = QPushButton("Test", self)
        test.clicked.connect(lambda _=False, s=spin: self.test_requested.emit(s.value()))
        remove = QPushButton("✕", self)
        remove.setFixedWidth(28)
        remove.clicked.connect(lambda _=False, w=spin: self._remove_row(w))

        actions = QWidget(self)
        a_layout = QHBoxLayout(actions)
        a_layout.setContentsMargins(0, 0, 0, 0)
        a_layout.addWidget(browse)
        a_layout.addWidget(test)
        a_layout.addWidget(remove)

        self.table.setCellWidget(row, _COL_NOTE, spin)
        self.table.setCellWidget(row, _COL_NAME, name_edit)
        self.table.setCellWidget(row, _COL_PATH, path_edit)
        self.table.setCellWidget(row, _COL_ACTIONS, actions)

    def _remove_row(self, marker_widget: QWidget) -> None:
        for row in range(self.table.rowCount()):
            if self.table.cellWidget(row, _COL_NOTE) is marker_widget:
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
