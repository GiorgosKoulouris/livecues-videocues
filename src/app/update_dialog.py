"""The small dialog a manual update check (or the badge) opens."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QTextBrowser, QVBoxLayout, QWidget

from . import theme
from .theme import Key, StateChip
from .updates import UpdateResult


class UpdateDialog(QDialog):
    """Current → latest, the release notes, and a link to the download page."""

    def __init__(self, result: UpdateResult, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Updates")
        self.setMinimumWidth(460)
        col = QVBoxLayout(self)
        col.setContentsMargins(18, 18, 18, 18)
        col.setSpacing(10)

        chip = StateChip(self)
        if result.status == "update":
            chip.set_state("ring", theme.WARN_AMBER, "Update available", theme.WARN_AMBER)
        elif result.status == "current":
            chip.set_state("disc", theme.LED_GREEN, "Up to date")
        else:
            chip.set_state("ring", theme.WARN_AMBER, "Check failed", theme.WARN_AMBER)
        col.addWidget(chip)

        if result.status == "update":
            line = f"You have {result.current}. Version {result.latest} is available."
        elif result.status == "current":
            line = f"You're on the latest version ({result.current})."
        else:
            line = result.message or "The update check failed."
        text = QLabel(line, self)
        text.setFont(theme.ui_font(14))
        text.setWordWrap(True)
        col.addWidget(text)

        if result.status == "update" and result.notes.strip():
            col.addWidget(theme.legend("Release notes", self))
            notes = QTextBrowser(self)
            notes.setOpenExternalLinks(True)
            notes.setMarkdown(result.notes)
            notes.setMinimumHeight(220)
            col.addWidget(notes, stretch=1)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addStretch(1)
        close = Key("Close", self)
        close.clicked.connect(self.reject)
        buttons.addWidget(close)
        if result.status == "update":
            open_page = Key("Open download page", self, variant="lit")
            open_page.clicked.connect(lambda: self._open(result.page_url))
            buttons.addWidget(open_page)
        col.addLayout(buttons)

    def _open(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))
        self.accept()
