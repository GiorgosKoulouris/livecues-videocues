"""Ask GitHub whether a newer release exists. Notifies only; never downloads.

One GET to the public ``/releases/latest`` endpoint, which already skips drafts
and pre-releases. The request runs on Qt's event loop, so it never blocks the
UI, and gives up after :data:`TIMEOUT_MS`. Every failure (offline, rate limit,
odd JSON) becomes an ``"error"`` result: the launch check stays silent about it,
and only a check the user asked for shows the reason.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from . import __version__

REPO = "GiorgosKoulouris/livecues-videocues"
LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"
TIMEOUT_MS = 5000

_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse_version(text: str) -> Optional[tuple[int, int, int]]:
    """``"v1.2.0"`` / ``"1.2.0"`` -> ``(1, 2, 0)``; anything else -> ``None``."""
    m = _VERSION_RE.match(text.strip())
    return tuple(int(g) for g in m.groups()) if m else None  # type: ignore[return-value]


@dataclass(frozen=True)
class UpdateResult:
    """Outcome of one check.

    ``status`` is ``"update"`` (``latest`` is newer than ``current``),
    ``"current"`` (nothing newer) or ``"error"`` (``message`` says why).
    ``manual`` is True when the user asked for the check.
    """

    status: str
    current: str
    manual: bool
    latest: str = ""
    page_url: str = RELEASES_PAGE
    notes: str = ""
    message: str = ""


def evaluate(payload: dict, current: str, manual: bool) -> UpdateResult:
    """Turn a ``/releases/latest`` JSON object into an :class:`UpdateResult`."""
    tag = str(payload.get("tag_name", ""))
    latest = parse_version(tag)
    mine = parse_version(current)
    if latest is None or mine is None:
        return UpdateResult("error", current, manual, message=f"Unrecognised version {tag or current!r}.")
    page = str(payload.get("html_url", ""))
    # Only ever hand the browser a page on this repo's GitHub.
    if not page.startswith(f"https://github.com/{REPO}/"):
        page = RELEASES_PAGE
    version = ".".join(map(str, latest))
    if latest <= mine:
        return UpdateResult("current", current, manual, latest=version, page_url=page)
    return UpdateResult(
        "update", current, manual,
        latest=version, page_url=page, notes=str(payload.get("body") or ""),
    )


class UpdateChecker(QObject):
    """Runs checks one at a time and reports each through :pyattr:`finished`."""

    finished = Signal(object)  # UpdateResult

    def __init__(self, parent: Optional[QObject] = None, *, url: str = LATEST_API,
                 current: str = __version__) -> None:
        super().__init__(parent)
        self._url = url
        self._current = current
        self._net = QNetworkAccessManager(self)
        self._reply: Optional[QNetworkReply] = None
        self._manual = False

    def is_busy(self) -> bool:
        return self._reply is not None

    def check(self, manual: bool = False) -> None:
        """Start a check. While one is running, a manual request upgrades it."""
        if self._reply is not None:
            self._manual = self._manual or manual
            return
        self._manual = manual
        req = QNetworkRequest(QUrl(self._url))
        req.setRawHeader(b"Accept", b"application/vnd.github+json")
        req.setRawHeader(b"User-Agent", f"LiveCues-VideoCues/{self._current}".encode())
        req.setTransferTimeout(TIMEOUT_MS)
        self._reply = self._net.get(req)
        self._reply.finished.connect(self._on_finished)

    def _on_finished(self) -> None:
        reply, self._reply = self._reply, None
        if reply is None:
            return
        reply.deleteLater()
        manual = self._manual
        if reply.error() != QNetworkReply.NoError:
            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            if status == 404:
                msg = "No releases have been published yet."
            elif reply.error() == QNetworkReply.OperationCanceledError:
                msg = "GitHub did not answer in time."
            else:
                msg = f"Could not reach GitHub ({reply.errorString()})."
            self.finished.emit(UpdateResult("error", self._current, manual, message=msg))
            return
        try:
            payload = json.loads(bytes(reply.readAll().data()).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("not an object")
        except ValueError:
            self.finished.emit(UpdateResult("error", self._current, manual,
                                            message="GitHub sent an unexpected answer."))
            return
        self.finished.emit(evaluate(payload, self._current, manual))
