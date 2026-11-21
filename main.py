#!/usr/bin/env python3
"""Entry for the make.fun bounty "The Passport Page of a Country
That Isn't There" (the-passport-page-of-a-countr-2-20261121-0318).

A program that draws one invented passport spread to /output/entry.png:
the open passport of the Republic of Virelia, a country that isn't
there. Left page: navy cover page with the Virelian emblem, motto and
visa stamps. Right page: the cream data page of one Elara Voss Marlowe,
with a drawn portrait, her details, a gold seal and an MRZ.

Python 3.13, Pillow only (stdlib + PIL). No network at runtime.
Deterministic: every run writes the same bytes.
"""

import hashlib
import math
import os
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

# --- canvas -------------------------------------------------------------
W = H = 1024
MAX_BYTES = 1_048_576

# --- palette ------------------------------------------------------------
DESK = (11, 31, 51)
DESK_TOP = (18, 48, 72)
GOLD = (201, 162, 39)
GOLD_LT = (232, 203, 106)
GOLD_DK = (146, 112, 22)
CREAM = (245, 238, 221)
CREAM_D = (228, 218, 192)
INK = (24, 42, 66)
INK_SOFT = (74, 92, 110)
TEAL = (16, 104, 104)
TEAL_LT = (64, 158, 158)
STAMP_RED = (172, 62, 46)
STAMP_TEAL = (22, 112, 104)

# --- fonts --------------------------------------------------------------
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
SERIF = os.path.join(FONT_DIR, "DejaVuSerif.ttf")
SERIF_B = os.path.join(FONT_DIR, "DejaVuSerif-Bold.ttf")
SANS = os.path.join(FONT_DIR, "DejaVuSans.ttf")
SANS_B = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
MONO = os.path.join(FONT_DIR, "DejaVuSansMono.ttf")
MONO_B = os.path.join(FONT_DIR, "DejaVuSansMono-Bold.ttf")


def font(path, size):
    return ImageFont.truetype(path, size)


# sha256 of the exact bytes written to /output/entry.png.
# Measured after the first run; then re-verified (see NOTES.md).
EXPECTED_SHA256 = "dcc0f7e7f52e06a0d8e3a503d69d751675ac9dbd32b3a4b9b0e71438014610de"

# The invented country, its bearer and its document.
COUNTRY = "REPUBLIC OF VIRELIA"
MOTTO = "LUX EX MARI"
DOC_NO = "VR-2026-0042"
MRZ1 = "P<VRLMARLOWE<<ELARA<VOSS<<<<<<<<<<<<<<<<<<<<"
MRZ2 = "VR202600424VRL9803147F3611212<<<<<<<<<<<<<08"


# --- small drawing helpers ----------------------------------------------
def vgrad(draw, box, top, bottom):
    """Vertical gradient fill inside box (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    steps = max(1, y1 - y0)
    for i in range(steps):
        t = i / steps
        c = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
        draw.line([(x0, y0 + i), (x1, y0 + i)], fill=c)


def spaced(draw, xy, text, fnt, fill, tracking=0):
    """Draw text with extra tracking between characters."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x


def spaced_w(draw, text, fnt, tracking=0):
    """Width of text drawn with tracking."""
    w = 0.0
    for ch in text:
        w += draw.textlength(ch, font=fnt) + tracking
    return w - tracking if text else 0


def centered(draw, cx, y, text, fnt, fill, tracking=0):
    w = spaced_w(draw, text, fnt, tracking)
    spaced(draw, (cx - w / 2, y), text, fnt, fill, tracking)
    return w


def ring(draw, cx, cy, r, fill, width=2):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=fill, width=width)


def star8(draw, cx, cy, r_out, r_in, fill):
    """Eight-pointed compass star."""
    pts = []
    for i in range(16):
        ang = math.pi / 2 + i * math.pi / 8
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(ang), cy - r * math.sin(ang)))
    draw.polygon(pts, fill=fill)


def arc_waves(draw, cx, cy, r, fill, width=2):
    """Three concentric wave arcs, like a guilloche."""
    for k, rr in enumerate((r, r - 14, r - 28)):
        draw.arc([cx - rr, cy - rr, cx + rr, cy + rr],
                 start=200, end=340, fill=fill, width=width)


