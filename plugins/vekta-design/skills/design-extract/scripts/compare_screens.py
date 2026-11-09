#!/usr/bin/env python3
"""Fidelity check: compare a screenshot of the implementation with the source design.

Aligns both images to the same width, then reports the share of pixels that differ noticeably and writes
a side-by-side + heat-map image so you can see exactly where spacing, colour or type drifted.

Usage:
  python3 compare_screens.py <source.png> <implementation.png> [--out design-source/compare/home]
                             [--threshold 24] [--crop x,y,w,h]
Tips: capture the implementation at the same viewport width and device scale as the source; hide dynamic
content (dates, avatars) or crop to a stable region. < 3% different pixels is usually visually identical;
investigate any clustered red areas regardless of the total.
Requires: Pillow
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageOps


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("implementation")
    ap.add_argument("--out", default="design-source/compare/result")
    ap.add_argument("--threshold", type=int, default=24, help="per-pixel difference (0-255) counted as different")
    ap.add_argument("--crop", default="", help="x,y,w,h region (in source pixels) to compare")
    a = ap.parse_args()

    src = Image.open(a.source).convert("RGB")
    imp = Image.open(a.implementation).convert("RGB")
    if imp.width != src.width:
        imp = imp.resize((src.width, round(imp.height * src.width / imp.width)), Image.Resampling.LANCZOS)
    h = min(src.height, imp.height)
    src, imp = src.crop((0, 0, src.width, h)), imp.crop((0, 0, imp.width, h))
    if a.crop:
        x, y, w, hh = (int(v) for v in a.crop.split(","))
        src, imp = src.crop((x, y, x + w, y + hh)), imp.crop((x, y, x + w, y + hh))

    diff = ImageChops.difference(src, imp).convert("L")
    mask = diff.point(lambda v: 255 if v > a.threshold else 0)
    changed = mask.histogram()[255]
    pct = 100 * changed / (mask.width * mask.height)

    heat = Image.composite(Image.new("RGB", src.size, (230, 30, 30)), ImageOps.grayscale(imp).convert("RGB"), mask)
    side = Image.new("RGB", (src.width * 3 + 20, src.height), "white")
    side.paste(src, (0, 0))
    side.paste(imp, (src.width + 10, 0))
    side.paste(heat, (src.width * 2 + 20, 0))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    side.save(f"{out}-side-by-side.png")
    verdict = "visually identical" if pct < 3 else "close — check red areas" if pct < 10 else "noticeable differences"
    print(f"{pct:.2f}% of pixels differ (threshold {a.threshold}) → {verdict}. Saved {out}-side-by-side.png "
          "(source | implementation | differences in red)")


if __name__ == "__main__":
    main()
