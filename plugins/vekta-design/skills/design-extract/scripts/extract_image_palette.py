#!/usr/bin/env python3
"""Measure colours from design images (screenshots, mockups, exported Figma frames, PDF pages).

For each image: dominant palette with coverage %, a split into neutrals vs accents, WCAG contrast between
the main colours, and exact pixel colours at points or regions you name (e.g. a button, a heading).

Usage:
  python3 extract_image_palette.py <image> [<image> ...] [--colors 14] [--out design-source/images]
         [--point name:x,y ...] [--region name:x,y,w,h ...]
  PDF pages: convert first, e.g.  pdftoppm -png -r 110 design.pdf design-source/pdf/page
Requires: Pillow (pip install pillow)

Palette hexes are exact pixel values (most frequent shade of each colour group); gradients/photos give
approximate groups — use --point/--region on flat areas for exact values.
Notes: screenshots are usually at 2x or 3x — divide measured pixel sizes by the device scale factor.
Anti-aliasing blends edges: sample the middle of shapes and text strokes, not their borders.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image


def lum(rgb: tuple[int, int, int]) -> float:
    def ch(v: int) -> float:
        x = v / 255
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2])


def contrast(a, b) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def hexs(rgb) -> str:
    return "#%02X%02X%02X" % tuple(rgb[:3])


def saturation(rgb) -> float:
    mx, mn = max(rgb) / 255, min(rgb) / 255
    if mx == 0:
        return 0.0
    return (mx - mn) / mx


def dist(a, b) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def palette(img: Image.Image, n: int) -> list[dict]:
    """Exact colours: count real pixel values (nearest-neighbour downscale keeps them unblended), then group
    near-identical shades from anti-aliasing under the most frequent exact value of each group."""
    rgb_img = img.convert("RGB")
    scale = min(1.0, 700 / max(rgb_img.size))
    if scale < 1:
        rgb_img = rgb_img.resize((max(1, int(rgb_img.width * scale)), max(1, int(rgb_img.height * scale))), Image.Resampling.NEAREST)
    counts = sorted(rgb_img.getcolors(rgb_img.width * rgb_img.height) or [], reverse=True)
    total = sum(c for c, _ in counts) or 1
    groups: list[dict] = []
    for count, rgb in counts:
        for g in groups:
            if dist(g["rgb"], rgb) < 18:
                g["count"] += count
                break
        else:
            if len(groups) < 400:
                groups.append({"rgb": rgb, "count": count})
    groups.sort(key=lambda m: -m["count"])
    out = []
    for m in groups[:n]:
        rgb = m["rgb"]
        out.append({"hex": hexs(rgb), "coverage": round(100 * m["count"] / total, 1),
                    "kind": "accent" if saturation(rgb) > 0.28 and 0.08 < lum(rgb) < 0.9 else "neutral",
                    "luminance": round(lum(rgb), 3), "rgb": rgb})
    return out


def sample(img: Image.Image, x: int, y: int, w: int = 1, h: int = 1) -> str:
    box = img.convert("RGB").crop((x, y, x + w, y + h))
    colors = sorted(box.getcolors(w * h + 1) or [], reverse=True)
    return hexs(colors[0][1]) if colors else ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+")
    ap.add_argument("--colors", type=int, default=14)
    ap.add_argument("--out", default="design-source/images")
    ap.add_argument("--point", action="append", default=[], help="name:x,y")
    ap.add_argument("--region", action="append", default=[], help="name:x,y,w,h (most common colour in region)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    md = ["# Image colour measurements", ""]
    for path in a.images:
        img = Image.open(path)
        pal = palette(img, a.colors)
        main = pal[:6]
        matrix = [[round(contrast(p["rgb"], q["rgb"]), 2) for q in main] for p in main]
        pts = {}
        for spec in a.point:
            name, xy = spec.split(":")
            x, y = (int(v) for v in xy.split(","))
            pts[name] = sample(img, x, y)
        for spec in a.region:
            name, box = spec.split(":")
            x, y, w, h = (int(v) for v in box.split(","))
            pts[name] = sample(img, x, y, w, h)
        report[path] = {"size": img.size, "palette": [{k: v for k, v in p.items() if k != "rgb"} for p in pal],
                        "contrast": {"colors": [p["hex"] for p in main], "matrix": matrix}, "samples": pts}
        md += [f"## {Path(path).name} ({img.size[0]}×{img.size[1]})", "", "| Colour | Coverage | Kind | Luminance |", "|---|---|---|---|"]
        md += [f"| {p['hex']} | {p['coverage']}% | {p['kind']} | {p['luminance']} |" for p in pal]
        md += ["", "Contrast between main colours:", "", "| | " + " | ".join(p["hex"] for p in main) + " |",
               "|---|" + "---|" * len(main)]
        md += [f"| {main[i]['hex']} | " + " | ".join(f"{v}" for v in row) + " |" for i, row in enumerate(matrix)]
        if pts:
            md += ["", "Samples: " + ", ".join(f"{k} = {v}" for k, v in pts.items())]
        md.append("")
    (out / "palette.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "palette.md").write_text("\n".join(md), encoding="utf-8")
    print(f"✓ measured {len(a.images)} image(s) → {out}/palette.md, palette.json")


if __name__ == "__main__":
    main()