def make_stamp(lines, radius, color, angle):
    """A round visa stamp on its own layer, rotated."""
    size = radius * 2 + 16
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = size // 2
    ring(d, c, c, radius, color + (235,), 3)
    ring(d, c, c, radius - 8, color + (235,), 2)
    f_top = font(SANS_B, 15)
    f_mid = font(SANS_B, 13)
    f_bot = font(SANS, 13)
    fonts = (f_top, f_mid, f_bot)
    y = c - 30
    for i, line in enumerate(lines):
        w = d.textlength(line, font=fonts[i])
        d.text((c - w / 2, y), line, font=fonts[i], fill=color + (235,))
        y += 22 if i == 0 else 24
    return layer.rotate(angle, resample=Image.BICUBIC, expand=False)


def draw_emblem(draw, cx, cy, r):
    """Compass rose with a lighthouse at its heart, in gold."""
    ring(draw, cx, cy, r, GOLD, 3)
    ring(draw, cx, cy, r - 9, GOLD, 1)
    star8(draw, cx, cy, r - 16, r - 52, GOLD)
    # lighthouse tower in dark navy, silhouetted on the gold star
    tower = [(cx - 13, cy + 34), (cx - 8, cy - 26),
             (cx + 8, cy - 26), (cx + 13, cy + 34)]
    draw.polygon(tower, fill=DESK)
    draw.rectangle([cx - 11, cy - 34, cx + 11, cy - 26], fill=DESK)
    draw.ellipse([cx - 7, cy - 44, cx + 7, cy - 30], fill=GOLD_LT)
    # light beams
    draw.polygon([(cx - 6, cy - 37), (cx - 44, cy - 48),
                  (cx - 44, cy - 26)], fill=GOLD_LT)
    draw.polygon([(cx + 6, cy - 37), (cx + 44, cy - 48),
                  (cx + 44, cy - 26)], fill=GOLD_LT)
    # waves under the tower
    for k, yy in enumerate((cy + 42, cy + 52)):
        draw.arc([cx - 40, yy - 10, cx + 40, yy + 10],
                 start=200, end=340, fill=GOLD, width=2)


def draw_left_page(img, box):
    """Navy cover page: emblem, name, motto, map, stamps."""
    x0, y0, x1, y1 = box
    page = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    d = ImageDraw.Draw(page)
    vgrad(d, (0, 0, x1 - x0, y1 - y0), DESK_TOP, DESK)
    # guilloche arcs, faint, bottom corners
    faint = GOLD + (38,)
    layer = Image.new("RGBA", page.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for rr in range(60, 420, 26):
        ld.arc([30 - rr, y1 - y0 - 60 - rr, 30 + rr, y1 - y0 - 60 + rr],
               start=270, end=360, fill=faint, width=1)
        ld.arc([x1 - x0 - 30 - rr, y1 - y0 - 60 - rr,
                x1 - x0 - 30 + rr, y1 - y0 - 60 + rr],
               start=180, end=270, fill=faint, width=1)
    page = Image.alpha_composite(page, layer)
    d = ImageDraw.Draw(page)
    # gold double border
    d.rectangle([14, 14, x1 - x0 - 15, y1 - y0 - 15],
                outline=GOLD, width=3)
    d.rectangle([22, 22, x1 - x0 - 23, y1 - y0 - 23],
                outline=GOLD, width=1)
    cx = (x1 - x0) // 2
    # emblem
    draw_emblem(d, cx, 168, 92)
    # country name
    centered(d, cx, 292, "REPUBLIC OF", font(SERIF_B, 30),
             GOLD_LT, tracking=4)
    centered(d, cx, 330, "VIRELIA", font(SERIF_B, 44),
             GOLD_LT, tracking=10)
    d.line([(cx - 110, 392), (cx + 110, 392)], fill=GOLD, width=2)
    centered(d, cx, 406, "P A S S P O R T", font(SERIF_B, 26),
             GOLD, tracking=2)
    centered(d, cx, 448, "LUX EX MARI  ·  EST. 1847",
             font(SANS, 14), GOLD_LT, tracking=2)
    # archipelago map
    my = 478
    centered(d, cx, my, "THE VIRELIAN ARCHIPELAGO",
             font(SANS, 12), GOLD_LT, tracking=2)
    islands = [
        [(cx - 118, my + 62), (cx - 96, my + 34), (cx - 66, my + 44),
         (cx - 78, my + 70), (cx - 104, my + 76)],
        [(cx - 30, my + 78), (cx - 8, my + 44), (cx + 22, my + 52),
         (cx + 30, my + 82), (cx - 2, my + 92)],
        [(cx + 62, my + 40), (cx + 84, my + 26), (cx + 108, my + 40),
         (cx + 96, my + 62), (cx + 72, my + 60)],
    ]
    for isl in islands:
        d.polygon(isl, outline=GOLD, width=2)
    for px, py in ((cx - 92, my + 54), (cx + 2, my + 66),
                   (cx + 86, my + 44)):
        d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=GOLD_LT)
    centered(d, cx, my + 108, "54°17′N  11°02′W — THREE ISLANDS, ONE SEA",
             font(SANS, 11), GOLD_LT, tracking=1)
    # visa stamps
    stamp1 = make_stamp(["ARRIVAL", "PORT MERIDIAN", "21 NOV 2026"],
                        70, STAMP_RED, -14)
    stamp2 = make_stamp(["ADMITTED", "AURORA GATE", "12 MAR 2026"],
                        64, STAMP_TEAL, 11)
    page.paste(stamp1, (28, 606), stamp1)
    page.paste(stamp2, (x1 - x0 - 28 - stamp2.width, 626), stamp2)
    img.paste(page, (x0, y0), page)


