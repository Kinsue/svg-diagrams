"""Render flow / layered architecture diagrams to SVG without a browser.

Layer-based deterministic layout: author declares ordered layers, each with
boxes; edges are drawn as orthogonal elbows. See REFERENCE.md for the schema.
"""

TONES = {
    "info": ("#eef2ff", "#6366f1", "#1e1b4b"),
    "ok": ("#f0fdf4", "#4ade80", "#14532d"),
    "warn": ("#fffbeb", "#fbbf24", "#92400e"),
    "danger": ("#fef2f2", "#f87171", "#991b1b"),
    "muted": ("#f8fafc", "#cbd5e1", "#334155"),
    "store": ("#f5f3ff", "#a78bfa", "#4c1d95"),
}

FONT = "Noto Sans CJK SC,Source Han Sans SC,Microsoft YaHei,WenQuanYi Zen Hei,Droid Sans Fallback,DejaVu Sans,sans-serif"

BW, BH, GX, GY = 196, 62, 104, 30
PAD, TITLE_H = 44, 78
LTITLE_H = 30


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _w(s, size):
    return sum(size if ord(c) > 0x2E80 else size * 0.55 for c in s)


def _wrap(s, size, maxw):
    out, cur = [], ""
    for c in s:
        if _w(cur + c, size) > maxw and cur:
            out.append(cur)
            cur = c
        else:
            cur += c
    if cur:
        out.append(cur)
    return out


