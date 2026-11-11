---
name: LiveCues VideoCues
description: A flat dark hardware panel (silkscreen legends, recessed display slots, one signal orange) for firing video cues from MIDI.
colors:
  chassis: "#191a17"
  bar: "#141512"
  display: "#0c0d0b"
  key: "#282a25"
  key-hover: "#343630"
  edge: "#3a3c34"
  line: "#2d2e29"
  active-wash: "#22241f"
  legend: "#dcdbcd"
  legend-dim: "#8d8c80"
  signal: "#ff6a1a"
  signal-ink: "#1c0b00"
  led-green: "#79e08a"
  led-red: "#ff4a3a"
  warn-amber: "#e0a030"
typography:
  title:
    fontFamily: "IBM Plex Sans"
    fontSize: "18px"
    fontWeight: 600
  body:
    fontFamily: "IBM Plex Sans"
    fontSize: "14px"
    fontWeight: 500
  key-label:
    fontFamily: "IBM Plex Sans"
    fontSize: "14px"
    fontWeight: 600
    letterSpacing: "0.04em"
  tab:
    fontFamily: "IBM Plex Sans"
    fontSize: "12px"
    fontWeight: 600
    letterSpacing: "0.12em"
  legend:
    fontFamily: "IBM Plex Sans"
    fontSize: "11px"
    fontWeight: 600
    letterSpacing: "0.12em"
  hint:
    fontFamily: "IBM Plex Sans"
    fontSize: "10px"
    fontWeight: 600
    letterSpacing: "0.12em"
  now-playing:
    fontFamily: "IBM Plex Mono"
    fontSize: "14px"
    fontWeight: 500
  readout:
    fontFamily: "IBM Plex Mono"
    fontSize: "13px"
    fontWeight: 400
  log:
    fontFamily: "IBM Plex Mono"
    fontSize: "12px"
    fontWeight: 400
rounded:
  none: "0px"
spacing:
  key-gap: "6px"
  row-gap: "8px"
  bar-gap: "12px"
  page: "16px"
  section: "18px"
  cluster-gap: "24px"
components:
  bar:
    backgroundColor: "{colors.bar}"
    textColor: "{colors.legend}"
    typography: "{typography.title}"
    padding: "0 16px"
    height: "52px"
  tab:
    backgroundColor: "{colors.chassis}"
    textColor: "{colors.legend-dim}"
    typography: "{typography.tab}"
    height: "40px"
  tab-selected:
    backgroundColor: "{colors.chassis}"
    textColor: "{colors.legend}"
    typography: "{typography.tab}"
    height: "40px"
  key:
    backgroundColor: "{colors.key}"
    textColor: "{colors.legend}"
    typography: "{typography.key-label}"
    rounded: "{rounded.none}"
    padding: "0 16px"
    height: "36px"
  key-hover:
    backgroundColor: "{colors.key-hover}"
    textColor: "{colors.legend}"
  key-pressed:
    backgroundColor: "{colors.legend}"
    textColor: "{colors.chassis}"
  key-lit:
    backgroundColor: "{colors.signal}"
    textColor: "{colors.signal-ink}"
    typography: "{typography.key-label}"
    padding: "0 16px"
    height: "36px"
  key-sunk:
    backgroundColor: "{colors.chassis}"
    textColor: "{colors.led-red}"
    height: "36px"
  key-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.legend}"
    height: "36px"
  key-square:
    backgroundColor: "{colors.key}"
    textColor: "{colors.legend}"
    width: "40px"
    height: "36px"
  readout:
    backgroundColor: "{colors.display}"
    textColor: "{colors.legend}"
    typography: "{typography.readout}"
    rounded: "{rounded.none}"
    padding: "0 10px"
    height: "36px"
  field:
    backgroundColor: "{colors.display}"
    textColor: "{colors.legend}"
    rounded: "{rounded.none}"
    padding: "0 8px"
    height: "36px"
  table-header:
    backgroundColor: "{colors.bar}"
    textColor: "{colors.legend-dim}"
    typography: "{typography.legend}"
    padding: "0 8px"
    height: "30px"
  table-row:
    backgroundColor: "{colors.display}"
    textColor: "{colors.legend}"
    padding: "5px"
    height: "46px"
  tick-on:
    backgroundColor: "{colors.signal}"
    textColor: "{colors.legend}"
    size: "18px"
  tick-off:
    backgroundColor: "{colors.display}"
    textColor: "{colors.legend-dim}"
    size: "18px"
  log:
    backgroundColor: "{colors.display}"
    textColor: "{colors.legend}"
    typography: "{typography.log}"
    padding: "6px 4px"
---

# Design System: LiveCues VideoCues

