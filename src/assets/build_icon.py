"""Render ``app.svg`` into ``app.png`` (256px) and a multi-size Windows ``app.ico``.

Run after editing ``app.svg`` to regenerate the bundled icons:

    python assets/build_icon.py            # uses the files next to this script

No Pillow dependency: PNGs are rendered with Qt (PySide6 + QtSvg), then packed
into a Vista-style ICO container (each entry is a PNG-encoded image, which the
ICO format allows). Needs only PySide6, which the app already depends on.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QImage, QPainter, QGuiApplication
from PySide6.QtSvg import QSvgRenderer

HERE = Path(__file__).resolve().parent
SRC = HERE / "app.svg"
OUT_PNG = HERE / "app.png"
OUT_ICO = HERE / "app.ico"
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def _render(svg: QByteArray, size: int) -> QImage:
    renderer = QSvgRenderer(svg)
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(p)
    p.end()
    return img


def _png_bytes(img: QImage) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def _write_ico(images: list[tuple[int, bytes]], path: Path) -> None:
    header = struct.pack("<HHH", 0, 1, len(images))  # reserved, type=icon, count
    offset = 6 + 16 * len(images)
    entries = b""
    data = b""
    for size, png in images:
        dim = 0 if size >= 256 else size  # 0 means 256 in the ICO spec
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        data += png
        offset += len(png)
    path.write_bytes(header + entries + data)


def main() -> int:
    QGuiApplication(sys.argv)
    svg = QByteArray(SRC.read_bytes())
    _render(svg, 256).save(str(OUT_PNG), "PNG")
    _write_ico([(s, _png_bytes(_render(svg, s))) for s in ICO_SIZES], OUT_ICO)
    print(f"wrote {OUT_PNG.name} and {OUT_ICO.name} (sizes: {ICO_SIZES})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
