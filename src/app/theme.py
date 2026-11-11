"""LiveCues suite look ("The Silkscreen Desk"): tokens, fonts and drawn widgets.

Colours and rules come from the suite design system shared with
livecues-reaper-remote (see DESIGN.md). Dark only. Flat: depth is tone plus
1px lines, never shadows. Square corners, except keys, which have one
chamfered corner (top right). One signal orange for selection, focus and the
single lit key; green / red / amber only report state, always beside a shape
or a word.

Qt style sheets cannot do letter-spacing or clip-paths, so fonts are set as
QFont objects (never in the sheet) and keys, tabs, ticks and state LEDs are
painted here.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QLabel,
    QSizePolicy,
    QStyleFactory,
    QWidget,
)

from .paths import asset

# ----- tokens (mirror shared/css/tokens.css in livecues-reaper-remote) -------
CHASSIS = "#191a17"      # page background
BAR = "#141512"          # top bar, table headers
DISPLAY = "#0c0d0b"      # recessed slots: readouts, fields, log, table
KEY = "#282a25"          # key face
KEY_HOVER = "#343630"
EDGE = "#3a3c34"         # border of slots and fields
LINE = "#2d2e29"         # dividers
ACTIVE_WASH = "#22241f"
LEGEND = "#dcdbcd"       # all primary text
LEGEND_DIM = "#8d8c80"   # secondary text
SIGNAL = "#ff6a1a"       # selection, focus, the one lit key
SIGNAL_INK = "#1c0b00"   # text on a signal fill
LED_GREEN = "#79e08a"
LED_RED = "#ff4a3a"
WARN_AMBER = "#e0a030"

KEY_H = 36               # key / field height (the suite's mouse-only size)
CHAMFER = 8              # cut corner of a key, px

SANS = "IBM Plex Sans"
MONO = "IBM Plex Mono"

_FONT_FILES = (
    "IBMPlexSans-Medium.ttf",
    "IBMPlexSans-SemiBold.ttf",
    "IBMPlexSans-Bold.ttf",
    "IBMPlexMono-Regular.ttf",
    "IBMPlexMono-Medium.ttf",
)


# ----- fonts -----------------------------------------------------------------
def load_fonts() -> None:
    """Register the bundled Plex faces (the stage machine may be offline)."""
    for name in _FONT_FILES:
        QFontDatabase.addApplicationFont(str(asset("fonts", name)))


def ui_font(px: int = 14, weight: QFont.Weight = QFont.Medium) -> QFont:
    f = QFont(SANS)
    f.setPixelSize(px)
    f.setWeight(weight)
    return f


def mono_font(px: int = 13, weight: QFont.Weight = QFont.Normal) -> QFont:
    f = QFont(MONO)
    f.setStyleHint(QFont.Monospace)
    f.setPixelSize(px)
    f.setWeight(weight)
    return f


def legend_font(px: int = 11, weight: QFont.Weight = QFont.DemiBold) -> QFont:
    """Silkscreen legend: small spaced capitals printed on the panel."""
    f = ui_font(px, weight)
    f.setLetterSpacing(QFont.AbsoluteSpacing, px * 0.12)
    f.setCapitalization(QFont.AllUppercase)
    return f


def key_font() -> QFont:
    f = ui_font(14, QFont.DemiBold)
    f.setLetterSpacing(QFont.AbsoluteSpacing, 14 * 0.04)
    return f


# ----- application-wide theme ------------------------------------------------
_SHEET = f"""
QMainWindow, QDialog, QMessageBox {{ background: {CHASSIS}; }}
QWidget {{ color: {LEGEND}; }}
QToolTip {{ background: {BAR}; color: {LEGEND}; border: 1px solid {EDGE}; padding: 4px 6px; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {DISPLAY}; color: {LEGEND}; border: 1px solid {EDGE}; border-radius: 0;
    padding: 0 8px; min-height: {KEY_H - 2}px;
    selection-background-color: {SIGNAL}; selection-color: {SIGNAL_INK};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border: 2px solid {SIGNAL}; padding: 0 7px; }}
