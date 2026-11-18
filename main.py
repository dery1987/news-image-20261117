#!/usr/bin/env python3
"""news-image-20261117: draw one front page summing up Tuesday 17 Nov 2026.

Pure Python 3.13 standard library. No network, no randomness, no time:
the same source always writes byte-identical /output/entry.png.
Run: mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import binascii
import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---- palette (newsprint) ----
PAPER = (247, 243, 234)
INK = (17, 17, 17)
WHITE = (255, 255, 255)
RED = (179, 35, 27)
NAVY = (30, 58, 95)
BLUE = (42, 100, 150)
SKY = (174, 205, 226)
ORANGE = (232, 120, 20)
GOLD = (233, 180, 40)
GREY = (110, 110, 105)
LIGHT = (238, 234, 222)
CRIMSON = (178, 34, 52)
GREEN = (46, 110, 62)

# ---- 5x7 bitmap font: each glyph is 7 rows, 5 bits, bit 4 = left column ----
FONT = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    " ": (0, 0, 0, 0, 0, 0, 0),
    "-": (0, 0, 0, 0x0E, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0x0C, 0x0C),
    ",": (0, 0, 0, 0, 0x0C, 0x04, 0x08),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    ":": (0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "/": (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
}


class Canvas:
    """RGB framebuffer with simple filled-shape drawing."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = self._idx(x0, yy)
            self.px[i:i + len(row)] = row

    def line(self, x0, y0, x1, y1, color, width=1):
        # Bresenham; thickness by stamping filled circles along the line.
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        r = max(1, width // 2)
        while True:
            self.fill_circle(x0, y0, r, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def fill_circle(self, cx, cy, r, color):
        if r <= 0:
            return
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(r * r - dy * dy))
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def circle(self, cx, cy, r, color, width=1):
        # Outline circle: stamp small circles along the circumference.
        steps = max(24, int(2 * math.pi * r))
        for i in range(steps):
            a = 2 * math.pi * i / steps
            self.fill_circle(int(cx + r * math.cos(a)),
                             int(cy + r * math.sin(a)),
                             max(1, width // 2), color)

    def fill_polygon(self, points, color):
        # Even-odd scanline fill.
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        y0, y1 = max(0, min(ys)), min(self.h - 1, max(ys))
        n = len(points)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x1, y1p = points[i]
                x2, y2p = points[(i + 1) % n]
                if (y1p <= y < y2p) or (y2p <= y < y1p):
                    t = (y - y1p) / (y2p - y1p)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                xa = int(math.ceil(xs[j]))
                xb = int(math.floor(xs[j + 1]))
                if xb >= xa:
                    self.fill_rect(xa, y, xb - xa + 1, 1, color)

    def star(self, cx, cy, r_out, r_in, points, color, rot=-math.pi / 2):
        pts = []
        for i in range(points * 2):
            r = r_out if i % 2 == 0 else r_in
            a = rot + math.pi * i / points
            pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
        self.fill_polygon(pts, color)

    def text(self, x, y, s, scale, color):
        """Draw text left-aligned at (x, y); glyph 5x7, advance 6*scale."""
        cx = x
        for ch in s:
            glyph = FONT.get(ch)
            if glyph is None:
                cx += 6 * scale
                continue
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        self.fill_rect(cx + col * scale, y + row * scale,
                                       scale, scale, color)
            cx += 6 * scale

    def text_width(self, s, scale):
        return max(0, len(s) * 6 * scale - scale)

    def text_centered(self, cx, y, s, scale, color):
        self.text(cx - self.text_width(s, scale) // 2, y, s, scale, color)


# ---- PNG encoder (filter 0, zlib level 9, no ancillary chunks) ----

def _chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data +
            struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF))


def encode_png(canvas):
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(canvas.h):
        raw.append(0)  # filter: None
        i = y * canvas.w * 3
        raw += canvas.px[i:i + canvas.w * 3]
    comp = zlib.compress(bytes(raw), 9)
    png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) +
           _chunk(b"IDAT", comp) + _chunk(b"IEND", b""))
    return png


# ---- icons: one simple, unmistakable picture per story ----

def wave(c, x0, x1, y, amp, color, width=3):
    pts = []
    x = x0
    while x <= x1:
        pts.append((x, int(y + amp * math.sin((x - x0) * 0.09))))
        x += 6
    for i in range(len(pts) - 1):
        c.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
               color, width)


