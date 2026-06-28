"""Convenience entry point (also used as the PyInstaller entry script).

Run from source with:  python run.py   (or:  python -m app.main)
"""
from app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
