# Contributing to LiveCues VideoCues

Thanks for taking the time to help. Bug reports, feature ideas, and pull
requests are all welcome.

## Before you start

- **Bugs and ideas:** open an issue using one of the templates. Search the
  existing issues first.
- **Security problems:** do **not** open a public issue. See
  [SECURITY.md](SECURITY.md).
- **Bigger changes:** open an issue to discuss the idea before writing code, so
  nobody spends time on something that will not be merged.

## Development setup

Follow [*Run from source*](../README.md#run-from-source) in the README. In short:

- **Windows** is the target platform: real MIDI input, video output, and the
  `.exe` build all happen there (`winvenv/` at the repo root).
- **Linux / macOS** (or the VS Code dev container) works for UI and logic work,
  but has no MIDI input; use **Ctrl+T** to test-trigger a mapping.

Install the pinned, tested dependency set:

```bat
pip install -r src\requirements-lock.txt
```

`src/requirements.txt` holds the loose minimum versions; `src/requirements-lock.txt`
holds the exact versions the app is tested and built with;
`src/requirements-build.txt` adds PyInstaller for building the `.exe`.

## Branches and pull requests

Work flows **`dev` → `stage` → `main`**:

- `dev` is where all changes land. **Open pull requests against `dev`.**
- `stage` is promoted from `dev` for pre-release testing.
- `main` is what releases are built from. It only receives promotions from `stage`.

In your pull request:

1. Keep it focused on one change, and describe what it does and why.
2. Say how you tested it. For anything touching MIDI, video output, or the
   build, test on Windows.
3. Update the README when you change behaviour, hotkeys, configuration, or setup
   steps.
4. Make sure the CI checks pass.

## Code style

- Match the style of the surrounding code; keep changes readable over clever.
- Architecture and module notes for contributors live in
  [`src/CLAUDE.md`](../src/CLAUDE.md); the visual design rules live in
  [`DESIGN.md`](../DESIGN.md).

## Dependencies

If you add or bump a dependency by hand, update both `src/requirements.txt`
(minimum version) and `src/requirements-lock.txt` (exact version).

Dependabot opens two kinds of pull requests:

- **Version updates**, weekly, against `dev`. Merge or close them before the
  next promote to `stage`: promoting rewrites `dev`, which leaves any open pull
  request on old history.
- **Security updates**, against `main`, because GitHub always opens them there.
  Leave them unmerged: `main` only moves by fast-forward to `stage`, and a merge
  on `main` would break that. Apply the same bump on `dev`, then close the pull
  request. The alert closes when the fix ships to `main`.

The `pip-audit` workflow checks the pinned versions on every push that changes
them, and audits `dev`, `stage` and `main` every week.

## Code of conduct

By taking part you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
