# CLAUDE.md

Guidance for working in this repository. The project lives in `/workspace/src/`.

## Git rules (not negotiable)

**All work happens on the `dev` branch.** Before committing anything, confirm
with `git branch --show-current`; if it is not `dev`, switch to it (or branch off
it) first.

These are the **owner's** jobs, never the agent's:

- **Never commit directly to `main`.**
- **Never merge into `main`** (no `git merge`, no rebase onto it, no fast-forward,
  no PR merge).
- **Never push** — not `main`, not `dev`, not any branch, not tags. No
  `git push` at all, even when a commit went fine and pushing looks like the
  obvious next step.

Committing to `dev` is fine when asked. If a task seems to *require* touching
`main` or publishing anything, stop and hand it back to the owner instead.

**Commit messages carry no AI attribution.** Do not add `Co-Authored-By: Claude`
(or any other co-author trailer), do not add "Generated with…" footers, and do
not mention Claude, Anthropic, or any assistant in the subject, body, or
trailers. Write the message as the repository owner would: describe the change
itself and nothing about who or what produced it. The same applies to anything
else that ends up published — tags, PR descriptions, release notes.

## What this is

**LiveCues VideoCues** (short code **LCVC**) — part of the LiveCues toolkit,
alongside `livecues-reaper-remote` (a separate repo; don't touch it from here). A Windows desktop app that listens to MIDI (including
**RTP-MIDI** over the network) and plays a video clip on a projector / second
display when a configured MIDI note arrives. Python + PySide6 (Qt). Packaged to
a standalone `.exe` with PyInstaller.

## Critical constraint: Linux dev box, Windows target

This devcontainer is **Linux**, but the app targets **Windows**. You can author
and headlessly smoke-test code here, but:

- **The `.exe` build, real RTP-MIDI input, and anything you have to *see* (the
  projector output, fullscreen, display placement) must be verified on
  Windows** — PyInstaller does not cross-compile and this container is headless.
- **Windows Python version matters:** `python-rtmidi` only ships prebuilt
  Windows wheels for **Python 3.10–3.12** (1.5.8 is the latest release, no
  3.13/3.14 wheels). Two supported paths, both documented in README
  *Troubleshooting*:
  - **Python 3.12 (simplest):** `py -3.12 -m venv winvenv` → installs from
    wheels, no compiler.
  - **Python 3.14 (build from source):** install *Build Tools for Visual Studio*
    with the **"Desktop development with C++"** workload (MSVC + Windows SDK),
    then `py -3.14 -m venv winvenv` and `pip install -r src\requirements.txt` —
    `python-rtmidi` compiles against MSVC; `PySide6` (abi3) and `mido` install
    normally. Use this when the user wants/needs 3.14. The owner's checkout is on
    3.14, so `winvenv` is the environment that actually exists on the Windows
    side; it's created at the **repo root**, not inside `src/`.
- **Video playback works in this container** (offscreen): the devcontainer
  installs `libxrandr2`, which PySide6's `libffmpegmediaplugin.so` links
  against — without it Qt Multimedia reports *"No QtMultimedia backends found"*
  and `QMediaPlayer`/`QVideoSink` never construct. Clips decode and `EndOfMedia`
  fires, so the idle / trigger / return-to-idle logic is fully testable here; you just can't
  see or hear the output.
- **MIDI input cannot be tested here** — there is no ALSA sequencer
  (`/dev/snd/seq`), so `mido.get_input_names()` raises and
  `MidiEngine.available_devices()` returns `[]` (it swallows the error by
  design). Exercise triggering via the **Ctrl+T** hotkey / `App._play_note(note)`
  instead. Real MIDI is a Windows-target concern.

## Layout

