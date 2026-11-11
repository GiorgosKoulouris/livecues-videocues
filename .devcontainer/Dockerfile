# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/devcontainers/base:ubuntu

USER root

# Build deps: python-rtmidi has no wheel for Python 3.14, so pip compiles it
# against ALSA (libasound2-dev + pkg-config) and the Python headers (python3-dev).
# Runtime deps: the libraries PySide6 actually loads in this container —
# Qt Gui/Widgets (glib, GL/EGL, xkbcommon, dbus, fontconfig, freetype, X11/xcb
# client libs) and Qt Multimedia's FFmpeg backend (libxrandr2, libpulse0).
# libxrandr2 is not optional: without it libffmpegmediaplugin.so fails to load
# and QtMultimedia reports "No QtMultimedia backends found", which kills
# QMediaPlayer/QVideoSink entirely.
# The apt cache mounts keep downloaded .debs across builds, so editing this
# package list doesn't re-download everything. Ubuntu images auto-clean the
# cache, which is why docker-clean is removed first.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        python3 \
        python3-venv \
        python3-dev \
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
        libpulse0

# Headless: no X server here, so Qt renders offscreen.
ENV QT_QPA_PLATFORM=offscreen
# QtMultimedia's FFmpeg backend dlopens optional PipeWire / VA-API libraries that
# a headless container has no use for; silence the "Couldn't load ..." chatter but
# keep every other multimedia warning visible.
ENV QT_LOGGING_RULES="qt.multimedia.symbolsresolver.warning=false"

# Mount point for the venv volume (see docker-compose.yml): the new volume is
# seeded from this directory, so it starts out owned by vscode, not root.
RUN mkdir -p /workspace/src/.venv && chown vscode:vscode /workspace/src/.venv

USER vscode
RUN curl -fsSL https://claude.ai/install.sh | bash
