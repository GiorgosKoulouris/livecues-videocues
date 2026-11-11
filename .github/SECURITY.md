# Security Policy

## Supported versions

Only the **latest release** receives security fixes. Please update to the
latest version before reporting.

## Reporting a vulnerability

**Do not report security problems in public issues, discussions, or pull
requests.**

Report them privately through GitHub instead:

1. Go to the repository's **Security** tab.
2. Click **Report a vulnerability**
   ([direct link](https://github.com/GiorgosKoulouris/livecues-videocues/security/advisories/new)).
3. Describe the problem, the affected version, and the steps to reproduce it.

You can expect an acknowledgement within **7 days**. Once the issue is
confirmed, a fix is prepared on a private branch and released, and the report is
published as a security advisory with credit to you, unless you prefer to stay
anonymous.

## Scope

LiveCues VideoCues is a local Windows desktop app. Things that are in scope
include:

- Opening a crafted configuration file (`config.json`) or video file causing
  code execution or writing outside the app's folders.
- Network MIDI (RTP-MIDI) input causing a crash or code execution.
- Problems with the published `.exe` or its bundled dependencies.

Vulnerabilities in third-party dependencies (Qt / PySide6, FFmpeg, mido,
python-rtmidi) should also be reported upstream; reporting them here is still
welcome so the bundled version can be updated.
