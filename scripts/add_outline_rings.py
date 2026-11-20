"""给立绘补 N 圈外描边（4× / 2× 用）。

convert_character.py 的 --outline-mode thin 只补 1px。高分辨率画布需要更粗的视觉等价描边：
  - 2× 画布：thin + 1 圈 = 2px
  - 4× 画布：thin + 1 圈 = 2px（推荐，visual ≈ 1.4 屏幕像素 @1080p）
  - 4× 画布：thin + 3 圈 = 4px（实测偏厚，用户否过，别默认用）

用法：
  python add_outline_rings.py <src.png> <dst.png> <rings> [--color 41,34,52]
"""

import argparse
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("rings", type=int)
    ap.add_argument("--color", default="41,34,52")
    args = ap.parse_args()

    out = tuple(int(v) for v in args.color.split(","))
    im = Image.open(args.src).convert("RGBA")
    px = im.load()
    w, h = im.size

    for _ in range(args.rings):
        add = []
        for y in range(h):
            for x in range(w):
                if px[x, y][3] != 0:
                    continue
                hit = False
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        xx, yy = x + dx, y + dy
                        if 0 <= xx < w and 0 <= yy < h and px[xx, yy][3] != 0:
                            hit = True
                            break
                    if hit:
                        break
                if hit:
                    add.append((x, y))
        for x, y in add:
            px[x, y] = (out[0], out[1], out[2], 255)

    im.save(args.dst)
    bb = im.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()
    print(
        args.dst,
        "bbox", bb,
        "figure", (bb[2] - bb[0], bb[3] - bb[1]),
        "center", (bb[0] + bb[2]) / 2,
        "gap", h - bb[3],
    )


if __name__ == "__main__":
    main()
