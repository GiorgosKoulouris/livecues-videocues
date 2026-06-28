"""Filesystem locations: per-user config dir and bundled asset resolution.

Works the same when run from source and when frozen by PyInstaller.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from . import APP_NAME


def config_dir() -> Path:
    """Per-user, writable config directory that survives app/system restarts.

    Windows -> %APPDATA%\\Video Cues
    Other   -> $XDG_CONFIG_HOME/Video Cues (or ~/.config/...)
    """
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
            os.path.expanduser("~"), ".config"
        )
    return Path(base) / APP_NAME


def config_file() -> Path:
    return config_dir() / "config.json"


def resource_dir() -> Path:
    """Directory of bundled read-only assets.

    When frozen by PyInstaller, data is unpacked under ``sys._MEIPASS``.
    When run from source, assets live next to the package.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent.parent


def asset(*parts: str) -> Path:
    return resource_dir().joinpath("assets", *parts)
