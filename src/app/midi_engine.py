"""MIDI input handling.

Reads a MIDI input port (e.g. the virtual port exposed by the Windows rtpMIDI
driver) via ``mido``/``python-rtmidi`` and turns Note-On events into Qt signals.

``mido`` calls our callback on its own (non-Qt) thread; emitting Qt signals from
there is safe because Qt delivers them to the receiver's thread via a queued
connection.

``mido`` is imported lazily so the rest of the app (and the GUI) still loads on a
machine without a MIDI backend installed — :meth:`MidiEngine.available_devices`
just returns an empty list in that case.
"""
from __future__ import annotations

import re
from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from .config import ALL_CHANNELS

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Semitone offset within an octave for each letter (natural notes).
_LETTER_SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# e.g. "C4", "c#3", "Db-1", "F♯2" -> letter, accidental(s), octave
_NOTE_RE = re.compile(r"^\s*([A-Ga-g])\s*([#♯bB♭]*)\s*(-?\d+)\s*$")


def note_name(note: int) -> str:
    """MIDI note number -> name, using the common convention where 60 = C4."""
    if not 0 <= note <= 127:
        return str(note)
    return f"{_NOTE_NAMES[note % 12]}{note // 12 - 1}"


def parse_note_name(text: str) -> Optional[int]:
    """Parse a note name like ``C3``/``F#2``/``Db-1`` to a MIDI number.

    Returns ``None`` if the text isn't a recognisable note name in 0..127.
    Accepts ``#``/``♯`` for sharp and ``b``/``♭`` for flat (case-insensitive
    letter; ``b`` is only treated as flat when it follows a letter).
    """
    if text is None:
        return None
    match = _NOTE_RE.match(text)
    if not match:
        return None
    letter, accidentals, octave_str = match.groups()
    semitone = _LETTER_SEMITONES[letter.upper()]
    for acc in accidentals:
        if acc in "#♯":
            semitone += 1
        else:  # 'b', 'B' or '♭'
            semitone -= 1
    note = (int(octave_str) + 1) * 12 + semitone
    if not 0 <= note <= 127:
        return None
    return note


class MidiEngine(QObject):
    """Owns the open MIDI input port and emits high-level signals."""

    note_on = Signal(int, int)          # (note, velocity)
    midi_activity = Signal(str)         # human-readable line for the log
    status_changed = Signal(bool, str)  # (connected, detail)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._port = None
        self._device_name: str = ""
        self._channel: int = ALL_CHANNELS  # 0 = all, else 1..16

    # ----- device discovery --------------------------------------------
    @staticmethod
    def available_devices() -> List[str]:
        try:
            import mido
        except Exception:
            return []
        try:
            return list(mido.get_input_names())
        except Exception:
            return []

    @property
    def connected(self) -> bool:
        return self._port is not None

    @property
    def device_name(self) -> str:
        return self._device_name

    # ----- connection lifecycle ----------------------------------------
    def connect_device(self, device_name: str, channel: int) -> bool:
        """(Re)open ``device_name`` filtering on ``channel`` (0 = all)."""
        self.disconnect_device()
        self._channel = channel
        self._device_name = device_name or ""

        if not device_name:
            self.status_changed.emit(False, "No MIDI device selected")
            return False

        try:
            import mido
        except Exception as exc:  # pragma: no cover - environment dependent
            self.status_changed.emit(False, f"MIDI backend unavailable: {exc}")
            return False

        try:
            self._port = mido.open_input(device_name, callback=self._on_message)
        except Exception as exc:
            self._port = None
            self.status_changed.emit(False, f"Could not open '{device_name}': {exc}")
            return False

        self.status_changed.emit(True, self._status_detail())
        return True

    def disconnect_device(self) -> None:
        if self._port is not None:
            try:
                self._port.close()
            except Exception:
                pass
            self._port = None
            self.status_changed.emit(False, "Disconnected")

    def _status_detail(self) -> str:
        ch = "all channels" if self._channel == ALL_CHANNELS else f"channel {self._channel}"
        return f"Connected to '{self._device_name}' ({ch})"

    # ----- incoming messages (mido thread) -----------------------------
    def _on_message(self, msg) -> None:
        msg_type = getattr(msg, "type", "")
        if msg_type not in ("note_on", "note_off"):
            return

        # mido channels are 0..15; our config uses 1..16 (0 = all).
        if self._channel != ALL_CHANNELS and getattr(msg, "channel", -1) != self._channel - 1:
            return

        note = getattr(msg, "note", -1)
        velocity = getattr(msg, "velocity", 0)
        name = note_name(note)
        ch_label = getattr(msg, "channel", 0) + 1

        if msg_type == "note_on" and velocity > 0:
            self.midi_activity.emit(f"Note On  {name} ({note}) vel {velocity} ch {ch_label}")
            self.note_on.emit(note, velocity)
        else:
            # note_off, or note_on with velocity 0 (a common "off" encoding)
            self.midi_activity.emit(f"Note Off {name} ({note}) ch {ch_label}")
