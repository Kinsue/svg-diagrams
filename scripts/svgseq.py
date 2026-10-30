"""Render UML sequence diagrams to SVG without a browser or mermaid-cli.

Use as a module:  from svgseq import render ; render(title, subtitle, actors, ops, out)
Ops are tuples; see REFERENCE.md for the schema.
"""

TONES = {
    "info": ("#eef2ff", "#c7d2fe", "#1f2937"),
    "ok": ("#f0fdf4", "#86efac", "#14532d"),
    "warn": ("#fffbeb", "#fcd34d", "#92400e"),
    "danger": ("#fef2f2", "#fca5a5", "#991b1b"),
    "muted": ("#f8fafc", "#cbd5e1", "#334155"),
}

NOTE_TONES = {
    "info": ("#fffbeb", "#f59e0b", "#92400e"),
    "ok": ("#f0fdf4", "#22c55e", "#14532d"),
    "warn": ("#fffbeb", "#f59e0b", "#92400e"),
    "danger": ("#fef2f2", "#ef4444", "#991b1b"),
}


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


def _rect(x, y, w, h, fill, stroke="none", rx=6, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    s = "" if stroke == "none" else f' stroke="{stroke}" stroke-width="1.4"'
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{s}{d}/>'


def _line(x1, y1, x2, y2, stroke, dash=None, marker=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = f' marker-end="url(#{marker})"' if marker else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="1.5"{d}{m}/>'


def _path(d, stroke, marker=None):
    m = f' marker-end="url(#{marker})"' if marker else ""
    return f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="1.5"{m}/>'


def _text(x, y, s, anchor="middle", size=14, fill="#111827", bold=False):
    b = ' font-weight="600"' if bold else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{FONT}" font-size="{size}" fill="{fill}"{b}>{_esc(s)}</text>'


def _label(x, y, s, anchor="middle", size=14, fill="#111827", bold=False, bg=True):
    """Label with an opaque backing box so it never fights lifelines or gridlines."""
    out = []
    w = _w(s, size)
    bx = x - w / 2 - 5 if anchor == "middle" else x - 5
    if bg:
        out.append(_rect(bx, y - size + 2, w + 10, size + 8, "#ffffff", rx=3))
    out.append(_text(x, y, s, anchor, size, fill, bold))
    return out


def render(title, subtitle, actors, ops, out_path, width=1480, font_size_label=14):
    M, BOXW, BOXH, TOP = 74, 190, 40, 56
    ALT_X = width - 26
    step = (width - 2 * M) / (len(actors) - 1)
    X = {a: M + i * step for i, a in enumerate(actors)}
    BODY, HEAD = [], []
    st = {"y": 152, "alt_top": 0, "alt_last": 0}

    def band(t, tone):
        fill, stroke, color = TONES.get(tone, TONES["info"])
        BODY.append(_rect(M - 26, st["y"], width - 2 * (M - 26), 30, fill, stroke))
        BODY.append(_text(M - 16, st["y"] + 20, t, "start", 14, color, True))
        st["y"] += 48

    def note(a1, a2, paras, tone):
        fill, stroke, color = NOTE_TONES.get(tone, NOTE_TONES["info"])
        lh, pad = 19, 11
        x1 = min(X[a1], X[a2]) - BOXW / 2 + 14
        x2 = max(X[a1], X[a2]) + BOXW / 2 - 14
        lines = []
        for p in paras:
            lines += _wrap(p, 13, x2 - x1 - pad * 2)
        h = lh * len(lines) + pad * 2 - 5
        BODY.append(_rect(x1, st["y"], x2 - x1, h, fill, stroke, 6, "5 4"))
        for i, ln in enumerate(lines):
            BODY.append(_text(x1 + pad, st["y"] + pad + lh * i + 9, ln, "start", 13, color))
        st["y"] += h + 26

    def msg(frm, to, s, dashed):
        y = st["y"] + 18
        x1, x2 = X[frm], X[to]
        col = "#475569" if dashed else "#334155"
        BODY.extend(_label((x1 + x2) / 2, y - 9, s, "middle", font_size_label))
        BODY.append(_line(x1, y, x2, y, col, "7 5" if dashed else None, "arwd" if dashed else "arw"))
        st["y"] = y + 30

    def selfmsg(a, s):
        y = st["y"] + 12
        x = X[a]
        BODY.extend(_label(x + 32, y - 7, s, "start", font_size_label))
        BODY.append(_path(f"M{x},{y} h44 q10,0 10,10 v12 q0,10 -10,10 h-44", "#334155", "arw"))
        st["y"] = y + 46

    def alt_start(s):
        st["alt_top"] = st["alt_last"] = st["y"] + 4
        BODY.extend(_label(ALT_X - 8, st["y"] + 20, s, "end", 13, "#7c3aed", True, False))
        st["y"] += 30

    def alt_else(s):
        BODY.append(_line(ALT_X, st["alt_top"], ALT_X, st["y"], "#7c3aed", "6 4"))
        BODY.extend(_label(ALT_X - 8, st["y"] + 20, s, "end", 13, "#7c3aed", True, False))
        st["alt_last"] = st["y"]
        st["y"] += 30

    def alt_end():
        BODY.append(_line(ALT_X, st["alt_last"], ALT_X, st["y"] + 8, "#7c3aed", "6 4"))
        st["y"] += 36

    for op in ops:
        k = op[0]
        if k == "band":
            band(op[1], op[2] if len(op) > 2 else "info")
        elif k == "note":
            note(op[1], op[2], op[3], op[4] if len(op) > 4 else "info")
        elif k == "msg":
            msg(op[1], op[2], op[3], bool(len(op) > 4 and op[4]))
        elif k == "self":
            selfmsg(op[1], op[2])
        elif k == "alt_start":
            alt_start(op[1])
        elif k == "alt_else":
            alt_else(op[1])
        elif k == "alt_end":
            alt_end()

    H = st["y"] + 42
    for a in actors:
        HEAD.append(_rect(X[a] - BOXW / 2, TOP, BOXW, BOXH, "#eef2ff", "#6366f1"))
        HEAD.append(_text(X[a], TOP + BOXH / 2 + 6, a, "middle", 16, "#1e1b4b", True))
        HEAD.insert(0, _line(X[a], TOP + BOXH + 6, X[a], H - 10, "#cbd5e1", "5 5"))

    foots = [_text(M - 16, H + 16 + i * 21, op[1], "start", 13, "#475569")
             for i, op in enumerate([o for o in ops if o[0] == "foot"])]
    H += 16 + len(foots) * 21 + 14

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{H}" viewBox="0 0 {width} {H}" font-family="{FONT}">
<defs>
<marker id="arw" markerWidth="11" markerHeight="11" refX="10" refY="3.5" orient="auto"><path d="M0,0 L0,7 L10,3.5 z" fill="#334155"/></marker>
<marker id="arwd" markerWidth="11" markerHeight="11" refX="10" refY="3.5" orient="auto"><path d="M0,0 L0,7 L10,3.5 z" fill="#475569"/></marker>
</defs>
<rect width="{width}" height="{H}" fill="#ffffff"/>
{_text(M - 26, 28, title, "start", 20, "#0f172a", True)}
{_text(width - 26, 28, subtitle, "end", 13, "#94a3b8")}
{chr(10).join(HEAD)}
{chr(10).join(BODY)}
{chr(10).join(foots)}
</svg>'''
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    return width, int(H)


FONT = "Noto Sans CJK SC,Source Han Sans SC,Microsoft YaHei,WenQuanYi Zen Hei,Droid Sans Fallback,DejaVu Sans,sans-serif"