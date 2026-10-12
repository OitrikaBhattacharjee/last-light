"""Quest puzzle for Last Light. One piece per day, stored only on this machine."""
import datetime as dt
import json
import os
import random
import tempfile

COLS, ROWS = 4, 3
TOTAL = COLS * ROWS


def fresh(finished=0):
    order = list(range(TOTAL))
    random.shuffle(order)
    return {"order": order, "got": 0, "last": None, "finished": finished}


def load(path):
    """Read saved progress. Anything missing or damaged starts a fresh puzzle."""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        ok = (sorted(d["order"]) == list(range(TOTAL))
              and isinstance(d["got"], int) and 0 <= d["got"] < TOTAL
              and isinstance(d["finished"], int) and d["finished"] >= 0
              and (d["last"] is None or isinstance(d["last"], str)))
        if ok:
            return d
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return fresh()


def save(path, d):
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(d, f)
    os.replace(tmp, path)


def award(d, today):
    """Give one piece, at most one per calendar day.
    Returns (state, status) where status is 'already', 'piece' or 'complete'."""
    if d["last"] == today.isoformat():
        return d, "already"
    d = dict(d, got=d["got"] + 1, last=today.isoformat())
    if d["got"] >= TOTAL:
        return fresh(d["finished"] + 1), "complete"
    return d, "piece"


def scene(revealed=None):
    """A small landscape. Cells not in `revealed` are covered. None shows it all."""
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" role="img" '
        'aria-label="A cabin on a hill with a tree">',
        '<rect width="400" height="300" fill="#d3e4e6"/>',
        '<circle cx="320" cy="70" r="30" fill="#e6c26b"/>',
        '<path d="M0 190 Q100 120 220 175 T400 160 V300 H0Z" fill="#a3bfa6"/>',
        '<path d="M0 230 Q130 170 260 220 T400 215 V300 H0Z" fill="#6f9777"/>',
        '<rect x="70" y="190" width="14" height="40" fill="#6b4f3a"/>',
        '<ellipse cx="77" cy="175" rx="32" ry="38" fill="#4d7a5a"/>',
        '<rect x="230" y="185" width="80" height="55" fill="#b5835a"/>',
        '<polygon points="222,187 270,148 318,187" fill="#7a4b3a"/>',
        '<rect x="260" y="208" width="20" height="32" fill="#5a3d2e"/>',
        '<rect x="236" y="198" width="14" height="14" fill="#f1e3b5"/>',
    ]
    if revealed is not None:
        cw, ch = 400 // COLS, 300 // ROWS
        for i in range(TOTAL):
            if i not in revealed:
                x, y = (i % COLS) * cw, (i // COLS) * ch
                parts.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#e4e1da" '
                             'stroke="#b9b5aa" stroke-width="2"/>' % (x, y, cw, ch))
    parts.append("</svg>")
    return "".join(parts)