## Overview

**Creative North Star: "The Silkscreen Desk"**

The control window is a piece of show hardware: a matte dark panel with
legends silkscreened onto it, values sitting in recessed display slots, and
keys you press, not click. An operator uses it in a dark room, mid-show, with
their attention split between this screen, the stage and the projector. Every
decision follows from that. The panel is **calm, legible and deliberate**.
Everything reads at a glance, nothing moves or glows unless the state changed,
and every mark on the panel means something.

The density is a working rack unit's: compact and evenly spaced, nothing
decorative. Hierarchy comes from tone and position, not size. Primary text is
one warm off-white, secondary text is one dimmer step, and a single orange is
the only voice raised above the rest. State colours (green, red, amber) are
indicator lamps. They report what the system is doing and are never used for
decoration.

The output window, which the audience sees, is outside this system. It stays
plain black. The theme is for the operator, never the audience.

**Key Characteristics:**
- Dark only. There is no light theme.
- Flat: depth is tone (Bar → Chassis → Display) plus 1px rules, never shadows.
- Square corners everywhere. The one exception is the key's single chamfered corner (top right).
- One Signal Orange: the one lit key, keyboard focus, selection and the selected tab.
- State is always a drawn shape plus a word, never colour alone.
- IBM Plex Sans for anything printed on the panel, IBM Plex Mono for any value the machine reports.

## Colors

A near-black, slightly olive chassis palette with warm off-white legends,
one hot orange and three indicator-lamp colours.

### Primary
- **Signal Orange** (`signal`): the system's single raised voice. It fills
  the one lit key in a view (Save on Edit), draws the 2px keyboard-focus ring,
  underlines the selected tab (3px), fills a checked tick, marks text selection,
  colours "VideoCues" in the top bar and colours the name of the clip that is
  playing.
- **Signal Ink** (`signal-ink`): text and glyphs on a Signal fill, and the
  focus ring drawn inside a lit key. Never used on its own.

### Neutral
- **Chassis Black** (`chassis`): the panel itself, and the window and dialog
  background. It also fills a sunk key.
- **Bar** (`bar`): the darker strip above the panel (top bar, table headers,
  tooltips, combo popups).
- **Display** (`display`): the recessed slots. Readouts, fields, the MIDI log
  and the mapping table all sit in it. It is the darkest tone, so it reads as
  sunk into the panel.
- **Key** (`key`) / **Key Hover** (`key-hover`): the key face and its hover
  face. Key Hover also colours scrollbar handles.
- **Edge** (`edge`): the 1px border round every Display slot and field, and
  the outline of a quiet key.
- **Line** (`line`): 1px dividers between sections and clusters, under the
  bar and tab strip, and between table rows.
- **Active Wash** (`active-wash`): a selected log line or combo-popup row.
  It is a tint, not a highlight.
- **Legend** (`legend`): all primary text and glyphs.
- **Legend Dim** (`legend-dim`): secondary text: caption legends, hotkey
  hints, unselected tabs, placeholders and disabled text.

### Indicator lamps
- **LED Green** (`led-green`): something is live and healthy. Used for a
  playing cue (triangle) and for MIDI connected (disc).
- **LED Red** (`led-red`): "something is on". Used for the idle loop owning
  the output (square) and the sunk Return to Idle key.
- **Warn Amber** (`warn-amber`): needs attention. Used for MIDI offline, a
  missing file or a closed output (ring).

### Named Rules
**The Lit-Key Rule.** At most one Signal-filled key per view, and it is the
view's forward action. Run has none: nothing there moves the operator
forward.

**The LED Rule.** Green, red and amber only report state, and always appear
beside a drawn shape and a word. They never fill a key face, tint a
background or decorate.

**The Dark Room Rule.** Text is Legend or Legend Dim. No new greys, no new
hues. Every colour in a widget comes from a token in `theme.py`, never a
hard-coded hex.

## Typography

**Sans:** IBM Plex Sans (Medium 500, SemiBold 600, Bold 700)
**Mono:** IBM Plex Mono (Regular 400, Medium 500)

Both are bundled in `src/assets/fonts` (OFL) and registered at start-up,
because the stage machine may be offline.

**Character:** Plex is engineered, slightly mechanical and plain. Sans is the
ink printed on the panel, and Mono is the readout the machine writes into it.

### Hierarchy
- **Title** (600, 18px): the top bar only. "LiveCues" in Legend,
  "VideoCues" in Signal Orange.
- **Body** (500, 14px): the application default: field text, the tick
  label, dialog text.
