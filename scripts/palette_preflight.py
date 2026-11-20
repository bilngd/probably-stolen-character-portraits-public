# -*- coding: utf-8 -*-
"""Palette preflight for portrait conversion.

Checks whether a character palette has a sclera (eye-white) slot that is far
enough from the lightest hair colour. If not, optionally writes a B+ palette
with the least-used slot replaced by a dedicated sclera colour.

Usage:
  python palette_preflight.py --palette female_aqua.json --src raw_aqua_matte.png
  python palette_preflight.py --palette female_aqua.json --src raw_aqua_matte.png \
      --out aqua_Bplus_palette.json

Only Pillow is required.
"""
import argparse
import json
import math
from collections import Counter

from PIL import Image

SCLERA = (170, 210, 222)
SCLERA_L_MIN = 195
SCLERA_CHROMA_MAX = 40
DELTA_E_MIN = 25


def luminance(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def chroma(c):
    return max(c) - min(c)


def is_skin(c):
    r, g, b = c
    return (r >= 165 and g >= 105 and b >= 75 and r > g + 3 and g > b + 3
            and r - b >= 25 and not (r > 205 and g < 95))


def srgb_to_lab(c):
    def inv(v):
        v = v / 255.0
        return ((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92
    r, g, b = inv(c[0]), inv(c[1]), inv(c[2])
    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505
    x, y, z = x / 0.95047, y / 1.00000, z / 1.08883

    def f(t):
        return t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0
    fx, fy, fz = f(x), f(y), f(z)
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def delta_e(c1, c2):
    l1, a1, b1 = srgb_to_lab(c1)
    l2, a2, b2 = srgb_to_lab(c2)
    return math.sqrt((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)


def build_palette_image(palette):
    pal = Image.new("P", (1, 1))
    flat = []
    for c in palette:
        flat.extend(c)
    if len(flat) < 768:
        flat += list(palette[-1]) * ((768 - len(flat)) // 3)
    pal.putpalette(flat)
    return pal


def palette_counts(im, palette):
    pim = im.convert("RGB").quantize(palette=build_palette_image(palette),
                                     dither=Image.Dither.NONE)
    idx = pim.tobytes()
    alpha = im.getchannel("A").tobytes()
    cnt = Counter()
    for i, a in zip(idx, alpha):
        if a >= 128:
            cnt[i] += 1
    return cnt


def hair_candidate(im, palette, bbox):
    top_h = max(1, int((bbox[3] - bbox[1]) * 0.20))
    top = im.crop((bbox[0], bbox[1], bbox[2], bbox[1] + top_h))
    cnt = palette_counts(top, palette)
    total = sum(cnt.values()) or 1
    cands = []
    for i, c in enumerate(palette):
        n = cnt.get(i, 0)
        if n < 2 or chroma(c) <= 35 or luminance(c) <= 110 or is_skin(c):
            continue
        cands.append((i, n, c, luminance(c), chroma(c)))
    if not cands:
        for i, c in enumerate(palette):
            if chroma(c) > 35 and not is_skin(c):
                cands.append((i, cnt.get(i, 0), c, luminance(c), chroma(c)))
    if not cands:
        return None
    # lightest hair shade with a non-trivial presence; tie -> more common
    return max(cands, key=lambda t: (t[3], t[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--palette", required=True)
    ap.add_argument("--src", help="matte raw; needed for hair detection and B+")
    ap.add_argument("--out", help="write B+ palette JSON here if preflight fails")
    ap.add_argument("--slot", type=int, help="force this palette index as the sclera slot")
    ap.add_argument("--sclera", default="170,210,222")
    args = ap.parse_args()

    palette = [[int(v) for v in c] for c in json.load(open(args.palette, encoding="utf-8"))]
    sclera_rgb = tuple(int(v) for v in args.sclera.split(","))
    report = {"palette": args.palette, "colors": len(palette), "sclera": list(sclera_rgb)}

    sclera_cands = [c for c in palette
                    if luminance(c) >= SCLERA_L_MIN and chroma(c) <= SCLERA_CHROMA_MAX]
    report["sclera_candidates"] = sclera_cands

    hair = None
    if args.src:
        im = Image.open(args.src).convert("RGBA")
        bb = im.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()
        if bb:
            hair = hair_candidate(im, palette, bb)
    if hair:
        report["hair"] = {"index": hair[0], "rgb": hair[2],
                          "luminance": round(hair[3], 1), "chroma": hair[4],
                          "count": hair[1]}
    else:
        report["hair"] = None

    if sclera_cands and hair:
        de = [delta_e(s, hair[2]) for s in sclera_cands]
        report["min_delta_e"] = round(min(de), 1)
        report["delta_e_list"] = [round(v, 1) for v in de]
        missing = min(de) < DELTA_E_MIN
    elif not sclera_cands:
        report["min_delta_e"] = None
        missing = True
    else:
        report["min_delta_e"] = None
        missing = None
    report["missing"] = missing

    if missing and args.src:
        src = Image.open(args.src).convert("RGBA")
        full_cnt = palette_counts(src, palette)
        total = sum(full_cnt.values()) or 1
        # never consider the dark structural slots (outline / near-black)
        cands = [i for i in range(len(palette)) if luminance(palette[i]) >= 60]
        cands.sort(key=lambda i: full_cnt.get(i, 0))
        report["slot_candidates"] = [
            {"index": i, "rgb": palette[i], "usage": full_cnt.get(i, 0),
             "usage_ratio": round(full_cnt.get(i, 0) / total, 4),
             "luminance": round(luminance(palette[i]), 1),
             "chroma": chroma(palette[i])}
            for i in cands[:5]
        ]
        if args.slot is None:
            report["hint"] = "choose --slot from slot_candidates; do not blind-replace a hair highlight"
        elif args.out:
            least = args.slot
            usage = full_cnt.get(least, 0)
            report["replaced"] = {"index": least, "rgb": palette[least],
                                  "usage": usage,
                                  "usage_ratio": round(usage / total, 4)}
            if usage / total > 0.005:
                report["warning"] = "chosen slot still >0.5%; check before replacing"
            palette[least] = list(sclera_rgb)
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(palette, f, ensure_ascii=False, indent=1)
            report["out"] = args.out

    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
