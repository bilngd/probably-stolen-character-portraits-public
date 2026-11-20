# -*- coding: utf-8 -*-
"""量 4× 立绘的头部占比：用来判断“头是不是真的太大”，避免凭观感重生成。

口径（2026-11-20 定）：
    canvas_ratio = (chin_y - head_top_y) / 画布高度(844)
    figure_ratio = (chin_y - head_top_y) / 人物 bbox 高度

chin_y 取「肤色连续段里的脖子最窄处」：有颈饰/高领的角色正好落在领口，
露颈角色（如示例角色）肤色会一路连到胸口，用最窄处而不是肤色段末尾，
不然脖子和胸口会被算进头。

现有 4× 女角实测参考（同一脚本）：
    正常成年角色  canvas 约 37–44% / figure 约 46–58%
    DeepSeek 示例 canvas 43.2% / figure 57.0%
→ 画布口径 36–45% 都属店内常态；**不要**拿 SKILL 的 38–40% 去卡人物 bbox。

仅作粗测：脸被刘海切断、露颈连到胸口、头饰盖住额头的角色会失准，
必须肉眼确认下巴；可用 --chin 直接指定下巴 y。

用法：
    python measure_head.py <png> [<png> ...]
    python measure_head.py --chin 573 <png>
"""
import argparse
from PIL import Image


def is_skin(p):
    return (
        p[3] > 0
        and p[0] > 195
        and 140 < p[1] < 238
        and 105 < p[2] < 228
        and p[0] - p[2] > 8
    )


def skin_widths(im, x0, x1, y0, y1):
    px = im.load()
    widths = []
    for y in range(y0, y1):
        n = 0
        for x in range(x0, x1):
            if is_skin(px[x, y]):
                n += 1
        widths.append(n)
    return widths


def skin_runs(im, x0, x1, y0, y1):
    widths = skin_widths(im, x0, x1, y0, y1)
    min_px = max(3, (x1 - x0) // 12)
    out = []
    start = None
    for i, w in enumerate(widths):
        y = y0 + i
        if w > min_px and start is None:
            start = y
        if w <= min_px and start is not None:
            out.append((start, y - 1))
            start = None
    if start is not None:
        out.append((start, y1))
    return [(a, b) for a, b in out if b - a >= 8]


def measure(path, band=45, verbose=False, chin_override=None):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    bb = im.getbbox()
    top, bottom = bb[1], bb[3]
    cx = (bb[0] + bb[2]) // 2
    x0, x1 = max(0, cx - band), min(w, cx + band)
    runs = skin_runs(im, x0, x1, top, bottom)
    if chin_override:
        chin = chin_override
    elif not runs:
        print(f"{path}: 未找到肤色行，需要人工看下巴（--chin）")
        return None
    else:
        # 取“最靠上的一段较长肤色”：脸被刘海/眼睛切断时，脖子+胸口那段会更长，
        # 按长度取会选错；按高度取才落在脸上。
        long_runs = [r for r in runs if r[1] - r[0] >= 25] or runs
        face = min(long_runs, key=lambda r: r[0])
        widths = skin_widths(im, x0, x1, face[0], face[1] + 1)
        max_w = max(widths)
        face_idx = widths.index(max_w)
        tail = widths[face_idx:]
        min_w = min(tail)
        neck_idx = face_idx + tail.index(min_w)
        # 脖子比脸窄明显才算找到；否则退回肤色段末尾
        chin = face[0] + neck_idx if min_w < max_w * 0.55 else face[1]
        if verbose:
            print(f"  skin runs: {runs}")
            print(f"  widths: {widths}")

    head_h = chin - top
    canvas_ratio = head_h / h
    figure_ratio = head_h / (bottom - top)
    print(
        f"{path}\n"
        f"  head_top={top} chin/neck={chin} figure={bb[2]-bb[0]}x{bottom-top}\n"
        f"  canvas_ratio={canvas_ratio:.1%}  figure_ratio={figure_ratio:.1%}\n"
        f"  ※ 粗测：脸被刘海切断/露颈的角色会失准，必须肉眼确认下巴"
    )
    return canvas_ratio, figure_ratio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--band", type=int, default=45, help="以人物中心为轴的取样半宽")
    ap.add_argument("--chin", type=int, default=None, help="手动指定下巴 y（脚本失准时用）")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    for p in args.images:
        measure(p, args.band, args.verbose, args.chin)


if __name__ == "__main__":
    main()