```
app/
  main.py            entry + signal wiring + hotkeys (Ctrl+B/F/T, Esc)  -> App class
  config.py          Config dataclass; JSON load/save in %APPDATA% (atomic, forgiving)
  paths.py           %APPDATA% + bundled-asset resolution (PyInstaller _MEIPASS aware)
  midi_engine.py     MidiEngine(QObject): MIDI port -> Qt signals; note_name()/parse_note_name() helpers
  video_window.py    VideoWindow: output window (Ctrl+F toggles fullscreen, resizable); fill-by-default video with manual zoom/pan/per-side crop; idle loop / trigger / return-to-idle; remembers its own placement
  control_window.py  ControlWindow: top bar + Run / Edit tabs over a QStackedWidget
  mapping_editor.py  MappingEditor: note -> video table widget (note # spinbox + synced note-name field)
  theme.py           Suite look: colour tokens, Plex fonts, palette + style sheet, drawn Key / Tab / StateChip / Tick
run.py               entry script (also the PyInstaller entry point)
app.spec             PyInstaller build spec (run on Windows)
requirements.txt     PySide6, mido, python-rtmidi
assets/              app icon (app.svg/png/ico), fonts/ (IBM Plex TTFs + OFL), ui/ (spinbox/combo arrows), optional idle video; `*.mp4` here is
                     gitignored, so any clips are local fixtures (app.spec still bundles
                     whatever is in the folder at build time)
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
- **Config** persists to `%APPDATA%\LiveCues\VideoCues\config.json` and must
  survive app/system restarts. The folder is fixed in `paths.CONFIG_SUBDIR`, not
  derived from `APP_NAME`. `Config.load()` first calls
  `paths.migrate_legacy_config()`, which copies a pre-1.1 `%APPDATA%\Video Cues\config.json`
  across once if the new file is missing (the old folder stays as a backup). Keep `Config.from_dict` forgiving (ignore unknown
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
  `VideoWindow.return_to_idle()` is a no-op while the idle loop is already
  playing, so a double press doesn't restart it from the top.
- **Output state feedback**: `VideoWindow.idle_state_changed(bool)` →
  `ControlWindow.set_output_idle` sinks the Return to Idle key in LED red. It
  tracks the *actual* output (emitted from `play_idle`/`trigger`), so a trigger
  that fails on a missing file correctly leaves the button red.
- **Window placement** persists as `output_screen` + `window_{x,y,width,height}`
  + `output_fullscreen`. `VideoWindow` owns the live state and reports it via
  `window_state_changed` → `App._on_window_state_changed` → config. Three things
  to preserve when touching this: saves are **debounced** (`_save_timer`,
  `_GEOMETRY_SAVE_DELAY_MS`) because dragging emits a burst of events and each
  save rewrites the JSON; `_restoring` suppresses tracking while *we* position
  the window, and `_remember_placement` additionally refuses to capture a rect
  while `_fullscreen` is set — Qt reports the fullscreen geometry through
  move/resize events *before* `isFullScreen()` flips, which would otherwise
  overwrite the windowed rect; and `apply_window_state` drops a saved rect that
  no longer overlaps a connected screen (`_rect_is_reachable`) so an unplugged
  projector can't strand the window off-screen.
- **Window lifecycle**: the control window *is* the app — `ControlWindow.closeEvent`
  emits `closing` → `App._on_control_closed` closes the output window, disconnects
  MIDI, and quits. (Qt only auto-quits when the *last* window closes, so without
  this the app keeps running headless behind a closed control window.) Closing the
  **output** window alone is recoverable instead: it stops playback, reports idle,
  and `VideoWindow.show_output()` (Run-tab **Show Output** key) reopens it
  at its saved placement and restarts the idle loop. `trigger()` reopens a closed
  output on its own so a cue can never land on a window that isn't there.
- **Editing config must not drop unlisted fields**: `ControlWindow._save`
  starts from `self._config.copy()` and overwrites only the form's own fields.
  Rebuilding a fresh `Config(...)` there would silently reset the view transform
  and window placement, which the Edit tab doesn't show.
- **Output placement**: the output window opens at its remembered size/position
  (Ctrl+F / Fullscreen button toggles fullscreen). The video **fills** the output by default — the
  `QVideoWidget` uses `KeepAspectRatioByExpanding` (cover, no black bars) and is
  positioned manually (`VideoWindow._apply_geometry`) so it can be zoomed,
  panned, and **per-side cropped**, clipped to the window. A crop extends the
  video past that window edge (so the window clips it) while the opposite edge
  still reaches the window — cropping never introduces black gaps. Move / zoom /
  crop controls live on the control window's Run tab; values persist as
  `video_zoom`/`video_offset_x`/`video_offset_y`/`video_crop_{left,right,top,bottom}`
  (offsets and crops are fractions of window size). The per-click Move and Zoom
  increments are user-configurable (Run-tab **Step** spinboxes, defaults 2%
  and ±10%) and persist as `move_step`/`zoom_step`; they reach the video via
  `VideoWindow.set_move_step`/`set_zoom_step` (separate from the transform — not
  part of `view_dict`). `VideoWindow._update` is the single clamped setter;
  `view_changed` emits a **dict** of the full transform.
  Flow: control buttons (`pan_requested`/`zoom_*_requested`/`crop_requested`/
  `reset_view_requested`) → `VideoWindow` methods → `view_changed` →
  `App._on_view_changed` (saves + syncs control's config copy). Saved transforms
  are re-applied via `VideoWindow.apply_view(config.view_dict())`.

## Look (LiveCues suite design)

The control window follows the suite design system of `livecues-reaper-remote`
("The Silkscreen Desk"); `/workspace/DESIGN.md` records how it maps onto Qt.
Everything visual lives in `app/theme.py`:

- **Colours are tokens** (`theme.CHASSIS`, `theme.SIGNAL`, …). Never hard-code a
  hex in a widget; never add a new hue.
- **Fonts are QFont objects, not style-sheet rules.** QSS can't do letter-spacing,
  and a QSS `font` rule overrides `setFont`. Use `theme.ui_font` / `mono_font` /
  `legend_font`; labels printed on the panel go through `theme.legend()`.
- **Buttons are `theme.Key`**, not QPushButton (QSS can't chamfer). One
  `variant="lit"` key per view at most (Save on Edit); `set_sunk(True)` is the red
  "on" state (Return to Idle at idle); `hint=` prints a hotkey; `glyph=` draws a
  symbol (no Unicode arrows or ✕ in key text). Focus rings show for keyboard focus
  only.
- State is a drawn shape plus a word (`theme.StateChip`), never colour alone.
- The output (`VideoWindow`) stays plain black; the theme is for the control window.

## Locked product behavior (don't change without asking)

Play once → idle · new note interrupts · looping idle video · audio muted by
default · Note-Off ignored (Note-On only) · hotkeys Ctrl+B / Ctrl+F / Ctrl+T +
bare Esc · Return to Idle button red whenever the idle loop owns the output ·
on-screen MIDI activity log.

There is no blackout *mode*: **Return to Idle** (button / Ctrl+B) is a plain
action that drops the current clip and resumes the idle loop, and a MIDI note
always takes over from idle without anything to exit first. True black happens
only when no idle video is configured. Don't reintroduce a latched blackout
state unless asked.

## Working here

- **Use the project venv at `/workspace/src/.venv`** (Python 3.14) — it has
  `PySide6`, `mido` *and* `python-rtmidi` installed, so just call
  `/workspace/src/.venv/bin/python`; no need to create a venv or pip-install for
  routine work. `python-rtmidi` has no 3.14 wheel, so it was compiled from source
  here — that works because the image ships `libasound2-dev` + `pkg-config`. To
  rebuild the venv from scratch:
  `cd /workspace/src && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
