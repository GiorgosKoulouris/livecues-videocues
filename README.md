<img src="src/assets/app.png" alt="Video Cues" width="96" align="left" />

# Video Cues

A Windows desktop app that listens to MIDI (including **RTP-MIDI** over the
network) and plays a video clip on a projector / second display whenever a
configured MIDI note arrives.

<br clear="left" />

- **Status view** — live MIDI connection, channel, output display, now-playing,
  and a scrolling MIDI activity log.
- **Edit view** — configure the note → video mappings, video root folder, idle
  (loop) video, MIDI device, MIDI channel, output display, and audio mute. Each
  mapping accepts the note as either a **MIDI number** (0–127) or a **note name**
  (e.g. `C3`, `F#2`, `Bb4`) — the two fields stay in sync.
- **Output window** — opens as a resizable, movable window on the display of your
  choice (projector / second monitor); press **F** (or use the Fullscreen button)
  to toggle fullscreen. The video **fills** the output by default (no black bars).
  Use the **Output position, zoom & crop** controls in the Status view to move,
  zoom, and crop each edge of the video on the display (handy for projector
  alignment); the placement is saved. Plays a looping idle video when nothing is
  triggered; a note interrupts with its clip, plays once, then returns to idle.
- Configuration is stored in `%APPDATA%\Video Cues\config.json` and
  **survives app and system restarts**.

## How triggering behaves

| Situation | Behaviour |
|-----------|-----------|
| Mapped Note-On received | Plays the clip once, then returns to the idle loop |
| New note while a clip is playing | Interrupts immediately and plays the new clip |
| Nothing playing | Loops the configured idle video (or black if none set) |
| Audio | Muted by default; toggle in Edit view |
| Note-Off | Ignored (only Note-On triggers) |

## Hotkeys

| Key | Action |
|-----|--------|
| **B** | Blackout toggle |
| **F** | Toggle fullscreen of the output window |
| **T** | Test-trigger the first mapping (no MIDI needed) |
| **Esc** | Exit fullscreen |

## RTP-MIDI setup (Windows)

The app reads ordinary Windows MIDI input ports. To receive **network MIDI**,
install the free **rtpMIDI** driver by Tobias Erichsen
(<https://www.tobias-erichsen.de/software/rtpmidi.html>):

1. Install rtpMIDI and open it.
2. Create a session (e.g. *"Session 1"`) and enable it.
3. Connect your remote MIDI source to that session (directory / "Connect").
4. In **Video Cues → Edit → MIDI device**, select the matching port
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
   git clone https://github.com/GiorgosKoulouris/VideoCues.git
   cd VideoCues
   py -3.12 -m venv winvenv
   winvenv\Scripts\activate
   pip install -r src\requirements.txt
   cd src
   python run.py
   ```

   In **PowerShell**, activate with `.\winvenv\Scripts\Activate.ps1` instead. If
   activation is blocked, run
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and retry.
3. The app launches with the control window. Use **Edit Configuration** to set
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
   python -m pip install -r src\requirements.txt
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
blackout logic testable. **MIDI input cannot be tested there** — a container has
no ALSA sequencer, so no ports are listed; use the **T** hotkey to test-trigger a
mapping instead. Real MIDI input and the `.exe` build are Windows-only.

## Build the executable (on Windows)

Use the `winvenv` from *Run from source*, then build from the `src` folder:

```bat
winvenv\Scripts\activate
pip install -r src\requirements.txt pyinstaller
cd src
pyinstaller app.spec
```

The standalone app is produced at `src\dist\VideoCues.exe` — a **one-file**
build, so that single `.exe` is the whole distributable. The `app.spec` bundles
Qt's multimedia / FFmpeg backend so video playback works on machines without Qt
installed, and the `assets` folder (default idle placeholder + icon). UPX is
disabled on purpose: it corrupts the Qt/FFmpeg DLLs inside a one-file build.

## Configuration file

`%APPDATA%\Video Cues\config.json`:

```json
{
  "video_root": "C:/Videos",
  "idle_video": "idle/standby.mp4",
  "midi_device": "rtpMIDI Session 1",
  "midi_channel": 0,
  "output_screen": 1,
  "audio_muted": true,
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
- `output_screen`: index of the display to use for the output window.
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
├── winvenv/         Windows venv — run + build here (gitignored)
└── src/             the application
    ├── app/
    │   ├── main.py            entry / wiring + hotkeys
    │   ├── config.py          load/save JSON config (dataclass)
    │   ├── paths.py           %APPDATA% + bundled-asset resolution
    │   ├── midi_engine.py     MIDI input -> Qt signals
    │   ├── video_window.py    output window (fill, zoom/pan/crop, idle/trigger/blackout)
    │   ├── control_window.py  Status + Edit GUI
    │   └── mapping_editor.py  note -> video table
    ├── assets/                app icon (app.svg/png/ico) + a place to drop an
    │                          idle video (`*.mp4` here is gitignored)
    ├── .venv/                 Linux venv used by the dev container (gitignored)
    ├── run.py                 entry script (also used by PyInstaller)
    ├── app.spec               PyInstaller build spec (run on Windows)
    ├── requirements.txt
    └── CLAUDE.md              contributor / architecture notes
```