QLineEdit:disabled, QComboBox:disabled {{ color: {LEGEND_DIM}; }}
QSpinBox, QDoubleSpinBox {{ padding-right: 22px; }}
QSpinBox:focus, QDoubleSpinBox:focus {{ padding-right: 21px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border; width: 20px; background: {KEY}; border: 0; border-left: 1px solid {EDGE};
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{ subcontrol-position: top right; border-bottom: 1px solid {EDGE}; }}
QSpinBox::down-button, QDoubleSpinBox::down-button {{ subcontrol-position: bottom right; }}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{ background: {KEY_HOVER}; }}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url({asset('ui', 'arrow-up.svg').as_posix()}); width: 8px; height: 8px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url({asset('ui', 'arrow-down.svg').as_posix()}); width: 8px; height: 8px; }}

QComboBox {{ padding-right: 30px; }}
QComboBox:focus {{ padding-right: 29px; }}
QComboBox::drop-down {{ subcontrol-origin: border; subcontrol-position: center right; width: 30px; border: 0; }}
QComboBox::down-arrow {{ image: url({asset('ui', 'arrow-down.svg').as_posix()}); width: 9px; height: 9px; }}
QComboBox QAbstractItemView {{
    background: {BAR}; color: {LEGEND}; border: 1px solid {EDGE}; outline: 0;
    selection-background-color: {ACTIVE_WASH}; selection-color: {LEGEND};
}}

QListWidget#log {{ background: {DISPLAY}; border: 1px solid {EDGE}; padding: 6px 4px; outline: 0; }}
QListWidget#log::item {{ padding: 1px 4px; border: 0; }}
QListWidget#log::item:selected {{ background: {ACTIVE_WASH}; color: {LEGEND}; }}

QTableWidget {{ background: {DISPLAY}; border: 1px solid {EDGE}; gridline-color: {LINE}; outline: 0; }}
QTableWidget::item {{ border: 0; }}
QHeaderView {{ background: {BAR}; border: 0; }}
QHeaderView::section {{
    background: {BAR}; color: {LEGEND_DIM}; border: 0; border-bottom: 1px solid {LINE};
    padding: 0 8px; height: 30px;
}}
QTableCornerButton::section {{ background: {BAR}; border: 0; }}