- **Ignore `/workspace/winvenv`** — that is the *Windows* venv from the host
  checkout (`Scripts\python.exe`, CPython 3.14.6, and PyInstaller for building
  the `.exe`). It is visible over the bind mount but unusable on Linux; the only
  venv to run here is `/workspace/src/.venv`. Never create a venv at the repo
  root — root is Windows territory, `src/.venv` is ours.
- Run from source: `/workspace/src/.venv/bin/python run.py` (or `... -m app.main`).
- `QT_QPA_PLATFORM=offscreen` and `QT_LOGGING_RULES` are already set in the image,
  so the app runs headless out of the box. Two harmless messages remain and are
  **not** bugs: `PulseAudioService: pa_context_connect() failed` (no audio server
  in the container; audio is muted by default and playback is unaffected) and
  `This plugin does not support propagateSizeHints()/raise()` (inherent to the
  offscreen platform plugin).
- Headless smoke test: instantiate `App(qapp)` and exercise config roundtrip,
  signal wiring, and a real trigger. Point the config somewhere disposable with
  `XDG_CONFIG_HOME=$(mktemp -d)` — on Linux `paths.config_file()` resolves to
  `$XDG_CONFIG_HOME/LiveCues/VideoCues/config.json` (the Windows `%APPDATA%` equivalent),
  so tests don't clobber a real config. Give the transform/playback a moment:
  drive assertions from `QTimer.singleShot` inside `qapp.exec()`, not inline.
- The image installs only what PySide6 loads offscreen (`libglib2.0-0 libgl1
  libegl1 libxkbcommon0 libdbus-1-3 libfontconfig1 libfreetype6 libx11-6
  libx11-xcb1 libxcb1 libxext6 libxrender1 libxrandr2 libpulse0`). The Qt **xcb**
  platform plugin is deliberately *not* satisfied — if you ever want a visible GUI
  over X11/VNC, add back `libxcb-cursor0 libxcb-icccm4 libxcb-image0
  libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-render0 libxcb-shape0
  libxcb-shm0 libxcb-sync1 libxcb-util1 libxcb-xfixes0 libxcb-xkb1
  libxkbcommon-x11-0` and unset `QT_QPA_PLATFORM`.
- Build (Windows only): `pip install -r requirements.txt pyinstaller` then
  `pyinstaller app.spec` → `dist\VideoCues.exe` (the exe name was deliberately kept through the LiveCues rename; **one-file** build; that single
  `.exe` is the distributable). Keep `upx=False` — UPX corrupts the bundled
  Qt/FFmpeg DLLs — and keep the `hiddenimports` for `rtmidi` /
  `mido.backends.rtmidi`, which mido loads dynamically.

## Conventions

- Keep modules small and single-responsibility as above; UI strings and behavior
  live with their widget. Match the existing PySide6 import style and the
  `from __future__ import annotations` + typed-signature pattern used throughout.
