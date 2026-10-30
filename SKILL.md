---
name: svg-diagrams
description: Generate crisp vector SVG diagrams (UML sequence diagrams and layered flow/architecture diagrams) from a small Python op-list, with no browser or mermaid-cli, then self-verify the layout by rasterizing to PNG and reading it back. Use when the user asks for a diagram, 时序图, 流程图, 架构图, 调用链/时序/流程图, wants a diagram embedded in Markdown docs, or when a mermaid diagram came out too dense, overlapped, or failed to parse (mermaid reserved words such as link/continue break it).
---

# SVG Diagrams

Produce readable, scalable SVG diagrams. Text stays real text, so diagrams stay searchable and diff-able.

## Quick start

```python
import sys; sys.path.insert(0, "<skill>/scripts")
from svgseq import render

render("SNMP 主链路时序图", "branch: idc_isolation",
       ["sa-zeus", "CMDB", "sa-snmp-task", "sa-snmp-work"],
       [("band", "阶段 0 · 资产获取"),
        ("msg", "sa-zeus", "sa-snmp-task", "GET /switch-assets", True),
        ("note", "sa-snmp-task", "CMDB", ["仅 Zeus 报错才回落 CMDB"]),
        ("foot", "注 1：隔离只发生在选择侧")],
       "out.svg")
```

`<skill>` = the directory containing this `SKILL.md`.

## Renderers

| Module | For | API |
|---|---|---|
| `scripts/svgseq.py` | UML sequence diagrams | `render(title, subtitle, actors, ops, out_path, width=1480)` |
| `scripts/svgflow.py` | flow / layered architecture | `render(title, subtitle, layers, edges, out_path, direction="LR", notes=None)` |

Full op schemas, tone tables and layout constants: see [REFERENCE.md](REFERENCE.md).
Worked examples: see [EXAMPLES.md](EXAMPLES.md).

## Workflow

1. **Decide the shape.** Interactions over time between named parties → `svgseq`. Stages/pipelines/ownership layers → `svgflow`.
2. **Draft content, not decoration.** Write the op list from the facts you already established. Do not pad arrows with code references. Authoring is a **design task**: derive nodes from the system's *components and relationships*, never by enumerating a diff. A file list produced by a recon pass is raw material, not the node set (see Information-architecture rules).
3. **Render** to the target path (repo root or `docs/` next to the report).
4. **Verify** (see below). Fix and re-render until clean.
5. **Link** the SVG from the Markdown report with `> 矢量图：[`name.svg`](./name.svg)`.
6. Keep the `.py` build script in a temp dir; commit only the `.svg`.

## Design rules (learned the hard way)

- **Never use `mmdc` / mermaid-cli here.** Puppeteer's Chrome is not installed and the download is blocked. Emit SVG directly.
- **Arrow labels answer "who → whom → what", never "where in the code".** File/line/function names go in prose or a table. Packing them into arrows is what makes diagrams unreadable.
- **Lifelines and group frames paint first (behind); every label carries an opaque white backing box.** The renderers already do this — keep using them instead of hand-rolling SVG.
- **Avoid mermaid reserved words even in prose labels** (`link`, `continue`, `end`, `alt`, `loop`, `opt`, `note`, `click`, `box`, `break`, `rect`, `activate`). Users often paste SVG content back into mermaid, and these words break the parse.
- **Use tones to carry meaning**, not decoration: `info` neutral, `ok` safe step, `warn` caveat, `danger` risk. In a risk diagram, make the one safe step `ok` so the dangerous ones read as the exception.
- **CJK font stack is embedded** (`Noto Sans CJK SC` → 思源 → 微软雅黑 → 文泉驿 → `Droid Sans Fallback`). Keep it.
- Put long explanation in `foot` lines or `note` blocks; the renderer wraps them.

## Information-architecture rules (what actually decides readability)

