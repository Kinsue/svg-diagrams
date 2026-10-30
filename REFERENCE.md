# REFERENCE

## `svgseq.render`

```python
render(title, subtitle, actors, ops, out_path, width=1480, font_size_label=14) -> (width, height)
```

`actors` is an ordered list of lifeline names (strings). They are evenly spread across `width`.

### Ops (tuples, applied in order)

| Op | Form | Effect |
|---|---|---|
| band | `("band", text[, tone])` | Full-width coloured phase band. Always open one per stage. |
| msg | `("msg", from, to, label[, dashed])` | Arrow between two lifelines. `dashed=True` for a return/reply. |
| self | `("self", actor, label)` | Self-call loop to the right of a lifeline. |
| note | `("note", a1, a2, [paras], [tone])` | Box spanning a1..a2; paragraphs are wrapped to fit. |
| alt_start | `("alt_start", label)` | Opens an `alt` block; dashed rule drawn at the right margin. |
| alt_else | `("alt_else", label)` | Closes the previous arm, opens the next. |
| alt_end | `("alt_end",)` | Closes the block. |
| foot | `("foot", text)` | Full-width footnote at the bottom. Repeat for each line. |

Arms must be balanced: every `alt_start` needs one `alt_end`; use `alt_else` between arms.

### Tones

`band`: `info` (default, indigo), `ok` (green), `warn` (amber), `danger` (red), `muted`.
`note`: `info` (default, amber), `ok`, `warn`, `danger`.

### Layout constants

`M=74` margin, `BOXW=190`, `BOXH=40`, `TOP=56`, first op baseline `y=152`.
Row pitch: `msg` 48, `self` 58, `band` 48, `note` height + 26, `alt` arms 30.
Label size 14 for messages, 13 for notes/alt/alt-frames. Footer 13 at 21px pitch.

Raise `width` past the default 1480 when you have more than ~7 actors, or labels will crowd.

## `svgflow.render`

```python
render(title, subtitle, layers, edges, out_path, direction="LR", notes=None) -> (width, height)
```

`layers` is an ordered list of `{"title": str|None, "boxes": [...]}`. Layer order is the flow order.
`direction` `"LR"` (columns, left to right) or `"TB"` (rows, top to bottom).

A box is a string (id == label) or a dict:

```python
{"id": "task", "label": "sa-snmp-task", "sub": "generate tasks", "tone": "info"}
```

`id` is what edges reference and must be unique. `sub` is the small grey line under the label.
A layer `title` draws a dashed frame around the whole layer — use it for zones
(`机房 A`, `控制面`, `数据面`) so ownership boundaries are visible.

`edges` is a list of `(from, to)`, `(from, to, label)`, or
`{"from": ..., "to": ..., "label": ..., "dashed": True}`. Unknown ids are skipped, not fatal.
Edges route as orthogonal elbows, so skipping layers is safe.

### Box tones

`info`, `ok`, `warn`, `danger`, `muted`, `store` (violet, for datastores).

### Layout constants

`BW=196`, `BH=62`, `GX=136`, `GY=30`, `PAD=44`, title band 78, layer-title band 30.
Canvas size is computed. Height grows to fit labels and notes.

Edge labels are wrapped to the inter-layer gap, then placed by a greedy pass that
treats **boxes and already-placed labels as obstacles** and nudges down until
clear. So labels never overlap each other or a box — but a dense graph can push a
label well below the diagram, where it detaches from its own edge and reads as a
floating legend. If that looks odd, shorten the labels or split the diagram
rather than raising `GX`. In a box-dense grid, the best fix is usually to **drop
the edge labels entirely** — when the arrows already encode direction, an
unlabelled but unambiguous edge beats a label parked at the bottom of the canvas.
Put the "what flows" detail in `notes` or the box `sub` text instead.

## Text metrics

Both renderers estimate width as `size` per full-width (CJK) char and `size * 0.55` per ASCII char.
Wrapping and white label backings derive from that estimate. It is approximate; if a label still
collides, shorten the text rather than tuning the constants.

## Rendering a proof PNG

`cairosvg` may need `--break-system-packages` on this machine:

```bash
pip install --quiet --break-system-packages cairosvg
```

Then rasterize per the snippet in `SKILL.md`. Read the PNG back as an image before declaring done.