def icon_strike(c, cx, cy):
    """Jet flying at an explosion burst over the sea (US strikes Iran)."""
    wave(c, cx - 210, cx + 210, cy + 78, 5, BLUE, 3)
    wave(c, cx - 210, cx + 210, cy + 92, 5, SKY, 3)
    # explosion burst
    c.star(cx + 105, cy - 5, 66, 30, 12, ORANGE)
    c.star(cx + 105, cy - 5, 36, 16, 12, GOLD)
    # jet, nose to the right, dark navy
    jx, jy = cx - 95, cy - 15
    c.fill_polygon([(jx - 70, jy - 6), (jx + 30, jy - 12), (jx + 78, jy),
                    (jx + 30, jy + 12), (jx - 70, jy + 8)], NAVY)
    c.fill_polygon([(jx - 5, jy - 8), (jx - 42, jy - 52), (jx - 28, jy - 8)],
                   NAVY)
    c.fill_polygon([(jx - 2, jy + 8), (jx - 30, jy + 42), (jx - 18, jy + 8)],
                   NAVY)
    c.fill_polygon([(jx - 70, jy - 6), (jx - 88, jy - 38), (jx - 56, jy - 6)],
                   NAVY)
    c.fill_circle(jx + 45, jy - 2, 5, WHITE)


def icon_bridge(c, cx, cy):
    """A bridge with its middle span dropped into the water (Kerch)."""
    deck_y = cy - 48
    # deck in two halves with a gap in the middle
    c.fill_rect(cx - 210, deck_y, 182, 12, INK)
    c.fill_rect(cx + 28, deck_y, 182, 12, INK)
    # shallow arch + hangers under each half so it reads as a bridge
    for xa, xb in ((cx - 205, cx - 33), (cx + 33, cx + 205)):
        pts = []
        for i in range(11):
            t = i / 10.0
            pts.append((int(xa + t * (xb - xa)),
                        int(deck_y + 12 + 26 * math.sin(math.pi * t))))
        for i in range(len(pts) - 1):
            c.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                   GREY, 5)
        for j in range(1, 5):
            hx = int(xa + (xb - xa) * j / 5.0)
            hy = int(deck_y + 12 + 26 * math.sin(math.pi * j / 5.0))
            c.line(hx, deck_y + 12, hx, hy, GREY, 2)
    # piers down to the water
    c.fill_rect(cx - 210, deck_y + 12, 16, 66, INK)
    c.fill_rect(cx + 194, deck_y + 12, 16, 66, INK)
    # crack marks at the broken deck ends
    c.line(cx - 28, deck_y, cx - 20, deck_y + 12, INK, 3)
    c.line(cx + 28, deck_y, cx + 20, deck_y + 12, INK, 3)
    # fallen span, tilted, in the water, with a splash
    c.fill_polygon([(cx - 58, cy + 58), (cx + 46, cy + 40),
                    (cx + 56, cy + 54), (cx - 48, cy + 72)], INK)
    c.line(cx - 30, cy + 40, cx - 44, cy + 24, BLUE, 3)
    c.line(cx + 10, cy + 34, cx + 2, cy + 18, BLUE, 3)
    c.line(cx + 44, cy + 38, cx + 56, cy + 22, BLUE, 3)
    c.fill_circle(cx - 68, cy + 50, 4, INK)
    c.fill_circle(cx + 70, cy + 62, 4, INK)
    wave(c, cx - 210, cx + 210, cy + 82, 5, BLUE, 3)
    wave(c, cx - 210, cx + 210, cy + 94, 5, SKY, 3)


def icon_skyline(c, cx, cy):
    """Skyscrapers with a flag (APEC leaders gather in Shenzhen)."""
    base = cy + 92
    towers = [(-200, 118, NAVY), (-122, 158, BLUE), (-44, 96, GREY),
              (34, 142, NAVY), (112, 108, BLUE)]
    for dx, h, color in towers:
        x0 = cx + dx
        c.fill_rect(x0, base - h, 70, h, color)
        for wy in range(base - h + 14, base - 12, 22):
            for wx in (x0 + 12, x0 + 32, x0 + 52):
                c.fill_rect(wx, wy, 8, 10, GOLD)
    # flag on the tallest tower
    c.line(cx - 87, base - 158, cx - 87, base - 192, INK, 3)
    c.fill_polygon([(cx - 87, base - 192), (cx - 55, base - 184),
                    (cx - 87, base - 176)], RED)