These come from a real failure: an architecture diagram that was really a
visualised `git diff` — `.go` filenames, function names, an HTTP route and a
Mongo collection all drawn as same-sized boxes, coloured by "new / modified",
and numbered ①..⑥ in an order that fought the arrows. It rendered fine and was
unreadable. **The renderer is never the problem; the shape of the content is.**
A diagram that is a commit message with boxes is the anti-pattern. Before you
draw, satisfy every rule below:

- **One abstraction level per diagram.** Every node must be the *same kind of
  thing* (all services, or all data stores, or all pipeline stages). Never mix
  source files, functions, HTTP routes, tables and external systems in one
  graph — the reader cannot build one mental model. Architecture diagrams plot
  **components**, never `foo.go`, `ApplyThing()`, or `path:line`. Those go in
  prose or a table beside the diagram.
- **Choose node granularity from the reader's question, not from your change
  set.** "What does the system do?" ⇒ components. If your node list is your
  `git status`, you are drawing a commit message. Stop and re-abstract.
- **Exactly one main direction, and it is the real causal/data direction.**
  L→R or T→B must equal how data/control actually moves. Put entry points at
  the origin. Do **not** number stages ①..⑥ in an order that contradicts the
  arrows — a number sequence is itself a direction claim.
- **Preserve the topology.** If the system is `many → one (converge) → store →
  many (fan out)`, draw the fan-in and the fan-out. Do not flatten a
  convergence into a linear numbered sequence; the convergence is usually the
  whole point.
- **Colour encodes the component's role, not the change.** Use tone for role or
  risk (store, entry, the single changed step, danger). Never colour by
  "added / modified / untouched" — that is a code-review dimension and it
  buries the architecture under edit status.
- **No orphan nodes.** Every box must have at least one edge. An unconnected
  box is noise, not information: give it a relationship or delete it.
- **Edges carry one consistent semantic.** Don't let solid mean "write" on one
  edge and "control" on another while dashed means "read" here and "action"
  there. Declare the semantics once (e.g. solid = call/write, dashed =
  read/async) and keep it everywhere.
- **Prefer no edge label over an ambiguous one.** If direction already says it,
  a label only helps if it stays attached to its edge. In box-dense graphs the
  flow renderer pushes crowded labels far below their edges (see REFERENCE.md);
  when that happens, drop the label rather than ship a detached legend.
- **Authoring is a design task.** Do not hand a raw `git status` / diff to a
  code-search pass and accept a file-per-box graph. Decide the abstraction
  level first, then fill in components.

## Verification

Rendering without erroring is **not** proof the diagram is readable.

```bash
python3 build.py && python3 -c "
import xml.dom.minidom, cairosvg
xml.dom.minidom.parse('d.svg')
s=open('d.svg').read().replace('Noto Sans CJK SC,Source Han Sans SC,Microsoft YaHei,WenQuanYi Zen Hei,Droid Sans Fallback,DejaVu Sans,sans-serif','Droid Sans Fallback')
open('_p.svg','w').write(s)
cairosvg.svg2png(url='_p.svg', write_to='d.png', scale=1.0, background_color='white')"
```

Then **read `d.png` back as an image** and check: no overlap, no clipped text, nothing outside the canvas, arrows point the right way, tone semantics are visible.

Also re-check the **content**, not just the pixels: is any node a filename/function/line number (abstraction-level leak)? Any orphan node? Does the ①..⑥ numbering agree with the arrows? Is the colour keyed to role rather than to "changed"? Fix the content before shipping — a clean render of a bad graph is still a bad graph.

The font substitution in that snippet only affects the PNG proof. Ship the SVG with the full font stack. A local `cairosvg` may still show tofu for some CJK glyphs — that is a preview artifact, not an SVG defect; trust the geometry.

## Files

- `scripts/svgseq.py` — sequence renderer
- `scripts/svgflow.py` — flow/architecture renderer
- `REFERENCE.md` — op schemas, tones, constants
- `EXAMPLES.md` — complete build scripts