# -*- coding: utf-8 -*-
"""导出《深空当铺 / Probably Stolen》原版顾客立绘的原始像素。

用法:
    python extract_portraits.py --out ref --base maleUpper femaleUpper
    python extract_portraits.py --out ref --base maleUpper femaleUpper maleLower scavMale

依赖: UnityPy, Pillow（pip install UnityPy pillow）。
输出: <out>/<base>_<i>_full.png（原始 288x211 画布）
      <out>/<base>_<i>_trim.png（裁掉透明边的人物本体）
"""
import argparse
import os
import re
import sys

import UnityPy
from PIL import Image

GAME_ROOT = os.environ.get("PS_GAME_DIR")
DEFAULT_GAME = os.path.join(GAME_ROOT, "Probably Stolen_Data") if GAME_ROOT else r"C:/Path/To/Probably Stolen/Probably Stolen_Data"
DEFAULT_FILES = ["sharedassets1.assets", "sharedassets0.assets", "resources.assets"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", nargs="+", required=True)
    ap.add_argument("--game", default=DEFAULT_GAME)
    ap.add_argument("--assets", nargs="*", default=DEFAULT_FILES)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    wanted = set(args.base)
    found = {}

    for fn in args.assets:
        path = os.path.join(args.game, fn)
        if not os.path.exists(path):
            continue
        env = UnityPy.load(path)
        for obj in env.objects:
            if obj.type.name != "Sprite":
                continue
            try:
                d = obj.read()
                name = d.m_Name
            except Exception:
                continue
            m = re.match(r"^(.*?)_(\d+)$", name)
            if not m or m.group(1) not in wanted:
                continue
            base, idx = m.group(1), int(m.group(2))
            try:
                img = d.image.convert("RGBA")
            except Exception as e:
                print(f"  !! {name}: {e}")
                continue
            # 同帧可能在多个 assets 里重复，保留首次
            found.setdefault((base, idx), (img, fn))

    for base in args.base:
        frames = sorted(((k[1], v) for k, v in found.items() if k[0] == base), key=lambda x: x[0])
        if not frames:
            print(f"{base}: 未找到（检查名字是否带 _N 后缀）")
            continue
        print(f"\n{base}: {len(frames)} frames  src={frames[0][1][1]}")
        for idx, (img, _fn) in frames:
            full = os.path.join(args.out, f"{base}_{idx}_full.png")
            img.save(full)
            bbox = img.getbbox()
            if bbox:
                crop = img.crop(bbox)
                crop.save(os.path.join(args.out, f"{base}_{idx}_trim.png"))
                print(f"  {base}_{idx:<3d} canvas={img.width}x{img.height} bbox={bbox} trim={crop.width}x{crop.height}")
            else:
                print(f"  {base}_{idx:<3d} 空帧")


if __name__ == "__main__":
    sys.exit(main())