def icon_virus(c, cx, cy):
    """Spiky virus with a small medical cross (measles)."""
    for i in range(12):
        a = 2 * math.pi * i / 12
        x1 = int(cx + 52 * math.cos(a))
        y1 = int(cy + 52 * math.sin(a))
        x2 = int(cx + 80 * math.cos(a))
        y2 = int(cy + 80 * math.sin(a))
        c.line(x1, y1, x2, y2, CRIMSON, 6)
        c.fill_circle(x2, y2, 8, CRIMSON)
    c.fill_circle(cx, cy, 54, CRIMSON)
    c.fill_circle(cx - 20, cy - 14, 9, (226, 120, 125))
    c.fill_circle(cx + 18, cy + 8, 9, (226, 120, 125))
    c.fill_circle(cx + 2, cy - 26, 7, (226, 120, 125))
    # small medical cross badge
    bx, by = cx + 148, cy + 58
    c.fill_circle(bx, by, 26, WHITE)
    c.circle(bx, by, 26, RED, 3)
    c.fill_rect(bx - 5, by - 14, 10, 28, RED)
    c.fill_rect(bx - 14, by - 5, 28, 10, RED)


# ---- the four stories of 17 November 2026 (verified 19 Nov 2026) ----
# 1. US strikes Iran: Reuters, 17 Nov 2026 (US warplanes hit a missile
#    launch site on Qeshm Island after Iranian attacks on US forces).
# 2. Kerch Bridge: Reuters/AP, 17 Nov 2026 (Ukraine drops a road span;
#    Russia hits Kyiv's Northern and Southern bridges).
# 3. APEC Shenzhen: 17 Nov 2026 (CEO Summit opens; Trump, Xi and Putin
#    due to meet on Thursday 19 Nov; China confirmed the trilateral).
# 4. Measles: PAHO/Reuters/NPR, 17 Nov 2026 (US loses measles elimination
#    status after 26 years; 5,412 cases in 2026 as of 12 Nov).

STORIES = [
    {"icon": icon_strike,
     "head": ("US STRIKES", "IRAN"),
     "deck": ("US WARPLANES HIT A MISSILE", "SITE AFTER IRAN HIT US FORCES"),
     "sub": "QESHM ISLAND - HORMUZ"},
    {"icon": icon_bridge,
     "head": ("KERCH BRIDGE", "STRUCK"),
     "deck": ("UKRAINE DROPS A ROAD SPAN", "RUSSIA HITS TWO KYIV BRIDGES"),
     "sub": "CRIMEA - KYIV BRIDGES HIT"},
    {"icon": icon_skyline,
     "head": ("APEC OPENS IN", "SHENZHEN"),
     "deck": ("TRUMP, XI AND PUTIN DUE", "TO MEET ON THURSDAY"),
     "sub": "CHINA - TRUMP, XI, PUTIN"},
    {"icon": icon_virus,
     "head": ("MEASLES STATUS", "LOST"),
     "deck": ("PAHO: VIRUS SPREAD FOR OVER", "A YEAR - 5,400 CASES IN 2026"),
     "sub": "USA - AFTER 26 YEARS"},
]


def draw_panel(c, px, py, story):
    w, h = 480, 404
    c.fill_rect(px, py, w, h, WHITE)
    c.fill_rect(px, py, w, 3, INK)
    c.fill_rect(px, py + h - 3, w, 3, INK)
    c.fill_rect(px, py, 3, h, INK)
    c.fill_rect(px + w - 3, py, 3, h, INK)
    cx = px + w // 2
    story["icon"](c, cx, py + 100)
    c.text_centered(cx, py + 202, story["head"][0], 5, INK)
    c.text_centered(cx, py + 244, story["head"][1], 5, INK)
    c.fill_rect(px + 24, py + 292, w - 48, 2, GREY)
    c.text_centered(cx, py + 306, story["deck"][0], 2, INK)
    c.text_centered(cx, py + 326, story["deck"][1], 2, INK)
    c.text_centered(cx, py + 358, story["sub"], 2, RED)


def compose():
    c = Canvas(W, H, PAPER)
    # masthead: the day, named large
    c.text_centered(W // 2, 38, "TUESDAY - THE DAY IN WORLD NEWS", 2, GREY)
    c.text_centered(W // 2, 64, "17 NOVEMBER 2026", 9, INK)
    c.fill_rect(24, 140, 976, 4, INK)
    c.fill_rect(24, 148, 976, 3, RED)
    # 2x2 front page
    for i, story in enumerate(STORIES):
        px = 24 + (i % 2) * (480 + 16)
        py = 168 + (i // 2) * (404 + 16)
        draw_panel(c, px, py, story)
    return c


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    png = encode_png(compose())
    with open(os.path.join(outdir, "entry.png"), "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main()