QScrollBar:vertical {{ background: {DISPLAY}; width: 10px; margin: 0; }}
QScrollBar:horizontal {{ background: {DISPLAY}; height: 10px; margin: 0; }}
QScrollBar::handle {{ background: {KEY_HOVER}; min-height: 24px; min-width: 24px; }}
QScrollBar::handle:hover {{ background: {EDGE}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QFrame#bar {{ background: {BAR}; border-bottom: 1px solid {LINE}; }}
QFrame#rule {{ background: {LINE}; border: 0; max-height: 1px; min-height: 1px; }}
QFrame#slot {{ background: {DISPLAY}; border: 1px solid {EDGE}; }}
QLabel#readout {{ background: {DISPLAY}; border: 1px solid {EDGE}; padding: 0 10px; }}
QLabel#dim {{ color: {LEGEND_DIM}; }}

/* Plain QPushButtons only remain in system dialogs; give them a flat key face. */
QPushButton {{ background: {KEY}; color: {LEGEND}; border: 0; border-radius: 0; padding: 0 16px; min-height: {KEY_H}px; }}
QPushButton:hover {{ background: {KEY_HOVER}; }}
QPushButton:pressed {{ background: {LEGEND}; color: {CHASSIS}; }}
QPushButton:focus {{ border: 2px solid {SIGNAL}; }}
"""


def apply_theme(app: QApplication) -> None:
    """Fonts, dark palette and the suite style sheet for the whole app."""
    load_fonts()
    app.setStyle(QStyleFactory.create("Fusion"))

    hints = app.styleHints()
    if hasattr(hints, "setColorScheme"):  # Qt 6.8+: dark window frame on Windows
        hints.setColorScheme(Qt.ColorScheme.Dark)

    pal = QPalette()
    for role, colour in (
        (QPalette.Window, CHASSIS),
        (QPalette.WindowText, LEGEND),
        (QPalette.Base, DISPLAY),
        (QPalette.AlternateBase, BAR),
        (QPalette.Text, LEGEND),
        (QPalette.PlaceholderText, LEGEND_DIM),
        (QPalette.Button, KEY),
        (QPalette.ButtonText, LEGEND),
        (QPalette.BrightText, LEGEND),
        (QPalette.Highlight, SIGNAL),
        (QPalette.HighlightedText, SIGNAL_INK),
        (QPalette.ToolTipBase, BAR),
        (QPalette.ToolTipText, LEGEND),
        (QPalette.Link, SIGNAL),
        (QPalette.Light, KEY_HOVER),
        (QPalette.Midlight, KEY),
        (QPalette.Mid, EDGE),
        (QPalette.Dark, BAR),
        (QPalette.Shadow, DISPLAY),
    ):
        pal.setColor(role, QColor(colour))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor(LEGEND_DIM))
    app.setPalette(pal)
    app.setFont(ui_font(14))
    app.setStyleSheet(_SHEET)


# ----- small builders --------------------------------------------------------
def legend(text: str, parent: Optional[QWidget] = None, colour: str = LEGEND_DIM) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setFont(legend_font())
    lbl.setStyleSheet(f"color: {colour};")
    return lbl


def rule(parent: Optional[QWidget] = None) -> QWidget:
    """A 1px Line divider."""
    w = QWidget(parent)
    w.setObjectName("rule")
    w.setFixedHeight(1)
    w.setAttribute(Qt.WA_StyledBackground, True)
    w.setStyleSheet(f"background: {LINE};")
    return w


def readout(text: str = "—", parent: Optional[QWidget] = None, px: int = 13) -> QLabel:
    """A recessed Display slot holding a monospace value."""
    lbl = QLabel(text, parent)
    lbl.setObjectName("readout")
    lbl.setFont(mono_font(px))
    lbl.setFixedHeight(KEY_H)
    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return lbl



# ----- drawn shapes ----------------------------------------------------------
def draw_shape(p: QPainter, shape: str, rect: QRectF, colour: QColor) -> None:
    """State shapes shared with the suite: disc, ring, square, triangle."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing, True)
    if shape == "ring":
        p.setPen(QPen(colour, 1.6))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(rect.adjusted(0.8, 0.8, -0.8, -0.8))
    elif shape == "disc":
        p.setPen(Qt.NoPen)
        p.setBrush(colour)
        p.drawEllipse(rect)
    elif shape == "square":
        p.setPen(Qt.NoPen)
        p.setBrush(colour)
        p.drawRect(rect.adjusted(0.5, 0.5, -0.5, -0.5))
    elif shape == "triangle":
        p.setPen(Qt.NoPen)
        p.setBrush(colour)
        p.drawPolygon(QPolygonF([rect.topLeft(), QPointF(rect.right(), rect.center().y()), rect.bottomLeft()]))
    p.restore()


def draw_glyph(p: QPainter, glyph: str, c: QPointF, size: float, colour: QColor) -> None:
    """Drawn key symbols (no font glyphs): arrows, plus, minus, cross, play."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing, True)
    h = size / 2
    if glyph in ("up", "down", "left", "right", "play"):
        p.setPen(Qt.NoPen)
        p.setBrush(colour)
        pts = {
            "up": [(0, -h * 0.8), (h, h * 0.6), (-h, h * 0.6)],
            "down": [(0, h * 0.8), (h, -h * 0.6), (-h, -h * 0.6)],
            "left": [(-h * 0.8, 0), (h * 0.6, -h), (h * 0.6, h)],
            "right": [(h * 0.8, 0), (-h * 0.6, -h), (-h * 0.6, h)],
            "play": [(h * 0.8, 0), (-h * 0.6, -h), (-h * 0.6, h)],
        }[glyph]
        p.drawPolygon(QPolygonF([QPointF(c.x() + x, c.y() + y) for x, y in pts]))
    else:
        pen = QPen(colour, 2.0)
        pen.setCapStyle(Qt.SquareCap)
        p.setPen(pen)
        if glyph in ("plus", "minus"):
            p.drawLine(QPointF(c.x() - h, c.y()), QPointF(c.x() + h, c.y()))
        if glyph == "plus":
            p.drawLine(QPointF(c.x(), c.y() - h), QPointF(c.x(), c.y() + h))
        if glyph == "cross":
            k = h * 0.75
            p.drawLine(QPointF(c.x() - k, c.y() - k), QPointF(c.x() + k, c.y() + k))
            p.drawLine(QPointF(c.x() - k, c.y() + k), QPointF(c.x() + k, c.y() - k))
    p.restore()


def _chamfer_path(r: QRectF, cut: float = CHAMFER) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(r.left(), r.top())
    path.lineTo(r.right() - cut, r.top())
    path.lineTo(r.right(), r.top() + cut)
    path.lineTo(r.right(), r.bottom())
    path.lineTo(r.left(), r.bottom())
    path.closeSubpath()
    return path


# ----- widgets ---------------------------------------------------------------
_KEYBOARD_REASONS = (Qt.TabFocusReason, Qt.BacktabFocusReason, Qt.ShortcutFocusReason)


class _KeyboardFocus:
    """Mixin: remember whether focus arrived from the keyboard.

    The Signal focus ring is drawn only then, like CSS ``:focus-visible``,
    so a mouse click or the window's initial focus never lights a ring.
    """

    _kbd_focus = False

    def focusInEvent(self, event) -> None:  # noqa: N802
        self._kbd_focus = event.reason() in _KEYBOARD_REASONS
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: N802
        self._kbd_focus = False
        super().focusOutEvent(event)

    def _show_focus(self) -> bool:
        return self.hasFocus() and self._kbd_focus


class Key(_KeyboardFocus, QAbstractButton):
    """A flat key with one chamfered corner.

    ``variant``: ``"normal"`` (Key face), ``"lit"`` (Signal face, the one
    forward action in a view) or ``"quiet"`` (no face, a 1px Edge line).
    :meth:`set_sunk` draws the "something is on" state in LED red: Chassis
    face, a 2px red inset outline and red text. ``hint`` is a small Legend
    Dim legend at the right (a hotkey). ``glyph`` draws a symbol instead of,
    or before, the text.
    """

    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
        *,
        variant: str = "normal",
        glyph: str = "",
        hint: str = "",
        width: Optional[int] = None,
    ) -> None:
        super().__init__(parent)
        self.setText(text)
        self._variant = variant
        self._glyph = glyph
        self._hint = hint
        self._sunk = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_Hover, True)
        self.setFont(key_font())
        if variant == "lit":
            f = self.font()
            f.setWeight(QFont.Bold)
            self.setFont(f)
        if width is not None:
            self.setFixedSize(width, KEY_H)
        else:
            self.setFixedHeight(KEY_H)
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def set_sunk(self, sunk: bool) -> None:
        if sunk != self._sunk:
            self._sunk = sunk
            self.update()

    def is_sunk(self) -> bool:
        return self._sunk

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt naming)
        fm = QFontMetrics(self.font())
        w = 32
        if self.text():
            w += fm.horizontalAdvance(self.text())
        if self._glyph and self.text():
            w += 18
        elif self._glyph:
            w = KEY_H
        if self._hint:
            w += 14 + QFontMetrics(legend_font(10)).horizontalAdvance(self._hint.upper()) + 2
        return QSize(max(w, KEY_H), KEY_H)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return self.sizeHint()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect())
        path = _chamfer_path(r)
        enabled = self.isEnabled()
        down = self.isDown() and enabled
        hover = self.underMouse() and enabled
        if not enabled:
            p.setOpacity(0.4)

        text = QColor(LEGEND)
        hint = QColor(LEGEND_DIM)
        if down:
            p.fillPath(path, QColor(LEGEND))
            text = hint = QColor(CHASSIS)
        elif self._sunk:
            p.fillPath(path, QColor(CHASSIS))
            p.save()
            p.setClipPath(path)
            pen = QPen(QColor(LED_RED), 4)  # 2px visible inside the clip
            pen.setJoinStyle(Qt.MiterJoin)
            p.setPen(pen)
            p.drawPath(path)
            p.restore()
            text = QColor(LED_RED)
            hint = QColor(LED_RED)
            hint.setAlphaF(0.75)
        elif self._variant == "lit":
            face = QColor(SIGNAL)
            if hover:
                face = _mix(SIGNAL, LEGEND, 0.12)
            p.fillPath(path, face)
            text = QColor(SIGNAL_INK)
            hint = QColor(SIGNAL_INK)
            hint.setAlphaF(0.7)
        elif self._variant == "quiet":
            if hover:
                p.fillPath(path, QColor(KEY))
            p.save()
            p.setClipPath(path)
            p.setPen(QPen(QColor(EDGE), 2))
            p.drawPath(path)
            p.restore()
        else:
            p.fillPath(path, QColor(KEY_HOVER if hover else KEY))

        # Content: [glyph][text] ........ [hint]
        content = r.adjusted(16, 0, -16, 0)
        if self._hint:
            hf = legend_font(10)
            p.setFont(hf)
            p.setPen(hint)
            hw = QFontMetrics(hf).horizontalAdvance(self._hint.upper()) + 2
            p.drawText(QRectF(content.right() - hw, r.top(), hw, r.height()), Qt.AlignVCenter | Qt.AlignRight, self._hint)
            content.setRight(content.right() - hw - 14)

        if self._glyph and not self.text():
            draw_glyph(p, self._glyph, r.center(), 10, text)
        else:
            p.setFont(self.font())
            p.setPen(text)
            align = Qt.AlignVCenter | (Qt.AlignLeft if self._hint else Qt.AlignHCenter)
            if self._glyph:
                tw = QFontMetrics(self.font()).horizontalAdvance(self.text())
                total = 18 + tw
                x0 = content.left() if self._hint else r.center().x() - total / 2
                draw_glyph(p, self._glyph, QPointF(x0 + 5, r.center().y()), 9, text)
                p.drawText(QRectF(x0 + 18, r.top(), tw + 2, r.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())
            else:
                p.drawText(content, align, self.text())

        if self._show_focus():
            p.setOpacity(1.0)
            p.setClipPath(path)
            p.setPen(QPen(QColor(SIGNAL_INK if self._variant == "lit" else SIGNAL), 2))
            p.setBrush(Qt.NoBrush)
            p.drawPath(_chamfer_path(r.adjusted(4, 4, -4, -4), CHAMFER - 2))
        p.end()


class Tab(_KeyboardFocus, QAbstractButton):
    """Equal-width tab: Legend Dim caps; selected is Legend with a 3px Signal underline.

    Not checkable on purpose: the owner decides whether a click may switch
    (Edit asks about unsaved changes first), then calls :meth:`set_selected`.
    """

    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setText(text)
        self._selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_Hover, True)
        self.setFont(legend_font(12))
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def is_selected(self) -> bool:
        return self._selected

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(QFontMetrics(self.font()).horizontalAdvance(self.text()) + 48, 40)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        r = self.rect()
        on = self._selected
        colour = QColor(LEGEND if on or self.underMouse() else LEGEND_DIM)
        p.setFont(self.font())
        p.setPen(colour)
        p.drawText(r.adjusted(0, 0, 0, -3), Qt.AlignCenter, self.text())
        if on:
            p.fillRect(0, r.height() - 3, r.width(), 3, QColor(SIGNAL))
        if self._show_focus():
            p.setPen(QPen(QColor(SIGNAL), 2))
            p.drawRect(QRectF(r).adjusted(3, 3, -3, -6))
        p.end()


class StateChip(QWidget):
    """A drawn state shape followed by an uppercase state word."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._shape = "ring"
        self._colour = QColor(LEGEND_DIM)
        self._word = ""
        self._word_colour = QColor(LEGEND_DIM)
        self._ref_font: Optional[QFont] = None
        self.setFont(legend_font(11))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def align_baseline_to(self, font: QFont) -> None:
        """Sit the word on the same baseline as text set in ``font`` beside this chip.

        The chip takes that font's line height, so a label centred next to it
        shares its baseline exactly.
        """
        self._ref_font = font
        self.updateGeometry()
        self.update()

    def set_state(self, shape: str, colour: str, word: str, word_colour: Optional[str] = None) -> None:
        self._shape = shape
        self._colour = QColor(colour)
        self._word = word
        self._word_colour = QColor(word_colour or LEGEND_DIM)
        self.setAccessibleName(word)
        self.updateGeometry()
        self.update()

    def word(self) -> str:
        return self._word

    def sizeHint(self) -> QSize:  # noqa: N802
        h = QFontMetrics(self._ref_font).height() if self._ref_font else 24
        return QSize(11 + 7 + QFontMetrics(self.font()).horizontalAdvance(self._word.upper()) + 4, h)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setFont(self.font())
        p.setPen(self._word_colour)
        if self._ref_font is None:
            cy = self.height() / 2
            draw_shape(p, self._shape, QRectF(0, cy - 5.5, 11, 11), self._colour)
            p.drawText(QRectF(18, 0, self.width() - 18, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self._word)
        else:
            # Baseline of the neighbouring text as a centred label would set it.
            ref = QFontMetrics(self._ref_font)
            baseline = (self.height() - ref.height()) / 2 + ref.ascent()
            cap = QFontMetrics(self.font()).capHeight()
            draw_shape(p, self._shape, QRectF(0, baseline - cap / 2 - 5.5, 11, 11), self._colour)
            p.drawText(QPointF(18, baseline), self._word)
        p.end()


class Tick(_KeyboardFocus, QCheckBox):
    """Checkbox in the suite's tick style: a Signal box with a drawn check when on."""

    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(KEY_H)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(18 + 10 + QFontMetrics(self.font()).horizontalAdvance(self.text()) + 4, KEY_H)

    def hitButton(self, pos) -> bool:  # noqa: N802 (the whole row toggles)
        return self.rect().contains(pos)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        box = QRectF(1, (self.height() - 18) / 2, 18, 18)
        if self.isChecked():
            p.fillRect(box, QColor(SIGNAL))
            pen = QPen(QColor(SIGNAL_INK), 2.2)
            pen.setCapStyle(Qt.SquareCap)
            p.setPen(pen)
            p.drawPolyline(QPolygonF([
                QPointF(box.left() + 4.5, box.center().y()),
                QPointF(box.left() + 7.8, box.bottom() - 5),
                QPointF(box.right() - 4, box.top() + 5),
            ]))
        else:
            p.fillRect(box, QColor(DISPLAY))
            p.setPen(QPen(QColor(LEGEND_DIM), 1))
            p.drawRect(box.adjusted(0.5, 0.5, -0.5, -0.5))
        if self._show_focus():
            p.setPen(QPen(QColor(SIGNAL), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRect(box.adjusted(-3, -3, 3, 3))
        p.setPen(QColor(LEGEND if self.isChecked() else LEGEND_DIM))
        p.setFont(self.font())
        p.drawText(QRectF(28, 0, self.width() - 28, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())
        p.end()


def _mix(a: str, b: str, t: float) -> QColor:
    ca, cb = QColor(a), QColor(b)
    return QColor(
        round(ca.red() + (cb.red() - ca.red()) * t),
        round(ca.green() + (cb.green() - ca.green()) * t),
        round(ca.blue() + (cb.blue() - ca.blue()) * t),
    )