- **Key label** (600, 14px, 0.04em): key faces. A lit key goes up to 700.
- **Tab** (600, 12px, 0.12em, uppercase): Run / Edit.
- **Legend** (600, 11px, 0.12em, uppercase): every caption printed on the
  panel (OUTPUT, MIDI DEVICE, STEP, CROP EDGES), table headers and the state
  word in a state chip.
- **Hint** (600, 10px, 0.12em, uppercase): the hotkey printed at the right
  of a key (CTRL+B).
- **Now playing** (Mono 500, 14px): the clip name in the Output slot.
- **Readout** (Mono 400, 13px): device, channel and display readouts, paths,
  and the MIDI detail in the bar (12px).
- **Log** (Mono 400, 12px): MIDI activity lines.

### Named Rules
**The Silkscreen Rule.** Anything that labels the panel is a legend: small,
spaced, upper-case, Legend Dim. Anything the machine reports is in Mono.
Words the operator acts on (key labels) are sentence-case Sans.

**The QFont Rule.** Fonts are set as QFont objects through
`theme.ui_font` / `mono_font` / `legend_font` / `key_font`, never in the
style sheet. QSS cannot do letter-spacing, and a QSS `font` rule overrides
`setFont`, which would strip the legend tracking.

## Layout

The window opens at 760 × 800 and stacks three bands: the **top bar**
(52px), the **tab strip** (40px, Line under it) and the **page**, a single
column with a 16px margin on all sides.

Inside a page, the rhythm is set by the 36px key/field height. Rows of keys
and slots sit 8px apart, keys within a cluster 6px apart, and a caption
legend sits directly above the thing it labels. Sections are separated by
a 1px Line rule with 10px of space either side (an 18px gap from row to
rule). Clusters within a section (Move / Zoom / Crop edges) are 24px apart
and split by vertical Line rules.

The page grows downward into one stretch element: the MIDI log on Run and
the mapping table on Edit. The bottom key row always stays pinned. It puts
secondary actions at the left (Add mapping on Edit) and the
view-ending actions at the right (Show Output and Fullscreen; Cancel and
Save).

## Elevation & Depth

The system is flat. Depth is three tones, not light: Bar sits above the
panel, Chassis is the panel, and Display is sunk into it. Edges are drawn
with 1px Edge and Line rules. Nothing on the panel casts a shadow, uses a
gradient or glows.

### Named Rules
**The Flat-Panel Rule.** No shadows on the panel, ever. The single exception
is a transient popup (combo list, tooltip). It is already separated by a
Bar face and an Edge line, and may keep the platform's native drop shadow,
but we never add one ourselves.

**The Sunk-Is-On Rule.** A pressed-in look is reserved for state, not
decoration. A key sinks (Chassis face, red inset outline) only while
something it controls is on.

## Shapes

Every corner is square (0 radius). That covers slots, fields, the table,
ticks, scrollbars and dialogs.

The **key** is the one silhouette with character: a rectangle with its top
right corner cut at 45° (8px chamfer). It is painted (`theme.Key`) because
QSS cannot clip a chamfer. The keyboard-focus ring follows the same
silhouette, inset 4px with a 6px chamfer.

State shapes are drawn, never typed: an **11px disc** (live), **ring**
(waiting or warning), **square** (idle) and **triangle** (playing). Key
symbols are drawn too: filled triangles for direction and play, and 2px
square-capped strokes for plus, minus and cross. Unicode arrows and ✕ are
never used in key text.

## Components

### Keys (`theme.Key`)
*Pressed, not clicked.* A flat face that inverts on press and sinks while
something is on.
- **Shape:** 36px tall, chamfered top-right (8px), 16px side padding.
  Square keys are 40px wide (Move arrows) or 52px (Crop/Uncrop). Zoom keys
  are 84px.
- **Normal:** Key face, Legend label. Hover lifts to Key Hover.
- **Pressed:** inverts to a Legend face with Chassis text.
- **Lit:** Signal Orange face, Signal Ink label at 700. Hover mixes in 12%
  Legend. At most one per view.
- **Quiet:** no face, a 2px-wide Edge outline clipped to the silhouette
  (1px visible); hover fills it with Key. Used for Reset view and the
  per-row remove key.
- **Sunk:** Chassis face, a 2px LED Red inset outline, and LED Red label and
  hint. Used only for Return to Idle while the idle loop owns the output.
- **Disabled:** whole key at 40% opacity.
- **Focus:** a 2px Signal ring inside the key, inset 4px (Signal Ink on a lit
  key). It is drawn only when focus arrived from the keyboard, like
  `:focus-visible`.
- **Hint:** a hotkey printed in the Hint style at the right, in Legend Dim
  (70% Signal Ink on lit, 75% red on sunk). The label then left-aligns.
- **Glyph:** a drawn symbol alone, or 18px before the label.

