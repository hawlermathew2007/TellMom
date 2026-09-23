"""Draws the isometric part drawings the website uses (site/index.html).

Prints one <symbol> per part, ready to paste into the hidden <svg><defs> at the
top of site/index.html, replacing the existing ones:

    python scripts/site-icons.py

Colours are written as attributes, not classes: the page shows the drawings
through <use>, whose shadow tree the page's CSS cannot reach. Keep FILLS in
step with the colour tokens in site/styles.css.
"""
import math
import re

C30, S30 = math.cos(math.pi / 6), math.sin(math.pi / 6)


class Iso:
    def __init__(self, s=1.0, ox=0.0, oy=0.0):
        self.s, self.ox, self.oy = s, ox, oy
        self.out = []

    def p(self, x, y, z):
        return (self.ox + (x - y) * C30 * self.s, self.oy + (x + y) * S30 * self.s - z * self.s)

    def poly(self, pts, cls):
        d = " ".join(f"{a:.1f},{b:.1f}" for a, b in (self.p(*q) for q in pts))
        self.out.append(f'<polygon class="{cls}" points="{d}"/>')

    def box(self, x, y, z, w, d, h, top="f-top", right="f-r", left="f-l"):
        self.poly([(x, y, z + h), (x + w, y, z + h), (x + w, y + d, z + h), (x, y + d, z + h)], top)
        self.poly([(x + w, y, z), (x + w, y + d, z), (x + w, y + d, z + h), (x + w, y, z + h)], right)
        self.poly([(x, y + d, z), (x + w, y + d, z), (x + w, y + d, z + h), (x, y + d, z + h)], left)

    def cyl(self, cx, cy, z, r, h, top="f-top", side="f-l"):
        rx, ry = r * self.s * math.sqrt(2) * C30, r * self.s * math.sqrt(2) * S30
        bx, by = self.p(cx, cy, z)
        tx, ty = self.p(cx, cy, z + h)
        self.out.append(
            f'<path class="{side}" d="M{bx-rx:.1f},{by:.1f} A{rx:.1f},{ry:.1f} 0 0 0 {bx+rx:.1f},{by:.1f} '
            f'L{tx+rx:.1f},{ty:.1f} L{tx-rx:.1f},{ty:.1f} Z"/>'
        )
        self.out.append(f'<ellipse class="{top}" cx="{tx:.1f}" cy="{ty:.1f}" rx="{rx:.1f}" ry="{ry:.1f}"/>')

    def line(self, a, b, cls="ln"):
        (x1, y1), (x2, y2) = self.p(*a), self.p(*b)
        self.out.append(f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')

    def svg(self):
        return "".join(self.out)


def pi_board(g):
    g.box(0, 0, 0, 34, 22, 2, top="f-green")
    g.box(12, 7, 2, 8, 8, 2, top="f-dark", right="f-dark", left="f-dark")      # SoC
    for i in range(10):                                                         # GPIO header
        g.box(4 + i * 2.6, 1.2, 2, 1.4, 1.4, 2.4, top="f-dark", right="f-dark", left="f-dark")
    g.box(27, 3, 2, 7, 6, 5)                                                    # USB
    g.box(27, 12, 2, 7, 6, 5)                                                   # Ethernet


def backend(g):
    for k in range(3):
        g.box(0, 0, k * 8, 24, 18, 7)
        g.line((24, 3, k * 8 + 3.5), (24, 11, k * 8 + 3.5), "ln-thin")
        g.cyl(24.2, 14.5, k * 8 + 3.5, 0.9, 0, top="f-signal")


def classifier(g):
    g.box(0, 0, 0, 24, 24, 6)
    g.cyl(12, 12, 6, 8, 3, top="f-sky", side="f-r")
    g.cyl(12, 12, 9, 4, 5, top="f-top", side="f-l")


def proxy(g):
    g.box(0, 0, 0, 26, 18, 16)
    # blindfold: a band round the two visible sides, no top
    x, y, w, d, z, h = -0.4, -0.4, 26.8, 18.8, 7, 4
    g.poly([(x + w, y, z), (x + w, y + d, z), (x + w, y + d, z + h), (x + w, y, z + h)], "f-signal")
    g.poly([(x, y + d, z), (x + w, y + d, z), (x + w, y + d, z + h), (x, y + d, z + h)], "f-signal")
    g.poly([(x + w, y + d * 0.35, z + h), (x + w + 5, y + d * 0.2, z - 3), (x + w + 3, y + d * 0.42, z - 5), (x + w, y + d * 0.5, z + 1)], "f-signal")


def game(g):
    g.box(0, 0, 0, 30, 14, 4)
    g.box(3, 3, 4, 6, 2, 1.4, top="f-dark", right="f-dark", left="f-dark")
    g.box(6, 0.5, 4, 2, 7, 1.4, top="f-dark", right="f-dark", left="f-dark")
    g.cyl(21, 4, 4, 1.4, 1.2, top="f-action")
    g.cyl(25, 7, 4, 1.4, 1.2, top="f-signal")
    g.cyl(21, 9, 4, 1.4, 1.2, top="f-sky")


def laptop(g):
    g.box(0, 0, 0, 30, 20, 2)
    # screen hinged at the back edge (y=0), standing up
    g.poly([(0, 1, 2), (0, 19, 2), (0, 19, 20), (0, 1, 20)], "f-top")
    g.poly([(0, 3, 4), (0, 17, 4), (0, 17, 18), (0, 3, 18)], "f-sky")


def fit(draw, size):
    """Draw once to measure, then again scaled and centred in a size x size box."""
    g = Iso(1)
    draw(g)
    xs, ys = [], []
    for m in re.finditer(r'points="([^"]+)"', g.svg()):
        for pt in m.group(1).split():
            a, b = pt.split(",")
            xs.append(float(a)); ys.append(float(b))
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    s = (size - 8) / max(w, h)
    g2 = Iso(s, -min(xs) * s + (size - w * s) / 2, -min(ys) * s + (size - h * s) / 2)
    draw(g2)
    return g2.svg()


FILLS = {"f-top": "#ffffff", "f-r": "#e8f4fa", "f-l": "#a9d3ea", "f-green": "#3f8f5a",
         "f-dark": "#2a3240", "f-signal": "#ffcf1a", "f-action": "#cf2a16", "f-sky": "#c4e3f3",
         "ln": "none", "ln-thin": "none"}
STROKE = 'stroke="#14181f" stroke-width="1.6" stroke-linejoin="round" vector-effect="non-scaling-stroke"'
PARTS = [("pi", pi_board), ("backend", backend), ("classifier", classifier), ("proxy", proxy),
         ("game", game), ("laptop", laptop)]


if __name__ == "__main__":
    import re
    for name, draw in PARTS:
        svg = re.sub(r'class="([\w-]+)"', lambda m: f'fill="{FILLS[m.group(1)]}" {STROKE}', fit(draw, 120))
        print(f'    <symbol id="i-{name}" viewBox="0 0 120 120">{svg}</symbol>')
