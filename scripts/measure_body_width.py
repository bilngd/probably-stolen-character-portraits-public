# -*- coding: utf-8 -*-
"""粗测 4× 立绘的“肩线宽”（宽发角色不计外侧发丝的口径）。

用法:
    python measure_body_width.py <png> [--band 0.50-0.85] [--step 0.05]

输出:
    - 人物总 bbox / aspect（含所有发丝）
    - 人物 bbox 高度每一档的：y、中央连续段宽（含中轴的最大连通段）、全 span、
      左右各自“外侧发丝”占的像素

怎么读:
    肩线宽取肩头 / 上臂外缘那一行的“中央连续段宽”。
    外侧发丝 = 全 span 减去中央段（左右分叉、和身体之间有透明缝的头发）。
    典型肩线在下巴下方一点（人物 bbox 高度约 60–75% 处）；各角色构图不同，以 6× 预览为准。

依赖: numpy, pillow。
"""
import argparse

import numpy as np
from PIL import Image


def row_runs(row):
    idx = np.where(row)[0]
    if idx.size == 0:
        return []
    out = []
    start = prev = int(idx[0])
    for i in idx[1:]:
        i = int(i)
        if i == prev + 1:
            prev = i
        else:
            out.append((start, prev))
            start = prev = i
    out.append((start, prev))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png")
    ap.add_argument("--band", default="0.50-0.85", help="相对人物 bbox 高度的扫描区间")
    ap.add_argument("--step", type=float, default=0.05)
    ap.add_argument("--alpha", type=int, default=10)
    args = ap.parse_args()

    im = Image.open(args.png).convert("RGBA")
    a = np.asarray(im)
    mask = a[:, :, 3] > args.alpha
    ys, xs = np.where(mask)
    if len(xs) == 0:
        raise SystemExit("no opaque pixels")
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    w, h = x1 - x0 + 1, y1 - y0 + 1
    cx = (x0 + x1) // 2

    lo, hi = [float(v) for v in args.band.split("-")]
    frac = lo
    print(f"{args.png}")
    print(f"figure = {w}x{h}  aspect = {w / h:.3f}  center_x = {(x0 + x1) / 2:.1f}")
    print(" frac    y   central  span   left_hair right_hair")
    while frac <= hi + 1e-9:
        y = min(int(y0 + frac * h), y1)
        rr = row_runs(mask[y])
        if not rr:
            print(f" {frac:.2f}  {y:4d}       -     -        -         -")
        else:
            cr = [r for r in rr if r[0] <= cx <= r[1]]
            if cr:
                c0, c1 = cr[0]
                cw = c1 - c0 + 1
                lh = c0 - rr[0][0]
                rh = rr[-1][1] - c1
            else:
                cw = lh = rh = 0
            span = rr[-1][1] - rr[0][0] + 1
            print(f" {frac:.2f}  {y:4d}   {cw:5d}  {span:4d}   {lh:8d}  {rh:8d}")
        frac += args.step

    print("\n肩线宽取肩头 / 上臂外缘那一行的 central；外侧发丝不计入体型表。")
    print("记录到 ref/<角色>_gen.log：body_width=<肩线宽>；figure 仍记总 bbox。")


if __name__ == "__main__":
    main()