### Top bar
Bar face, 52px, Line under it. The title sits at the left. The MIDI state
sits at the right: a reason in Legend Dim Mono 12px, then a state chip
(green disc MIDI CONNECTED / dim ring CONNECTING… / amber ring MIDI
OFFLINE).

### Tabs (`theme.Tab`)
Run and Edit split the strip equally, 40px tall. Unselected tabs are in
Legend Dim and lift to Legend on hover. The selected tab is Legend with a
3px Signal underline across its full width. Leaving Edit with unsaved
changes asks first: **Save** (lit), **Discard**, **Keep editing** (Escape).

### State chip (`theme.StateChip`)
An 11px drawn shape, 7px gap, then an upper-case legend word. It sets the
widget's accessible name to the word. The **Output slot** on Run is a
Display slot holding a chip and the clip name:

| Output | Shape | Word | Clip name |
|---|---|---|---|
| A cue is playing | LED Green triangle | PLAYING | Signal Orange |
| Idle loop (or black) | LED Red square | IDLE ON OUTPUT | Legend Dim |
| Mapped file missing | Warn Amber ring | MISSING FILE | Warn Amber |
| Output window closed | Warn Amber ring | OUTPUT CLOSED | Legend Dim |

**Return to Idle** sits beside the slot and sinks red whenever the idle loop
owns the output. There is no filled red key anywhere.

### Readouts and fields
- **Run values:** on Run, only the Output slot is recessed (56px, Mono 20px
  clip name). Device, channel and display are plain Mono 13px values under
  their legends, so they can't be mistaken for editable fields. Each of Move,
  Zoom and Crop prints its current value in Mono 13px on one shared line under
  its keys; the crop rows are Crop and Restore.
- **Readouts** (`theme.readout`): a Display slot with a 1px Edge, 10px
  padding and Mono 13px. They are read-only and selectable, and are changed
  on Edit.
- **Fields** (line edits, spin boxes, combo boxes): a Display slot with a
  1px Edge, 8px padding and 34px minimum inner height. Focus thickens the
  border to 2px Signal. Disabled text drops to Legend Dim. Spin buttons are
  20px Key faces split by Edge lines, with 8px drawn arrows from
  `assets/ui`. The combo popup is Bar with an Edge line, and its selected
  row is Active Wash.

### Tick (`theme.Tick`)
An 18px square. When on, it is a Signal fill with a drawn Signal Ink check
and the label is in Legend. When off, it is an empty Display box with a
Legend Dim outline and the label is in Legend Dim. The whole row is
clickable. The keyboard-focus ring is a Signal square 3px outside the box.

### Mapping table and log
- **Mapping table:** a Display panel with an Edge line. Headers are Bar at
  30px in the Legend style over a Line rule. Rows are 46px (a 36px field
  with 5px above and below), separated by Line. Each row has Browse…, Test
  (play glyph) and a quiet remove key (cross glyph).
- **MIDI log:** a Display panel in Mono 12px. It keeps 500 lines and scrolls
  to the newest. Selected lines are Active Wash.
- **Scrollbars:** a 10px Display track and a Key Hover handle (Edge on
  hover), with no arrow buttons.

## Do's and Don'ts

### Do:
- **Do** use `theme.Key` for every action in the control window. Use
  `variant="lit"` for the view's single forward action, `"quiet"` for
  low-stakes or destructive-adjacent actions, and `set_sunk(True)` only for
  "something is on".
- **Do** take every colour from the tokens in `theme.py` (`theme.SIGNAL`,
  `theme.CHASSIS`, …).
- **Do** caption every slot and cluster with `theme.legend()` placed
  directly above it.
- **Do** pair every state colour with a drawn shape and an upper-case word
  (`theme.StateChip`).
- **Do** keep keys and fields at 36px and corners square. The 8px top-right
  chamfer on keys is the only cut.
- **Do** show the focus ring for keyboard focus only.
- **Do** keep native file dialogs native, and keep the window frame dark
  (`setColorScheme(Dark)` on Qt 6.8+).

### Don't:
- **Don't** use QPushButton for actions in the control window. The QSS rule
  for it exists only to flatten buttons in system dialogs.
- **Don't** hard-code a hex in a widget, or add a new grey or hue.
- **Don't** put fonts in the style sheet. It overrides the legend tracking.
- **Don't** light more than one key per view, or fill a key red.
- **Don't** use colour alone to report state.
- **Don't** add shadows, gradients, glows or rounded corners to the panel.
- **Don't** put Unicode arrows or ✕ in key text. Use a drawn `glyph=`.
- **Don't** add a light theme.
- **Don't** theme the output window. It stays plain black.