def draw_portrait(d, box):
    """Drawn portrait: dusk sea, sun, and a profile silhouette."""
    x0, y0, x1, y1 = box
    vgrad(d, box, (22, 78, 96), (10, 38, 62))
    # sun, top right
    d.ellipse([x0 + 96, y0 + 18, x0 + 128, y0 + 50], fill=GOLD_LT)
    # waves, low at the bottom only
    for k, yy in enumerate((y1 - 34, y1 - 20)):
        d.arc([x0 - 30, yy - 14, x1 + 30, yy + 14],
              start=200, end=340, fill=TEAL_LT, width=3)
    # profile silhouette: head + shoulders, facing left
    d.ellipse([x0 + 48, y0 + 64, x0 + 96, y0 + 112], fill=INK)
    d.polygon([(x0 + 34, y1), (x0 + 48, y1 - 48), (x0 + 62, y1 - 62),
               (x0 + 96, y1 - 62), (x0 + 110, y1 - 42), (x0 + 114, y1)],
              fill=INK)
    # gold frame
    d.rectangle(box, outline=GOLD, width=3)


def draw_seal(d, cx, cy, r):
    """Gold rosette seal with a star."""
    for k in range(24):
        ang = k * math.pi / 12
        x1 = cx + (r - 6) * math.cos(ang)
        y1 = cy + (r - 6) * math.sin(ang)
        x2 = cx + r * math.cos(ang)
        y2 = cy + r * math.sin(ang)
        d.line([(x1, y1), (x2, y2)], fill=GOLD, width=2)
    d.ellipse([cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8],
              outline=GOLD, width=2)
    star8(d, cx, cy, r - 16, r - 30, GOLD)
    d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=GOLD)


def field(d, x, y, label, value, vsize=17, width=230):
    """One labelled data field."""
    d.text((x, y), label, font=font(SANS, 11), fill=INK_SOFT)
    d.text((x, y + 15), value, font=font(SANS_B, vsize), fill=INK)


def draw_right_page(img, box):
    """Cream data page: photo, bearer details, seal, MRZ."""
    x0, y0, x1, y1 = box
    w = x1 - x0
    page = Image.new("RGBA", (w, y1 - y0), (0, 0, 0, 0))
    d = ImageDraw.Draw(page)
    d.rectangle([0, 0, w - 1, y1 - y0 - 1], fill=CREAM)
    d.rectangle([14, 14, w - 15, y1 - y0 - 15], outline=INK, width=2)
    d.rectangle([22, 22, w - 23, y1 - y0 - 23], outline=INK, width=1)
    cx = w // 2
    centered(d, cx, 44, "REPUBLIC OF VIRELIA", font(SERIF_B, 27), INK)
    centered(d, cx, 80, "PASSPORT  —  PASSEPORT", font(SANS, 13),
             INK_SOFT, tracking=3)
    d.line([(40, 112), (w - 40, 112)], fill=GOLD, width=2)
    # portrait
    draw_portrait(d, (48, 132, 192, 322))
    d.text((48, 330), "PHOTOGRAPH", font=font(SANS, 10), fill=INK_SOFT)
    # fields beside the portrait
    fx = 214
    field(d, fx, 132, "TYPE / TYPE", "P")
    field(d, fx + 76, 132, "CODE / CODE", "VRL")
    field(d, fx, 186, "PASSPORT No.", DOC_NO, vsize=15)
    field(d, fx, 240, "SURNAME / NOM", "MARLOWE")
    field(d, fx, 294, "GIVEN NAMES / PRÉNOMS", "ELARA VOSS")
    field(d, fx, 348, "NATIONALITY / NATIONALITÉ", "VIRELIAN")
    # lower fields
    field(d, 48, 396, "DATE OF BIRTH", "14 MAR 1998")
    field(d, 214, 396, "PLACE OF BIRTH", "PORT MERIDIAN")
    field(d, 48, 450, "SEX / SEXE", "F")
    field(d, 214, 450, "DATE OF ISSUE", "21 NOV 2026")
    field(d, 48, 504, "DATE OF EXPIRY", "21 NOV 2036")
    field(d, 214, 504, "AUTHORITY / AUTORITÉ", "MINISTRY OF THE SEA",
          vsize=14)
    # holder's signature
    d.text((48, 558), "HOLDER'S SIGNATURE", font=font(SANS, 11),
           fill=INK_SOFT)
    sig = [(48, 592), (66, 576), (82, 594), (98, 570), (114, 588),
           (130, 574), (146, 592), (162, 580), (180, 594)]
    d.line(sig, fill=INK, width=2, joint="curve")
    d.line([(48, 604), (200, 604)], fill=INK_SOFT, width=1)
    # gold seal
    draw_seal(d, 330, 580, 36)
    d.text((296, 622), "OFFICIAL SEAL", font=font(SANS, 9),
           fill=INK_SOFT)
    # MRZ
    d.line([(40, 652), (w - 40, 652)], fill=INK_SOFT, width=1)
    f_mrz = font(MONO, 13)
    d.text((40, 668), MRZ1, font=f_mrz, fill=INK)
    d.text((40, 690), MRZ2, font=f_mrz, fill=INK)
    img.paste(page, (x0, y0), page)


