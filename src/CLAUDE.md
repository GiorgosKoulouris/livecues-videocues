# CLAUDE.md

Guidance for working in this repository. The project lives in `/workspace/src/`.

## What this is

**Video Cues** — a Windows desktop app that listens to MIDI (including
**RTP-MIDI** over the network) and plays a video clip on a projector / second
display when a configured MIDI note arrives. Python + PySide6 (Qt). Packaged to
a standalone `.exe` with PyInstaller.

## Critical constraint: Linux dev box, Windows target

This devcontainer is **Linux**, but the app targets **Windows**. You can author
and headlessly smoke-test code here, but:

- **The `.exe` build and real RTP-MIDI + video playback must be verified on
  Windows** — PyInstaller does not cross-compile.
- **Windows Python version matters:** `python-rtmidi` only ships prebuilt
  Windows wheels for **Python 3.10–3.12** (1.5.8 is the latest release, no
  3.13/3.14 wheels). Two supported paths, both documented in README
  *Troubleshooting*:
  - **Python 3.12 (simplest):** `py -3.12 -m venv .venv` → installs from wheels,
    no compiler.
  - **Python 3.14 (build from source):** install *Build Tools for Visual Studio*
    with the **"Desktop development with C++"** workload (MSVC + Windows SDK),
    then `py -3.14 -m venv .venv` and `pip install -r requirements.txt` —
    `python-rtmidi` compiles against MSVC; `PySide6` (abi3) and `mido` install
    normally. Use this when the user wants/needs 3.14.
- In this container, `python-rtmidi` may not be installed (needs ALSA headers),
  and **Qt Multimedia has no media backend** — expect
  `qt.multimedia.symbolsresolver: Couldn't load pipewire` / `No QtMultimedia
  backends found` warnings. These are environmental and **do not** indicate a
  bug; on Windows PySide6 ships the FFmpeg backend (bundled via `app.spec`).

## Layout

```
app/
  main.py            entry + signal wiring + hotkeys (B/F/T/Esc)  -> App class
  config.py          Config dataclass; JSON load/save in %APPDATA% (atomic, forgiving)
  paths.py           %APPDATA% + bundled-asset resolution (PyInstaller _MEIPASS aware)
  midi_engine.py     MidiEngine(QObject): MIDI port -> Qt signals; note_name()/parse_note_name() helpers
  video_window.py    VideoWindow: windowed-by-default output (F toggles fullscreen, resizable); fill-by-default video with manual zoom/pan/per-side crop; idle loop / trigger / blackout
  control_window.py  ControlWindow: Status view + Edit view (QStackedWidget)
  mapping_editor.py  MappingEditor: note -> video table widget (note # spinbox + synced note-name field)
run.py               entry script (also the PyInstaller entry point)
app.spec             PyInstaller build spec (run on Windows)
requirements.txt     PySide6, mido, python-rtmidi
assets/              bundled idle/placeholder videos + app icon (app.svg/png/ico)
```

The app icon is `assets/app.svg` (source); `app.png` (runtime window icon, set via
`QApplication.setWindowIcon` in `main.py`) and the multi-size `app.ico` (Windows
`.exe` icon, wired in `app.spec`) are rendered from it. To regenerate after editing
the SVG, run `python assets/build_icon.py` (Qt-only, no Pillow) → it rewrites both.

## Architecture notes

- `App` (in `main.py`) owns live state and connects everything. Signal flow:
  `MidiEngine.note_on` → `App._on_note_on` → `App._play_note` →
  `VideoWindow.trigger`. Config edits flow `ControlWindow.config_changed` →
  `App._apply_config` (saves to disk + re-applies MIDI/output live).
- **Config** persists to `%APPDATA%\Video Cues\config.json` and must
  survive app/system restarts. Keep `Config.from_dict` forgiving (ignore unknown
  keys, default missing ones, drop invalid notes) so old configs keep loading.
  Mapping values are paths **relative to `video_root`** (absolute also accepted).
