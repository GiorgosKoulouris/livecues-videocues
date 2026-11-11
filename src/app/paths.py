"""Filesystem locations: per-user config dir and bundled asset resolution.

Works the same when run from source and when frozen by PyInstaller.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# Config lives under a shared "LiveCues" folder, one subfolder per app. This is
# deliberately decoupled from APP_NAME so a display-name change never moves it.
CONFIG_SUBDIR = ("LiveCues", "VideoCues")
# Where releases up to 1.0.x kept the config, before the LiveCues rename.
LEGACY_CONFIG_SUBDIR = ("Video Cues",)


def _config_base() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
            os.path.expanduser("~"), ".config"
        )
    return Path(base)


def config_dir() -> Path:
    """Per-user, writable config directory that survives app/system restarts.

    Windows -> %APPDATA%\\LiveCues\\VideoCues
    Other   -> $XDG_CONFIG_HOME/LiveCues/VideoCues (or ~/.config/...)
    """
    return _config_base().joinpath(*CONFIG_SUBDIR)


def config_file() -> Path:
    return config_dir() / "config.json"


def legacy_config_file() -> Path:
    return _config_base().joinpath(*LEGACY_CONFIG_SUBDIR, "config.json")


def migrate_legacy_config() -> bool:
    """One-time copy of a pre-rename config into the new location.

    Copies only when the new config is missing and the legacy one exists; the
    legacy folder is left untouched as a backup. Returns True if it copied.
    """
    new, old = config_file(), legacy_config_file()
    if new.exists() or not old.is_file():
        return False
    try:
        new.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old, new)
    except OSError:
        return False
    return True


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