# --- composition --------------------------------------------------------
def draw_spread():
    img = Image.new("RGB", (W, H), DESK)
    d = ImageDraw.Draw(img)
    vgrad(d, (0, 0, W, H), DESK_TOP, DESK)
    # faint desk guilloche
    for rr in range(80, 700, 34):
        d.arc([-rr, H - rr, rr, H + rr], start=270, end=360,
              fill=(201, 162, 39, 26), width=1)
    # top caption: the bounty title, small and gold
    centered(d, W // 2, 52,
             "THE PASSPORT PAGE OF A COUNTRY THAT ISN'T THERE",
             font(SANS_B, 17), GOLD_LT, tracking=3)
    # book shadow + pages
    d.rectangle([52, 128, 976, 884], fill=(4, 14, 24))
    draw_left_page(img, (56, 120, 496, 880))
    draw_right_page(img, (528, 120, 968, 880))
    # spine shadow
    spine = Image.new("RGBA", (36, 760), (0, 0, 0, 0))
    sd = ImageDraw.Draw(spine)
    for i in range(36):
        a = 90 - abs(i - 18) * 5
        sd.line([(i, 0), (i, 760)], fill=(0, 0, 0, max(0, a)))
    img.paste(spine, (494, 120), spine)
    # footer caption
    centered(d, W // 2, 924, "REPUBLIC OF VIRELIA  ·  PASSPORT Nº VR-2026-0042",
             font(SANS, 15), GOLD_LT, tracking=2)
    return img


# --- entry / self-test ---------------------------------------------------
def resolve_out_dir():
    return os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")


def write_entry(out_dir):
    img = draw_spread()
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    img.save(path, format="PNG", optimize=True)
    return path


def verify_written(path):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) > MAX_BYTES:
        raise ValueError(f"entry.png is {len(data)} bytes, over 1 MiB")
    img = Image.open(path)
    if img.size != (1024, 1024):
        raise ValueError(f"entry.png is {img.size}, must be 1024x1024")
    if img.format != "PNG":
        raise ValueError(f"entry.png format is {img.format}, must be PNG")
    digest = hashlib.sha256(data).hexdigest()
    if EXPECTED_SHA256 != "0" * 64 and digest != EXPECTED_SHA256:
        raise ValueError(f"sha256 mismatch: got {digest}")
    return digest, len(data)


def run_once(out_dir):
    path = write_entry(out_dir)
    digest, size = verify_written(path)
    print(f"wrote {path}: 1024x1024 PNG, {size} bytes")
    print(f"sha256: {digest}")
    return digest


def self_test():
    digests = []
    for _ in range(2):
        with tempfile.TemporaryDirectory() as tmp:
            digests.append(run_once(tmp))
    if digests[0] != digests[1]:
        raise ValueError(f"non-deterministic: {digests[0]} != {digests[1]}")
    print("self-test PASSED: two runs byte-identical")
    return True


def main(argv):
    if "--self-test" in argv:
        self_test()
        return 0
    try:
        run_once(resolve_out_dir())
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
