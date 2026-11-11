<img src="src/assets/app.png" alt="LiveCues VideoCues" width="96" align="left" />

# LiveCues VideoCues

Part of the LiveCues toolkit, alongside
[LiveCues ReaperRemote](https://github.com/GiorgosKoulouris/livecues-reaper-remote).

A Windows desktop app that listens to MIDI (including **RTP-MIDI** over the
network) and plays a video clip on a projector / second display whenever a
configured MIDI note arrives.

<br clear="left" />

- **Run tab** — live MIDI connection, what is on the output (now playing, beside
  **Return to Idle**), device, channel and output display, the output placement
  controls, and a scrolling MIDI activity log.
- **Edit tab** — configure the note → video mappings, video root folder, idle
  (loop) video, MIDI device, MIDI channel, output display, and audio mute. Each
  mapping accepts the note as either a **MIDI number** (0–127) or a **note name**
  (e.g. `C3`, `F#2`, `Bb4`) — the two fields stay in sync. **Save** applies the
  changes; leaving for the Run tab with unsaved changes asks first.
  The tab also shows the app version and **Check for updates** (see *Updates*).
- **Output window** — opens as a resizable, movable window on the display of your
  choice (projector / second monitor); press **Ctrl+F** (or use the Fullscreen
  button) to toggle fullscreen. The video **fills** the output by default (no black bars).
  Use the **Output position, zoom & crop** controls on the Run tab to move,
  zoom, and crop each edge of the video on the display (handy for projector
  alignment); the placement is saved. Plays a looping idle video when nothing is
  triggered; a note interrupts with its clip, plays once, then returns to idle.
  The window's **size, position, display, and fullscreen state are remembered**
  and restored on the next run — including when you drag it onto another
  monitor, which updates the saved output display. If you close it, **Show
  Output** brings it back where it was (an incoming MIDI cue reopens it too);
  closing the **control** window quits the whole app, output included.
- Configuration is stored in `%APPDATA%\LiveCues\VideoCues\config.json` and
  **survives app and system restarts**.

## Download

Grab `VideoCues-X.Y.Z-win64.exe` from the
[latest release](https://github.com/GiorgosKoulouris/livecues-videocues/releases/latest).
It is a single file with nothing to install: put it anywhere and run it.

- **"Windows protected your PC"**: the exe isn't code-signed, so SmartScreen
  warns on first run. Click **More info → Run anyway**.
- **Check the download** (optional): each release lists the exe's SHA-256 in
  `SHA256SUMS.txt`. In PowerShell, `Get-FileHash VideoCues-X.Y.Z-win64.exe`
  should print the same hash.

### Updates

At launch the app asks GitHub (`api.github.com`) once whether a newer release
exists. Nothing else is sent, and when offline it stays silent. If there is
one, the Edit tab shows an **Update available** badge next to the version;
it never interrupts the Run tab. **Check for updates** on the Edit tab checks
on demand. Either one opens a short dialog with the release notes and a link
to the download page. The app never downloads or installs anything itself:
download the new exe and replace the old one. Pre-releases are never offered.

## Look

The control window uses the LiveCues suite design shared with
[LiveCues ReaperRemote](https://github.com/GiorgosKoulouris/livecues-reaper-remote):
a flat, dark-only panel with small spaced-capital labels, one signal orange for
the selected tab, keyboard focus and the one highlighted key, and green / red /
amber only for state, always next to a shape or a word. See [DESIGN.md](DESIGN.md).

## How triggering behaves

| Situation | Behaviour |
|-----------|-----------|
| Mapped Note-On received | Plays the clip once, then returns to the idle loop |
| New note while a clip is playing | Interrupts immediately and plays the new clip |
| Nothing playing | Loops the configured idle video (or black if none set) |
| **Return to Idle** pressed | Drops the current clip and resumes the idle loop at once |
| Note arrives with the output window closed | Reopens the output where it was, then plays the clip |
| Audio | Muted by default; toggle in the Edit tab |
| Note-Off | Ignored (only Note-On triggers) |

The **Return to Idle** button turns **red whenever the idle loop is on the
output** — i.e. whenever no cue is playing — and the output readout beside it
says **Idle on output**, so a glance at the control window tells you nothing is
currently on the projector. A MIDI note always takes over
from the idle loop; there is no mode to exit first.

## Hotkeys

Modifier-based so a stray keypress during a show can't change what the audience
sees:

| Key | Action |
|-----|--------|
| **Ctrl+B** | Return to Idle (stop the current clip, resume the idle loop) |
| **Ctrl+F** | Toggle fullscreen of the output window |
| **Ctrl+T** | Test-trigger the first mapping (no MIDI needed; each mapping row also has a Test key) |
| **Esc** | Exit fullscreen |

## RTP-MIDI setup (Windows)

The app reads ordinary Windows MIDI input ports. To receive **network MIDI**,
install the free **rtpMIDI** driver by Tobias Erichsen
(<https://www.tobias-erichsen.de/software/rtpmidi.html>):

1. Install rtpMIDI and open it.
2. Create a session (e.g. *"Session 1"`) and enable it.
3. Connect your remote MIDI source to that session (directory / "Connect").
4. In **LiveCues VideoCues → Edit → MIDI device**, select the matching port
   (e.g. `rtpMIDI Session 1` / `Network`), set the channel, and **Save**.

> Alternative: a fully in-process AppleMIDI implementation (`pymidi`) is possible
> but the rtpMIDI driver is far more robust and is the recommended path.

## Run from source

The application code lives in the [`src/`](src) folder; the virtual environments
live **outside** it:

| Environment | Where | What it is for |
|-------------|-------|----------------|
| `winvenv/` | repo root | The **Windows** venv — running the app for real and building the `.exe` |
| `src/.venv` | inside `src/` | The **Linux** venv used by the dev container (see below) |

Keeping them apart means the same checkout can be used from Windows and from the
Linux dev container at the same time without the two treading on each other.
Both are gitignored.

### Windows

1. Install **Python 3.10–3.12** from <https://www.python.org/downloads/> — tick
   *"Add python.exe to PATH"* during setup.

   > Use **3.12 or older** for the easy path. `python-rtmidi` only publishes
   > prebuilt Windows wheels up to Python 3.12; on **3.13+** pip falls back to a
   > source build that needs the Visual Studio C++ compiler (see *Using Python
   > 3.14* and *Troubleshooting* below). If you have several Pythons installed,
   > create the venv explicitly with `py -3.12 -m venv winvenv`.
2. Open **Command Prompt** (or PowerShell), clone the repo, and from the **repo
   root** create the venv and install:

   ```bat
   git clone https://github.com/GiorgosKoulouris/livecues-videocues.git
   cd livecues-videocues
   py -3.12 -m venv winvenv
   winvenv\Scripts\activate
   pip install -r src\requirements-lock.txt
   cd src
   python run.py
   ```

   In **PowerShell**, activate with `.\winvenv\Scripts\Activate.ps1` instead. If
   activation is blocked, run
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and retry.
3. The app launches with the control window. Use the **Edit** tab to set
   the MIDI device, channel, output display, video root, idle video, and the
   note → video mappings, then **Save**. See *RTP-MIDI setup* above for network
   MIDI.

> `python run.py` must be started from the `src` folder (or as
> `python src\run.py`) — `run.py` imports the `app` package next to it.

> On Python 3.10–3.12, `PySide6` and `python-rtmidi` both install from prebuilt
> Windows wheels, so no compiler is required.

#### Troubleshooting: `python-rtmidi` build error on Windows

If `pip install` fails on `python-rtmidi` with
`ERROR: Unknown compiler(s): [['cl'], ...]` / `metadata-generation-failed`, pip
is trying to **compile it from source** because your Python is newer than the
available wheels (no wheels for 3.13/3.14). Pick one:

- **Use Python 3.12 (recommended):** install Python 3.12, then recreate the
  venv with `py -3.12 -m venv winvenv` and reinstall. `python-rtmidi` installs
  from a wheel — no compiler needed.
- **Compile from source:** install *Build Tools for Visual Studio* with the
  *"Desktop development with C++"* workload, then retry the install.

#### Using Python 3.14 on Windows

Python 3.14 has no prebuilt `python-rtmidi` wheel, so pip must **compile it from
source**. This works once a C++ compiler is available:

1. Install **Build Tools for Visual Studio**
   (<https://visualstudio.microsoft.com/visual-cpp-build-tools/>) and select the
   **"Desktop development with C++"** workload (MSVC compiler + Windows SDK).
   Reboot if prompted.
2. Open a **fresh** terminal (or *"Developer PowerShell for VS"*) so the compiler
   is on `PATH`, then from the **repo root** create the venv with 3.14 and
   install:

   ```powershell
   py -3.14 -m venv winvenv
   .\winvenv\Scripts\Activate.ps1
   python -m pip install -r src\requirements-lock.txt
   ```

   `PySide6` (abi3 wheel) and `mido` install normally; `python-rtmidi` compiles
   against MSVC and succeeds.
3. Verify, then run:

   ```powershell
   python --version          # 3.14.x
   python -c "import rtmidi; print('rtmidi ok')"
   cd src
   python run.py
   ```

### Linux / macOS (development only)

The app targets Windows, but you can run the GUI from source for development.
From the repo root:

```bash
cd src
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # or just PySide6 for GUI-only smoke tests
python run.py
```

On Debian/Ubuntu, install the system libraries PySide6 and `python-rtmidi` need
first:

```bash
sudo apt-get install -y libasound2-dev pkg-config \
    libglib2.0-0 libgl1 libegl1 libxkbcommon0 libdbus-1-3 \
    libfontconfig1 libfreetype6 libx11-6 libx11-xcb1 libxcb1 \
    libxext6 libxrender1 libxrandr2 libpulse0
```

> `libasound2-dev` + `pkg-config` are only needed when pip has to **compile**
> `python-rtmidi` (Python 3.13+, which has no wheel). `libxrandr2` is what Qt
> Multimedia's FFmpeg backend links against — without it Qt reports *"No
> QtMultimedia backends found"* and video playback silently fails.

A repo dev container is provided in [`.devcontainer/`](.devcontainer): it is
headless (`QT_QPA_PLATFORM=offscreen`), so the GUI is not visible, but the app
runs and **video clips really decode and play**, which makes the idle / trigger /
return-to-idle logic testable. **MIDI input cannot be tested there** — a container has
no ALSA sequencer, so no ports are listed; use the **Ctrl+T** hotkey to test-trigger a
mapping instead. Real MIDI input and the `.exe` build are Windows-only.

## Build the executable (on Windows)

Use the `winvenv` from *Run from source*, then build from the `src` folder:

```bat
winvenv\Scripts\activate
pip install -r src\requirements-lock.txt -r src\requirements-build.txt
cd src
pyinstaller app.spec
```

The standalone app is produced at `src\dist\VideoCues.exe` — a **one-file**
build, so that single `.exe` is the whole distributable. The `app.spec` bundles
Qt's multimedia / FFmpeg backend so video playback works on machines without Qt
installed, and the `assets` folder (default idle placeholder + icon). UPX is
disabled on purpose: it corrupts the Qt/FFmpeg DLLs inside a one-file build.

## Releasing

Maintainers only. A release is built by GitHub Actions
([`release.yml`](.github/workflows/release.yml)) when a `vX.Y.Z` tag on `main`
is pushed:

1. On `dev`, bump `__version__` in [`src/app/__init__.py`](src/app/__init__.py)
   and commit.
2. `/branch-flow promote`, then `/branch-flow ship`.
3. Tag `main` and push it:

   ```bash
   git tag v1.2.0 main
   git push origin main v1.2.0
   ```

The workflow refuses a tag that isn't on `main` or doesn't match
`__version__`. It builds on Windows with Python 3.14 from the pinned
requirements, then publishes the release with `VideoCues-X.Y.Z-win64.exe`,
`SHA256SUMS.txt` and auto-generated notes (edit them on GitHub afterwards if
needed). Running apps learn about it from `/releases/latest`, so a release
marked as a pre-release is never offered to them.

## Configuration file

`%APPDATA%\LiveCues\VideoCues\config.json`:

> Upgrading from 1.0.x, which stored it in `%APPDATA%\Video Cues\`: on first
> run the app copies that `config.json` across once. The old folder is left in
> place as a backup and can be deleted afterwards.

```json
{
  "video_root": "C:/Videos",
  "idle_video": "idle/standby.mp4",
  "midi_device": "rtpMIDI Session 1",
  "midi_channel": 0,
  "output_screen": 1,
  "audio_muted": true,
  "window_x": 1920,
  "window_y": 0,
  "window_width": 1280,
  "window_height": 720,
  "output_fullscreen": false,
  "video_zoom": 1.0,
  "video_offset_x": 0.0,
  "video_offset_y": 0.0,
  "video_crop_left": 0.0,
  "video_crop_right": 0.0,
  "video_crop_top": 0.0,
  "video_crop_bottom": 0.0,
  "move_step": 0.02,
  "zoom_step": 0.10,
  "mappings": { "60": "clips/intro.mp4", "62": "clips/verse.mp4" }
}
```

- `midi_channel`: `0` = all channels, `1`–`16` = a specific channel.
- `mappings`: MIDI note number → video path **relative to `video_root`**
  (absolute paths are also accepted).
- `output_screen`: index of the display used for the output window. Updated
  automatically when you drag the window onto another display, and settable from
  the Edit tab.
- `window_x` / `window_y` / `window_width` / `window_height`: the output
  window's **windowed** rectangle, saved shortly after you stop moving or
  resizing it, and kept unchanged while fullscreen so leaving fullscreen returns
  to your aligned window. Width/height `0` means "never saved" — the window then
  opens centered at 60% of the display. If the saved rectangle no longer lands on
  a connected display (projector unplugged, resolution change), it is discarded
  and the window opens centered instead.
- `output_fullscreen`: whether the output was fullscreen when last used; it
  reopens that way on the saved display.
- `video_zoom` / `video_offset_x` / `video_offset_y` / `video_crop_*`: output
  video placement set via the **Output position, zoom & crop** controls. The
  video fills the output by default (`1.0` zoom, all crops `0.0`); `video_zoom`
  zooms in further, offsets pan as a fraction of the window size, and each
  `video_crop_*` cuts that fraction off the matching edge. Adjusted live and
  saved automatically.
- `move_step`: how far each **Move** click nudges the video, as a fraction of the
  window size (default `0.02` = 2%). Set it live with the **Step** control next to
  the move arrows.
- `zoom_step`: how much each **Zoom** click scales the video, as a fraction
  (default `0.10` = ±10% per click). Set it live with the **Step** control under
  the zoom buttons.

## Project layout

```
.                    repo root
├── README.md        this file
├── LICENSE          MIT
├── .gitignore
├── .devcontainer/   VS Code dev container (Linux dev box)
├── .github/         contributing, security policy, issue/PR templates,
│                    Dependabot config, CI (CodeQL + pip-audit + release)
├── winvenv/         Windows venv — run + build here (gitignored)
└── src/             the application
    ├── app/
    │   ├── main.py            entry / wiring + hotkeys
    │   ├── config.py          load/save JSON config (dataclass)
    │   ├── paths.py           %APPDATA% + bundled-asset resolution
    │   ├── midi_engine.py     MIDI input -> Qt signals
    │   ├── video_window.py    output window (fill, zoom/pan/crop, idle/trigger,
    │   │                      remembered size/position/display/fullscreen)
    │   ├── control_window.py  Run + Edit GUI
    │   ├── mapping_editor.py  note -> video table
    │   ├── updates.py         GitHub latest-release check (notify only)
    │   ├── update_dialog.py   the update dialog
    │   └── theme.py           LiveCues suite look: colours, fonts, drawn keys
    ├── assets/                app icon (app.svg/png/ico), IBM Plex fonts,
    │                          UI arrows, and a place to drop an idle video
    │                          (`*.mp4` here is gitignored)
    ├── .venv/                 Linux venv used by the dev container (gitignored)
    ├── run.py                 entry script (also used by PyInstaller)
    ├── app.spec               PyInstaller build spec (run on Windows)
    ├── requirements.txt       loose minimum versions
    ├── requirements-lock.txt  exact tested/built versions
    ├── requirements-build.txt PyInstaller toolchain (Windows build)
    └── CLAUDE.md              contributor / architecture notes
```
