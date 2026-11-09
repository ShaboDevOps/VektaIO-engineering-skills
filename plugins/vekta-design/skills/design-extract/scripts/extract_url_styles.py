#!/usr/bin/env python3
"""Measure a live web page's design system from its computed styles (not guesses).

Opens the page in headless Chromium at one or more viewport widths, walks every visible element and
collects the values the browser actually renders: colours (weighted by area / text length), font
families, type scale, weights, line heights, letter spacing, radii, shadows, borders, spacing
(padding / margin / gap), container widths, transitions, CSS custom properties, @font-face sources,
plus samples of components (buttons, inputs, cards, chips, nav, header, footer) with screenshots.

Usage:
  python3 extract_url_styles.py <url-or-file> [--out design-source/web] [--widths 390,1280]
                                [--wait 1500] [--max-elements 6000]
Requires: pip install playwright && python -m playwright install chromium   (if not already present)

Outputs in --out:
  report.json   full frequency tables + component samples
  report.md     human-readable summary (top values, suggested scales)
  page-<w>.png  full-page screenshots;  components/<kind>-<n>-<w>.png  element crops
Only use on designs you own, are licensed to use, or have permission to replicate.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

COLLECT_JS = r"""
(maxEls) => {
  const out = { elements: [], vars: {}, fontFaces: [], fontsLoaded: [], components: [] };
  // CSS custom properties from same-origin stylesheets
  for (const sheet of Array.from(document.styleSheets)) {
    let rules; try { rules = sheet.cssRules; } catch (e) { continue; }
    const walk = (list) => { for (const r of Array.from(list || [])) {
      if (r.cssRules && !r.style) walk(r.cssRules);
      if (r.style) for (let i = 0; i < r.style.length; i++) {
        const p = r.style[i]; if (p.startsWith("--")) out.vars[p] = (out.vars[p] || []).concat([[r.selectorText || "", r.style.getPropertyValue(p).trim()]]).slice(0, 6);
      }
      if (r.constructor && r.constructor.name === "CSSFontFaceRule") out.fontFaces.push(r.cssText.slice(0, 400));
    }};
    walk(rules);
  }
  try { document.fonts.forEach(f => { if (f.status === "loaded") out.fontsLoaded.push(f.family + " " + f.weight + " " + f.style); }); } catch (e) {}

  const vis = (el, r, cs) => r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none" && parseFloat(cs.opacity) > 0.05;
  const all = Array.from(document.querySelectorAll("body *")).slice(0, maxEls);
  for (const el of all) {
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    if (!vis(el, r, cs)) continue;
    const ownText = Array.from(el.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(" ").trim();
    out.elements.push({
      tag: el.tagName.toLowerCase(), role: el.getAttribute("role") || "", cls: (el.className && el.className.baseVal === undefined ? String(el.className) : "").slice(0, 80),
      area: Math.round(r.width * r.height), w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.left), y: Math.round(r.top + window.scrollY),
      textLen: ownText.length,
      color: cs.color, bg: cs.backgroundColor, bgImage: cs.backgroundImage !== "none" ? cs.backgroundImage.slice(0, 160) : "",
      borderColor: cs.borderTopColor, borderWidth: cs.borderTopWidth, borderStyle: cs.borderTopStyle,
      font: cs.fontFamily, size: cs.fontSize, weight: cs.fontWeight, lh: cs.lineHeight, ls: cs.letterSpacing, tt: cs.textTransform,
      radius: cs.borderTopLeftRadius, shadow: cs.boxShadow,
      pt: cs.paddingTop, pr: cs.paddingRight, pb: cs.paddingBottom, pl: cs.paddingLeft,
      mt: cs.marginTop, mb: cs.marginBottom, gap: cs.rowGap === "normal" ? "" : cs.rowGap, colGap: cs.columnGap === "normal" ? "" : cs.columnGap,
      display: cs.display, maxW: cs.maxWidth, transition: cs.transitionDuration + "|" + cs.transitionTimingFunction + "|" + cs.transitionProperty,
      cursor: cs.cursor,
    });
  }
  return out;
}
"""

COMPONENT_SELECTORS = {
    "button": "button, [role=button], a[class*=btn], a[class*=button], input[type=submit]",
    "input": "input:not([type=hidden]):not([type=submit]):not([type=checkbox]):not([type=radio]), textarea, select",
    "nav": "nav, [role=navigation]",
    "header": "header, [role=banner]",
    "footer": "footer, [role=contentinfo]",
    "link": "main a, article a, p a",
    "heading": "h1, h2, h3",
    "chip": "[class*=badge], [class*=chip], [class*=tag], [class*=pill]",
    "card": "[class*=card], article",
}


def parse_rgba(s: str) -> tuple[int, int, int, float] | None:
    m = re.match(r"rgba?\(([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)(?:[,/ ]+([\d.]+%?))?\)", s or "")
    if not m:
        return None
    a = m.group(4)
    alpha = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
    return int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3))), alpha


def hexa(c: tuple[int, int, int, float]) -> str:
    r, g, b, a = c
    return "#%02X%02X%02X" % (r, g, b) + ("" if a >= 0.999 else "%02X" % round(a * 255))


def px(v: str) -> float | None:
    m = re.match(r"^(-?[\d.]+)px$", (v or "").strip())
    return float(m.group(1)) if m else None


def lum(c: tuple[int, int, int, float]) -> float:
    def ch(v: int) -> float:
        x = v / 255
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def contrast(a, b) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def top(counter: Counter, n: int = 12) -> list[list]:
    total = sum(counter.values()) or 1
    return [[k, round(100 * v / total, 1)] for k, v in counter.most_common(n)]


def guess_base_unit(values: list[float]) -> dict:
    """Share of spacing values that are multiples of each candidate base unit. Prefer 4 or 8 on near-ties."""
    vals = [v for v in values if 2 <= v <= 96]
    scores = {b: round(sum(1 for v in vals if abs(v / b - round(v / b)) < 0.01) / (len(vals) or 1), 2) for b in (4, 8, 5, 6)}
    best = max(scores, key=lambda b: (scores[b] + (0.08 if b in (4, 8) else 0), b == 8 and scores[8] >= scores[4] - 0.02))
    return {"guess": best, "scores": scores}


def analyse(elements: list[dict]) -> dict:
    bg, text, border = Counter(), Counter(), Counter()
    fonts, sizes, weights, lhs, ls = Counter(), Counter(), Counter(), Counter(), Counter()
    radii, shadows, spacing, transitions, maxw = Counter(), Counter(), Counter(), Counter(), Counter()
    size_font = defaultdict(Counter)
    pairs = Counter()
    for e in elements:
        b = parse_rgba(e["bg"])
        if b and b[3] > 0.02:
            bg[hexa(b)] += max(1, e["area"])
        t = parse_rgba(e["color"])
        if t and e["textLen"]:
            text[hexa(t)] += e["textLen"]
            fonts[e["font"].split(",")[0].strip().strip('"').strip("'")] += e["textLen"]
            sizes[e["size"]] += e["textLen"]
            weights[e["weight"]] += e["textLen"]
            lhs[f'{e["size"]}/{e["lh"]}'] += e["textLen"]
            if e["ls"] not in ("normal", "0px"):
                ls[f'{e["size"]}:{e["ls"]}'] += e["textLen"]
            size_font[e["size"]][e["font"].split(",")[0].strip().strip('"')] += e["textLen"]
            if b and b[3] > 0.9:
                pairs[(hexa(t), hexa(b))] += e["textLen"]
        if e["borderStyle"] not in ("none", "") and (px(e["borderWidth"]) or 0) > 0:
            bc = parse_rgba(e["borderColor"])
            if bc:
                border[f'{e["borderWidth"]} {hexa(bc)}'] += 1
        if e["radius"] not in ("0px", ""):
            radii[e["radius"]] += 1
        if e["shadow"] != "none":
            shadows[e["shadow"]] += 1
        for k in ("pt", "pr", "pb", "pl", "mt", "mb", "gap", "colGap"):
            v = px(e.get(k, ""))
            if v and v > 0:
                spacing[v] += 1
        dur, ease, prop = (e["transition"].split("|") + ["", "", ""])[:3]
        if dur not in ("0s", ""):
            uniq = lambda v: ", ".join(dict.fromkeys(x.strip() for x in re.split(r",(?![^()]*\))", v)))
            transitions[f"{uniq(dur)} {uniq(ease)} ({prop[:40]})"] += 1
        if e["maxW"] not in ("none", "") and e["w"] > 600:
            maxw[e["maxW"]] += 1
    sizes_sorted = sorted({px(s) for s in sizes if px(s)}, key=float)
    pair_report = []
    for (fg, bgc), n in pairs.most_common(15):
        c = contrast(parse_rgba(_rgba_from_hex(fg)), parse_rgba(_rgba_from_hex(bgc)))
        pair_report.append({"fg": fg, "bg": bgc, "weight": n, "contrast": round(c, 2)})
    return {
        "colors": {"backgrounds": top(bg, 14), "text": top(text, 12), "borders": top(border, 10)},
        "typography": {"families": top(fonts, 6), "sizes": top(sizes, 14), "sizeScalePx": sizes_sorted,
                       "weights": top(weights, 8), "lineHeights": top(lhs, 14), "letterSpacing": top(ls, 8),
                       "familyBySize": {k: v.most_common(2) for k, v in size_font.items()}},
        "radius": top(radii, 10), "shadows": top(shadows, 8),
        "spacing": {"valuesPx": top(spacing, 20), "baseUnitGuess": guess_base_unit(list(spacing.elements()))},
        "containers": top(maxw, 6), "motion": top(transitions, 10), "textOnBackground": pair_report,
    }


def _rgba_from_hex(h: str) -> str:
    h = h.lstrip("#")
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1
    return f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, {a})"


def to_md(url: str, results: dict) -> str:
    L = [f"# Design measurements — {url}", "", "Values the browser actually renders. % = share by area (backgrounds) or by text length (text).", ""]
    for width, r in results.items():
        a = r["analysis"]
        L += [f"## Viewport {width}px", "", "### Colours", "| Backgrounds | % | Text | % |", "|---|---|---|---|"]
        rows = max(len(a["colors"]["backgrounds"]), len(a["colors"]["text"]))
        for i in range(min(rows, 12)):
            b = a["colors"]["backgrounds"][i] if i < len(a["colors"]["backgrounds"]) else ["", ""]
            t = a["colors"]["text"][i] if i < len(a["colors"]["text"]) else ["", ""]
            L.append(f"| {b[0]} | {b[1]} | {t[0]} | {t[1]} |")
        L += ["", "Borders: " + ", ".join(f"{k} ({v}%)" for k, v in a["colors"]["borders"][:6]), "",
              "### Text on background (contrast)", "| Text | Background | Contrast |", "|---|---|---|"]
        L += [f"| {p['fg']} | {p['bg']} | {p['contrast']}:1 |" for p in a["textOnBackground"][:10]]
        ty = a["typography"]
        L += ["", "### Typography", "Families: " + ", ".join(f"{k} ({v}%)" for k, v in ty["families"]),
              "Size scale (px): " + ", ".join(f"{s:g}" for s in ty["sizeScalePx"]),
              "Weights: " + ", ".join(f"{k} ({v}%)" for k, v in ty["weights"]),
              "Line heights (size/lh): " + ", ".join(k for k, _ in ty["lineHeights"][:10]),
              "Letter spacing: " + (", ".join(k for k, _ in ty["letterSpacing"]) or "normal"), "",
              "### Shape, depth, spacing, motion",
              "Radius: " + ", ".join(f"{k} ({v}%)" for k, v in a["radius"]),
              "Shadows: " + "; ".join(f"`{k}`" for k, _ in a["shadows"][:5]),
              f"Spacing base unit (guess): {a['spacing']['baseUnitGuess']['guess']}px {a['spacing']['baseUnitGuess']['scores']} · common values: " + ", ".join(f"{k:g}" for k, _ in a["spacing"]["valuesPx"][:14]),
              "Containers (max-width): " + (", ".join(k for k, _ in a["containers"]) or "—"),
              "Transitions: " + ("; ".join(k for k, _ in a["motion"][:6]) or "none found"), ""]
        L += ["### Components sampled", *[f"- {c['kind']}: {c['w']}×{c['h']} radius {c['style'].get('radius')} bg {c['style'].get('bg')} "
                                         f"color {c['style'].get('color')} font {c['style'].get('size')}/{c['style'].get('weight')} "
                                         f"padding {c['style'].get('pt')} {c['style'].get('pr')} → `{c.get('shot', '')}`" for c in r["components"]], ""]
    return "\n".join(L)


async def run(url: str, out: Path, widths: list[int], wait_ms: int, max_els: int) -> None:
    from playwright.async_api import async_playwright
    out.mkdir(parents=True, exist_ok=True)
    (out / "components").mkdir(exist_ok=True)
    if not re.match(r"^[a-z]+://", url):
        url = Path(url).resolve().as_uri()
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for w in widths:
            page = await browser.new_page(viewport={"width": w, "height": 900}, device_scale_factor=1)
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(wait_ms)
            await page.evaluate("async () => { for (let y = 0; y < document.body.scrollHeight; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); } window.scrollTo(0, 0); }")
            await page.screenshot(path=str(out / f"page-{w}.png"), full_page=True)
            data = await page.evaluate(COLLECT_JS, max_els)
            comps = []
            for kind, sel in COMPONENT_SELECTORS.items():
                handles = await page.query_selector_all(sel)
                n = 0
                for h in handles:
                    if n >= 3:
                        break
                    box = await h.bounding_box()
                    if not box or box["width"] < 8 or box["height"] < 8:
                        continue
                    style = await h.evaluate("""el => { const cs = getComputedStyle(el); return {
                        bg: cs.backgroundColor, color: cs.color, size: cs.fontSize, weight: cs.fontWeight, font: cs.fontFamily,
                        radius: cs.borderRadius, border: cs.border, shadow: cs.boxShadow, pt: cs.paddingTop, pr: cs.paddingRight,
                        pb: cs.paddingBottom, pl: cs.paddingLeft, height: cs.height, gap: cs.gap, transition: cs.transition,
                        text: (el.innerText || el.value || "").trim().slice(0, 40) }; }""")
                    shot = f"components/{kind}-{n + 1}-{w}.png"
                    try:
                        await h.screenshot(path=str(out / shot))
                    except Exception:
                        shot = ""
                    comps.append({"kind": kind, "w": round(box["width"]), "h": round(box["height"]), "style": style, "shot": shot})
                    n += 1
            results[w] = {"analysis": analyse(data["elements"]), "components": comps, "cssVariables": data["vars"],
                          "fontFaces": data["fontFaces"][:20], "fontsLoaded": sorted(set(data["fontsLoaded"]))[:20],
                          "elementCount": len(data["elements"])}
            await page.close()
        await browser.close()
    (out / "report.json").write_text(json.dumps({"url": url, "viewports": results}, indent=2), encoding="utf-8")
    (out / "report.md").write_text(to_md(url, results), encoding="utf-8")
    print(f"✓ measured {url} at {widths} → {out}/report.md, report.json, screenshots")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--out", default="design-source/web")
    ap.add_argument("--widths", default="390,1280")
    ap.add_argument("--wait", type=int, default=1500)
    ap.add_argument("--max-elements", type=int, default=6000)
    a = ap.parse_args()
    asyncio.run(run(a.url, Path(a.out), [int(x) for x in a.widths.split(",")], a.wait, a.max_elements))


if __name__ == "__main__":
    main()
