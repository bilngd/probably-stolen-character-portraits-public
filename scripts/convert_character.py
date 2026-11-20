# -*- coding: utf-8 -*-
"""通用：把生成的插画转成《深空当铺》顾客立绘规格。

用法:
    python convert_character.py --src raw.png --out out.png --key femaleUpperExample \
        --palette palettes/female.json --squeeze 1.0 --height 604 --canvas 1152x844 --outline-mode thin

`--key` 只写进 report 的 `sprite_key` 方便核对，**不决定输出文件名、也不决定 sprite key**；
落位文件名自己按 `<key>4x.png` 起，并在代码里注册同名 key。

规格来源：原版 maleUpper/femaleUpper 立绘 288x211、PPU100、pivot(0.5,0.5)、
alpha 只有 0/255、统一 1px 描边 #292234、人物底部贴边水平居中。
height 按人设选，thin 后 bbox 高 = height + 2。
"""
import argparse
import json
import os
from collections import Counter

from PIL import Image, ImageFilter


def build_palette_image(palette):
    pal = Image.new("P", (1, 1))
    flat = []
    for c in palette:
        flat.extend(c)
    # 不要用 0 补齐：量化器会把纯黑当成第 N+1 个可用色，
    # 输出 distinct_colors 会比色板多 1（实测 24 色板 → 25 色）。
    if len(flat) < 768:
        last = list(palette[-1])
        flat += last * ((768 - len(flat)) // 3)
    pal.putpalette(flat)
    return pal


def clean_alpha(alpha, min_keep=4, min_fill=7):
    w, h = alpha.size
    src = alpha.load()
    out = Image.new("L", (w, h), 0)
    dst = out.load()
    for y in range(h):
        for x in range(w):
            n = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < w and 0 <= yy < h and src[xx, yy] > 0:
                        n += 1
            v = src[x, y]
            dst[x, y] = 255 if (v > 0 and n >= min_keep) or (v == 0 and n >= min_fill) else 0
    return out


def erode_alpha(alpha, steps=1):
    """把 alpha 边缘向内收 steps 像素，用来削掉抠图残留的白边/灰边。"""
    for _ in range(steps):
        w, h = alpha.size
        src = alpha.load()
        out = Image.new("L", (w, h), 0)
        dst = out.load()
        for y in range(h):
            for x in range(w):
                if src[x, y] == 0:
                    continue
                keep = True
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        xx, yy = x + dx, y + dy
                        if 0 <= xx < w and 0 <= yy < h and src[xx, yy] == 0:
                            keep = False
                            break
                    if not keep:
                        break
                dst[x, y] = 255 if keep else 0
        alpha = out
    return alpha


def despeckle(rgba, strength=5):
    """去掉孤立色点：自身颜色在 8 邻域出现 <=1 次、邻域有 >=strength 个同色时替换。"""
    w, h = rgba.size
    src = rgba.load()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dst = out.load()
    for y in range(h):
        for x in range(w):
            p = src[x, y]
            if p[3] == 0:
                dst[x, y] = (0, 0, 0, 0)
                continue
            neigh = []
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < w and 0 <= yy < h and src[xx, yy][3] > 0:
                        neigh.append(src[xx, yy][:3])
            if not neigh:
                dst[x, y] = p
                continue
            mode, cnt = Counter(neigh).most_common(1)[0]
            same = sum(1 for c in neigh if c == p[:3])
            dst[x, y] = (*mode, 255) if (same <= 1 and cnt >= strength) else p
    return out


def add_outline(rgba, outline, mode="thin"):
    """描边。none=不加（保留原图自带的 AA 边）；thin=仅外侧 1px；thick=外侧补一圈 + 主体最外圈压色（约 2px）。"""
    if mode == "none":
        return rgba
    w, h = rgba.size
    alpha = rgba.getchannel("A").point(lambda v: 255 if v > 0 else 0)
    mask = Image.new("L", (w + 2, h + 2), 0)
    mask.paste(alpha, (1, 1))
    mp = mask.load()
    big = Image.new("RGBA", (w + 2, h + 2), (0, 0, 0, 0))
    big.paste(rgba, (1, 1), rgba)
    bp = big.load()
    VW, VH = w + 2, h + 2
    for y in range(VH):
        for x in range(VW):
            if mp[x, y] > 0:
                continue
            hit = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < VW and 0 <= yy < VH and mp[xx, yy] > 0:
                        hit = True
                        break
                if hit:
                    break
            if hit:
                bp[x, y] = (*outline, 255)
    if mode == "thick":
        for y in range(1, h + 1):
            for x in range(1, w + 1):
                if mp[x, y] == 0:
                    continue
                near = False
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if mp[x + dx, y + dy] == 0:
                            near = True
                            break
                    if near:
                        break
                if near:
                    bp[x, y] = (*outline, 255)
    return big


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--key", default="character")
    ap.add_argument("--palette", required=True)
    ap.add_argument("--squeeze", type=float, default=1.0)
    ap.add_argument("--height", type=int, default=160)
    ap.add_argument("--canvas", default="288x211")
    ap.add_argument("--alpha-th", type=int, default=110)
    ap.add_argument("--outline", default="41,34,52")
    ap.add_argument("--outline-mode", default="thin", choices=["none", "thin", "thick"],
                    help="none=不加描边；thin=仅外侧 1px；thick=外侧 + 内侧约 2px")
    ap.add_argument("--edge-erode", type=int, default=0,
                    help="转换前 alpha 边缘向内收的像素数，削掉抠图白边")
    ap.add_argument("--resample", default="LANCZOS", choices=["BOX", "LANCZOS", "BICUBIC", "NEAREST"])
    ap.add_argument("--despeckle", type=int, default=5, help="0 关闭")
    ap.add_argument("--median", type=int, default=0, help="量化前 RGB 中值滤波，3/5 削细碎阴影，0 关闭")
    ap.add_argument("--preview-bg", default="28,30,36")
    args = ap.parse_args()

    CW, CH = [int(v) for v in args.canvas.lower().split("x")]
    OUTLINE = tuple(int(v) for v in args.outline.split(","))
    PBG = tuple(int(v) for v in args.preview_bg.split(","))
    palette = json.load(open(args.palette, encoding="utf-8"))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    im = Image.open(args.src).convert("RGBA")
    a = im.getchannel("A").point(lambda v: 255 if v > 10 else 0)
    bbox = a.getbbox()
    crop = im.crop(bbox)
    cw, ch = crop.size

    th = args.height
    tw = max(1, round(cw * th / ch * args.squeeze))
    rs = {"BOX": Image.BOX, "LANCZOS": Image.LANCZOS, "BICUBIC": Image.BICUBIC, "NEAREST": Image.NEAREST}[args.resample]
    small = crop.resize((tw, th), rs)
    alpha = clean_alpha(small.getchannel("A").point(lambda v: 255 if v >= args.alpha_th else 0))
    if args.edge_erode:
        alpha = erode_alpha(alpha, args.edge_erode)

    rgb_src = small.convert("RGB")
    if args.median:
        rgb_src = rgb_src.filter(ImageFilter.MedianFilter(args.median))
    rgb = rgb_src.quantize(palette=build_palette_image(palette),
                           dither=Image.Dither.NONE).convert("RGB")
    rgba = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    rgba.paste(rgb, (0, 0), alpha)
    if args.despeckle:
        rgba = despeckle(rgba, args.despeckle)

    big = add_outline(rgba, OUTLINE, args.outline_mode)
    bw, bh = big.size
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    canvas.paste(big, ((CW - bw) // 2, CH - bh), big)
    canvas.save(args.out)

    # 预览 + 规格
    bg = Image.new("RGBA", canvas.size, (*PBG, 255))
    bg.alpha_composite(canvas)
    prev_path = os.path.splitext(args.out)[0] + "_preview6x.png"
    bg.resize((CW * 6, CH * 6), Image.NEAREST).save(prev_path)

    data = list(canvas.getdata())
    alphas = Counter(p[3] for p in data)
    cols = Counter(p[:3] for p in data if p[3] > 0)
    bb = canvas.getbbox()
    scale = max(1, round(CH / 211))
    sprite_filter = "Bilinear" if scale >= 2 else "Point"
    report = {
        "file": os.path.basename(args.out),
        "sprite_key": args.key,
        "canvas": list(canvas.size),
        "alpha_values": sorted(alphas.keys()),
        "distinct_colors": len(cols),
        "bbox": list(bb),
        "figure": [bb[2] - bb[0], bb[3] - bb[1]],
        "center_x": (bb[0] + bb[2]) / 2,
        "bottom_gap": CH - bb[3],
        "sprite": {
            "ppu": 100 * scale,
            "pivot": [0.5, 0.5],
            "filter": sprite_filter,
            "wrap": "Clamp",
            "mipmap": False,
            "note": "loader 默认 PPU100/Point；4x 由 MOD 代码 Rebuild 时设 Bilinear、mipmap 关。--key 仅记录，不决定文件名 / sprite key。",
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=1))
    print("preview:", prev_path)


if __name__ == "__main__":
    main()
