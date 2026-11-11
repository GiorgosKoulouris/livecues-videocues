FROM tcop-claude:latest

USER root

# Build deps: python-rtmidi has no wheel for Python 3.14, so pip compiles it
# against ALSA (libasound2-dev + pkg-config).
# Runtime deps: the libraries PySide6 actually loads in this container —
# Qt Gui/Widgets (glib, GL/EGL, xkbcommon, dbus, fontconfig, freetype, X11/xcb
# client libs) and Qt Multimedia's FFmpeg backend (libxrandr2, libpulse0).
# libxrandr2 is not optional: without it libffmpegmediaplugin.so fails to load
# and QtMultimedia reports "No QtMultimedia backends found", which kills
# QMediaPlayer/QVideoSink entirely.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        python3 \
        python3-venv \
        libasound2-dev \
        pkg-config \
        libglib2.0-0 \
        libgl1 \
        libegl1 \
        libxkbcommon0 \
        libdbus-1-3 \
        libfontconfig1 \
        libfreetype6 \
        libx11-6 \
        libx11-xcb1 \
        libxcb1 \
        libxext6 \
        libxrender1 \
        libxrandr2 \
        libpulse0 && \
    rm -rf /var/lib/apt/lists/*

# Headless: no X server here, so Qt renders offscreen.
ENV QT_QPA_PLATFORM=offscreen
# QtMultimedia's FFmpeg backend dlopens optional PipeWire / VA-API libraries that
# a headless container has no use for; silence the "Couldn't load ..." chatter but
# keep every other multimedia warning visible.
ENV QT_LOGGING_RULES="qt.multimedia.symbolsresolver.warning=false"

USER vscode