- **MIDI**: `midi_channel` `0` = all channels, `1..16` = specific (mido channels
  are 0-based, so compare `msg.channel == channel - 1`). The mido callback runs
  on a non-Qt thread; emitting Qt signals from it is intentional and safe
  (queued delivery). `mido` is imported lazily so the GUI still loads without a
  MIDI backend.
- **RTP-MIDI** is handled by the external **rtpMIDI driver (Tobias Erichsen)**,
  not in-process — the app just reads the virtual MIDI port it exposes. Don't
  reintroduce an in-process AppleMIDI stack unless asked.
- **Video**: Qt Multimedia (`QMediaPlayer`/`QVideoWidget`). Idle video loops
  (`Loops.Infinite`); a trigger plays once (`Loops.Once`) and returns to idle on
  `EndOfMedia`. No idle video set → black screen. Audio muted by default.
- **Output placement**: the output window opens **windowed by default** (F /
  Fullscreen button toggles). The video **fills** the output by default — the
  `QVideoWidget` uses `KeepAspectRatioByExpanding` (cover, no black bars) and is
  positioned manually (`VideoWindow._apply_geometry`) so it can be zoomed,
  panned, and **per-side cropped**, clipped to the window. A crop extends the
  video past that window edge (so the window clips it) while the opposite edge
  still reaches the window — cropping never introduces black gaps. Move / zoom /
  crop controls live on the control window's Status page; values persist as
  `video_zoom`/`video_offset_x`/`video_offset_y`/`video_crop_{left,right,top,bottom}`
  (offsets and crops are fractions of window size). The per-click Move and Zoom
  increments are user-configurable (Status-page **Step** spinboxes, defaults 2%
  and ±10%) and persist as `move_step`/`zoom_step`; they reach the video via
  `VideoWindow.set_move_step`/`set_zoom_step` (separate from the transform — not
  part of `view_dict`). `VideoWindow._update` is the single clamped setter;
  `view_changed` emits a **dict** of the full transform.
  Flow: control buttons (`pan_requested`/`zoom_*_requested`/`crop_requested`/
  `reset_view_requested`) → `VideoWindow` methods → `view_changed` →
  `App._on_view_changed` (saves + syncs control's config copy). Saved transforms
  are re-applied via `VideoWindow.apply_view(config.view_dict())`.

## Locked product behavior (don't change without asking)

Play once → idle · new note interrupts · looping idle video · audio muted by
default · Note-Off ignored (Note-On only) · hotkeys B/F/T/Esc · on-screen MIDI
activity log.

## Working here

- **Use the project venv at `/workspace/.venv`** — it already has `PySide6` and
  `mido` installed, so just call `/workspace/.venv/bin/python` (no need to create
  a venv or pip-install for routine work). `python-rtmidi` is intentionally NOT
  installed here (it can't build on Linux without ALSA headers and isn't needed
  for offscreen GUI work — `mido` is imported lazily). If the mounted `.venv` is
  ever empty or root-owned after a container reset, rebuild it:
  `sudo chown -R vscode:vscode /workspace/.venv && python3 -m venv /workspace/.venv && /workspace/.venv/bin/pip install PySide6 mido`.
- Run from source: `/workspace/.venv/bin/python run.py` (or `... -m app.main`).
- Headless smoke test in this container: set `QT_QPA_PLATFORM=offscreen`, then
  instantiate `App` and exercise config roundtrip + signal wiring. PySide6 needs
  these system libs (already installed here, reinstall if the container resets):
  `libglib2.0-0 libgl1 libegl1 libdbus-1-3 libxkbcommon0 fontconfig libpulse0`.
  Expect harmless QtMultimedia "no backend" warnings — filter them out.
- Build (Windows only): `pip install -r requirements.txt pyinstaller` then
  `pyinstaller app.spec` → `dist\VideoCues\VideoCues.exe`.

## Conventions

- Keep modules small and single-responsibility as above; UI strings and behavior
  live with their widget. Match the existing PySide6 import style and the
  `from __future__ import annotations` + typed-signature pattern used throughout.