def _rect(x, y, w, h, fill, stroke="none", rx=8, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    s = "" if stroke == "none" else f' stroke="{stroke}" stroke-width="1.5"'
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{s}{d}/>'


def _path(d, stroke, marker=None, dash=None):
    m = f' marker-end="url(#{marker})"' if marker else ""
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="1.6" stroke-linejoin="round"{ds}{m}/>'


def _text(x, y, s, anchor="middle", size=14, fill="#111827", bold=False):
    b = ' font-weight="600"' if bold else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{FONT}" font-size="{size}" fill="{fill}"{b}>{_esc(s)}</text>'


def _label(x, y, s, size=12, fill="#334155", bold=False, anchor="middle"):
    w = _w(s, size)
    bx = {"middle": x - w / 2 - 5, "end": x - w - 5, "start": x - 5}[anchor]
    out = [_rect(bx, y - size + 1, w + 10, size + 7, "#ffffff", rx=3)]
    out.append(_text(x, y, s, anchor, size, fill, bold))
    return out


def _box(spec):
    if isinstance(spec, str):
        return {"id": spec, "label": spec, "sub": "", "tone": "info"}
    s = dict(spec)
    s.setdefault("id", s.get("label", ""))
    s.setdefault("label", s["id"])
    s.setdefault("sub", "")
    s.setdefault("tone", "info")
    return s


def render(title, subtitle, layers, edges, out_path, direction="LR", notes=None):
    norm = [{"title": l.get("title"), "boxes": [_box(b) for b in l.get("boxes", [])]} for l in layers]
    pos = {}
    ncol = len(norm)
    maxrows = max((len(l["boxes"]) for l in norm), default=1) or 1
    span_main = ncol * BW + (ncol - 1) * GX if direction == "LR" else maxrows * BW + (maxrows - 1) * GX
    span_cross = maxrows * BH + (maxrows - 1) * GY if direction == "LR" else ncol * BH + (ncol - 1) * GY
    W = PAD * 2 + span_main
    CONTENT_BOTTOM = TITLE_H + PAD + span_cross

    for ci, layer in enumerate(norm):
        nb = len(layer["boxes"])
        block = nb * BH + (nb - 1) * GY
        off = (span_cross - block) / 2
        for bi, b in enumerate(layer["boxes"]):
            if direction == "LR":
                x = PAD + ci * (BW + GX)
                y = TITLE_H + PAD + off + bi * (BH + GY)
            else:
                x = PAD + off + bi * (BW + GX)
                y = TITLE_H + PAD + ci * (BH + GY)
            pos[b["id"]] = (x, y)

    E = []
    PENDING = []
    for ci, layer in enumerate(norm):
        if not layer["title"]:
            continue
        xs = [pos[b["id"]] for b in layer["boxes"]]
        if not xs:
            continue
        if direction == "LR":
            gx, gy = PAD + ci * (BW + GX) - 20, TITLE_H + PAD - LTITLE_H
            gw = BW + 40
            gh = span_cross + LTITLE_H
        else:
            gx, gy = PAD - 20, TITLE_H + PAD + ci * (BH + GY) - 20
            gw = span_main + 40
            gh = BH + 40
        E.append(_rect(gx, gy, gw, gh, "#f8fafc", "#cbd5e1", 12, "6 5"))
        E.append(_text(gx + 14, gy + 20, layer["title"], "start", 13, "#64748b", True))

    for e in edges:
        if isinstance(e, dict):
            frm, to, lab = e["from"], e["to"], e.get("label", "")
            dash = e.get("dashed", False)
        else:
            frm, to = e[0], e[1]
            lab = e[2] if len(e) > 2 else ""
            dash = False
        if frm not in pos or to not in pos:
            continue
        (fx, fy), (tx, ty) = pos[frm], pos[to]
        if direction == "LR":
            sx, sy = fx + BW, fy + BH / 2
            dx, dy = tx, ty + BH / 2
            mx = (sx + dx) / 2 if dx > sx else (sx + 34)
            d = f"M{sx},{sy} H{mx} V{dy} H{dx}"
            lx, ly = mx, (sy + dy) / 2
        else:
            sx, sy = fx + BW / 2, fy + BH
            dx, dy = tx + BW / 2, ty
            my = (sy + dy) / 2 if dy > sy else (sy + 34)
            d = f"M{sx},{sy} V{my} H{dx} V{dy}"
            lx, ly = (sx + dx) / 2, my
        E.append(_path(d, "#64748b", "arw", "6 4" if dash else None))
        if lab:
            ls = _wrap(lab, 12, (GX - 22) if direction == "LR" else (BW - 22))
            for li, ln in enumerate(ls):
                PENDING.append([lx, ly + 4 - (len(ls) - 1) * 8 + li * 15, ln, direction])

    LABEL_BOTTOM = CONTENT_BOTTOM
    placed = [(pos[b["id"]][0] - 4, pos[b["id"]][1] - 4,
               pos[b["id"]][0] + BW + 4, pos[b["id"]][1] + BH + 4)
              for b in (b for l in norm for b in l["boxes"])]

    def fits(box, cand):
        for q in placed:
            if not (cand[2] < q[0] - 4 or cand[0] > q[2] + 4 or cand[3] < q[1] - 4 or cand[1] > q[3] + 4):
                return False
        return True

    for px, py, txt, dirn in PENDING:
        lw = _w(txt, 12)
        lh = 19
        cx = min(max(px, PAD + lw / 2 + 6), W - PAD - lw / 2 - 6)
        for _ in range(24):
            box = (cx - lw / 2 - 5, py - 11, cx + lw / 2 + 5, py + 8)
            if fits(box, box):
                break
            py += 16
        placed.append(box)
        E.extend(_label(cx, py, txt))
        LABEL_BOTTOM = max(LABEL_BOTTOM, box[3])

    notes_h = (len(notes) * 21 + 30) if notes else 0
    H = int(max(CONTENT_BOTTOM + 34, LABEL_BOTTOM + 18) + notes_h)

    for b in [b for l in norm for b in l["boxes"]]:
        x, y = pos[b["id"]]
        fill, stroke, fg = TONES.get(b["tone"], TONES["info"])
        E.append(_rect(x, y, BW, BH, fill, stroke))
        lines = _wrap(b["label"], 15, BW - 20)
        base = y + (BH - (len(lines) * 19 + (16 if b["sub"] else 0))) / 2 + 15
        for i, ln in enumerate(lines):
            E.append(_text(x + BW / 2, base + i * 19, ln, "middle", 15, fg, True))
        if b["sub"]:
            E.append(_text(x + BW / 2, base + len(lines) * 19 + 1, b["sub"], "middle", 12, "#64748b"))

    out = [_text(PAD - 6, 32, title, "start", 20, "#0f172a", True),
           _text(W - PAD + 6, 32, subtitle, "end", 13, "#94a3b8")]
    if notes:
        base = H - notes_h + 22
        for i, t in enumerate(notes):
            out.append(_text(PAD - 6, base + i * 21, t, "start", 13, "#475569"))
    notes = notes or []
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
<defs>
<marker id="arw" markerWidth="11" markerHeight="11" refX="10" refY="3.5" orient="auto"><path d="M0,0 L0,7 L10,3.5 z" fill="#64748b"/></marker>
</defs>
<rect width="{W}" height="{H}" fill="#ffffff"/>
{chr(10).join(out)}
{chr(10).join(E)}
</svg>'''
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    return W, int(H)