#!/usr/bin/env python3
"""VektaIO design-token compiler (stdlib only).

Reads a project's design tokens (W3C DTCG-style JSON: leaves may be {"$value": ...} or plain values,
references like "{color.palette.brand.600}") and generates:
  - web:    Tailwind CSS v4 theme file (@theme + light/dark variables + colour themes + reduced-motion),
            theme.js/.d.ts runtime (mode, preset theme, any custom colour — persisted), React useTheme hook,
            theme-init.js (no flash of the wrong theme)
  - mobile: app_tokens.dart (palette, semantic ThemeExtension, spacing, radius, shadows, motion, typography,
            preset themes, buildAppTheme()) + app_theme.dart (Riverpod AppThemeController, appThemeProvider,
            colour engine for custom colours)
  - preview.html with a live mode/theme/custom-colour switcher
It enforces WCAG 2.2 contrast for every semantic pair, in light and dark, for every preset theme. Custom colours
picked at runtime go through the same OKLCH engine (Python here, JS + Dart generated) so they're always readable.

Usage:
  build_tokens.py <design.config.json>          generate outputs
  build_tokens.py <design.config.json> --check  fail if outputs are stale or contrast fails (CI)

design.config.json (paths relative to the config file):
  { "tokens": "tokens.json",
    "outputs": { "css": "../src/styles/tokens.css", "js": "../src/shared/theme/theme.js",
                 "react": "../src/shared/theme/useTheme.ts", "themeInit": "../public/theme-init.js",
                 "dart": "../lib/app/theme/app_tokens.dart", "preview": "preview.html" },
    "dartMaterialImport": "package:flutter/material.dart" }
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REF = re.compile(r"^\{([^{}]+)\}$")
SEMANTIC_KEYS = [
    "background", "surface", "surface-muted", "surface-raised", "foreground", "foreground-muted",
    "primary", "primary-foreground", "secondary", "secondary-foreground", "accent", "accent-foreground",
    "border", "input", "ring",
    "success", "success-foreground", "warning", "warning-foreground",
    "danger", "danger-foreground", "info", "info-foreground",
]
# (foreground, background, minimum ratio)
CONTRAST_PAIRS = [
    ("foreground", "background", 4.5), ("foreground", "surface", 4.5), ("foreground", "surface-raised", 4.5),
    ("foreground-muted", "background", 4.5), ("foreground-muted", "surface", 4.5),
    ("foreground", "surface-muted", 4.5), ("foreground-muted", "surface-muted", 4.5),
    ("primary-foreground", "primary", 4.5), ("secondary-foreground", "secondary", 4.5),
    ("accent-foreground", "accent", 4.5), ("success-foreground", "success", 4.5),
    ("warning-foreground", "warning", 4.5), ("danger-foreground", "danger", 4.5),
    ("info-foreground", "info", 4.5),
    ("primary", "background", 3.0), ("ring", "background", 3.0), ("danger", "background", 3.0),
]


class TokenError(Exception):
    pass


# ---------------------------------------------------------------- resolution
def unwrap(node: Any) -> Any:
    return node["$value"] if isinstance(node, dict) and "$value" in node else node


def lookup(root: dict, path: str) -> Any:
    node: Any = root
    for part in path.split("."):
        node = unwrap(node)
        if not isinstance(node, dict) or part not in node:
            raise TokenError(f"unknown token reference {{{path}}}")
        node = node[part]
    return node


def resolve(root: dict, value: Any, seen: tuple[str, ...] = ()) -> Any:
    value = unwrap(value)
    if isinstance(value, str):
        m = REF.match(value.strip())
        if m:
            path = m.group(1)
            if path in seen:
                raise TokenError(f"circular reference: {' -> '.join(seen + (path,))}")
            return resolve(root, lookup(root, path), seen + (path,))
        return value
    if isinstance(value, dict):
        return {k: resolve(root, v, seen) for k, v in value.items() if not k.startswith("$")}
    if isinstance(value, list):
        return [resolve(root, v, seen) for v in value]
    return value


# ---------------------------------------------------------------- colour helpers
def parse_hex(c: str) -> tuple[int, int, int, int]:
    s = c.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s) + "ff"
    elif len(s) == 6:
        s += "ff"
    elif len(s) != 8 or not re.fullmatch(r"[0-9a-fA-F]{8}", s):
        raise TokenError(f"colour must be #RGB, #RRGGBB or #RRGGBBAA, got {c!r}")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16)


def luminance(c: str) -> float:
    def ch(v: int) -> float:
        x = v / 255
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b, _ = parse_hex(c)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def dart_color(c: str) -> str:
    r, g, b, a = parse_hex(c)
    return f"Color(0x{a:02X}{r:02X}{g:02X}{b:02X})"


# ---------------------------------------------------------------- naming / units
def camel(name: str) -> str:
    name = str(name)
    m = re.match(r"^(\d+)(.*)$", name)
    if m and m.group(2):  # "2xl" -> "xl2"
        name = m.group(2) + m.group(1)
    parts = re.split(r"[-_. ]+", name)
    out = parts[0].lower() + "".join(p[:1].upper() + p[1:] for p in parts[1:])
    return out if re.match(r"^[A-Za-z_]", out) else f"v{out}"


def px(v: Any) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*(px|rem)?\s*", str(v))
    if not m:
        raise TokenError(f"expected px/rem length, got {v!r}")
    n = float(m.group(1))
    return n * 16 if m.group(2) == "rem" else n


def css_len(v: Any) -> str:
    return f"{v}px" if isinstance(v, (int, float)) else str(v)


def ms(v: Any) -> int:
    if isinstance(v, (int, float)):
        return int(v)
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(ms|s)\s*", str(v))
    if not m:
        raise TokenError(f"expected duration like '200ms', got {v!r}")
    return int(float(m.group(1)) * (1000 if m.group(2) == "s" else 1))


def num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def font_stack(v: Any) -> list[str]:
    return [s.strip() for s in (v if isinstance(v, list) else str(v).split(","))]


def css_font(v: Any) -> str:
    generic = {"serif", "sans-serif", "monospace", "system-ui", "ui-sans-serif", "ui-serif", "ui-monospace", "cursive"}
    return ", ".join(f if f in generic else f'"{f}"' for f in font_stack(v))


def shadow_list(v: Any) -> list[dict]:
    items = v if isinstance(v, list) else [v]
    out = []
    for s in items:
        if not isinstance(s, dict):
            raise TokenError(f"shadow must be an object (offsetX, offsetY, blur, spread, color), got {s!r}")
        out.append({k: s.get(k, 0) for k in ("offsetX", "offsetY", "blur", "spread")} | {"color": s["color"]})
    return out


# ---------------------------------------------------------------- colour engine (reference implementation)
# The SAME algorithm is generated in JavaScript (web runtime) and Dart (Flutter runtime) so a colour the user
# picks at runtime gets exactly the treatment preset themes get at build time. Keep the three in sync.
RAMP_LIGHTNESS = {"50": 0.971, "100": 0.936, "200": 0.880, "300": 0.805, "400": 0.715, "500": 0.625,
                  "600": 0.535, "700": 0.455, "800": 0.380, "900": 0.300, "950": 0.220}
LIGHT_ORDER = ["600", "700", "500", "800", "900", "950"]
DARK_ORDER = ["300", "400", "200", "500", "100", "50"]


def _cbrt(x: float) -> float:
    return -((-x) ** (1 / 3)) if x < 0 else x ** (1 / 3)


def _to_linear(v: float) -> float:
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _from_linear(v: float) -> float:
    return 12.92 * v if v <= 0.0031308 else 1.055 * (v ** (1 / 2.4)) - 0.055


def hex_to_oklch(c: str) -> tuple[float, float, float]:
    r, g, b, _ = parse_hex(c)
    r, g, b = _to_linear(r / 255), _to_linear(g / 255), _to_linear(b / 255)
    l_ = _cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m_ = _cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s_ = _cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    import math
    return L, math.sqrt(a * a + bb * bb), math.atan2(bb, a)


def oklch_to_rgb(L: float, C: float, h: float) -> tuple[float, float, float]:
    import math
    a, b = C * math.cos(h), C * math.sin(h)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def _in_gamut(rgb: tuple[float, float, float]) -> bool:
    return all(-1e-4 <= v <= 1 + 1e-4 for v in rgb)


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    def ch(v: float) -> int:
        return max(0, min(255, int(round(_from_linear(max(0.0, min(1.0, v))) * 255))))
    return "#%02X%02X%02X" % tuple(ch(v) for v in rgb)


def ramp_from_seed(seed: str, keys: list[str]) -> dict[str, str]:
    """Palette ramp (50…950) sharing the seed's hue, with chroma tapered toward light/dark ends."""
    _, c0, h = hex_to_oklch(seed)
    out = {}
    for k in keys:
        if k not in RAMP_LIGHTNESS:
            continue
        L = RAMP_LIGHTNESS[k]
        c = max(0.0, c0 * (1 - 0.7 * ((L - 0.62) / 0.62) ** 2))
        for _ in range(200):
            if _in_gamut(oklch_to_rgb(L, c, h)):
                break
            c *= 0.96
        out[k] = _rgb_to_hex(oklch_to_rgb(L, c, h))
    return out


def scheme_from_seed(seed: str, base: dict, keys: list[str]) -> dict | None:
    """Primary/foreground/ring for light + dark from any seed colour, guaranteeing WCAG contrast.
    Keeps the exact seed when it already works; otherwise the nearest ramp shade that does."""
    seed = "#%02X%02X%02X" % parse_hex(seed)[:3]  # normalise to #RRGGBB (alpha ignored)
    ramp = ramp_from_seed(seed, keys or list(RAMP_LIGHTNESS))
    full = ramp_from_seed(seed, list(RAMP_LIGHTNESS))
    fgs = [base["light"]["surface"], base["dark"]["background"]]

    def pick(bgs: list[str], order: list[str]) -> tuple[str, str] | None:
        for cand in [seed] + [full[k] for k in order]:
            if min(contrast(cand, bg) for bg in bgs) < 3.0:
                continue
            fg = max(fgs, key=lambda f: contrast(f, cand))
            if contrast(fg, cand) >= 4.5:
                return cand, fg
        return None

    light = pick([base["light"]["background"], base["light"]["surface"]], LIGHT_ORDER)
    dark = pick([base["dark"]["background"], base["dark"]["surface"]], DARK_ORDER)
    if not light or not dark:
        return None
    return {"palette": ramp,
            "light": {"primary": light[0], "primary-foreground": light[1], "ring": light[0]},
            "dark": {"primary": dark[0], "primary-foreground": dark[1], "ring": dark[0]}}


# ---------------------------------------------------------------- load + validate
def _label(v: Any, fallback: str) -> dict[str, str]:
    if isinstance(v, dict):
        return {"en": v.get("en", fallback), "sw": v.get("sw", v.get("en", fallback))}
    return {"en": str(v or fallback), "sw": str(v or fallback)}


def load(tokens_path: Path) -> dict:
    raw = json.loads(tokens_path.read_text(encoding="utf-8"))
    t = resolve(raw, raw)
    color = t.get("color", {})
    for mode in ("light", "dark"):
        modemap = color.get(mode)
        if not isinstance(modemap, dict):
            raise TokenError(f"color.{mode} is required")
        missing = [k for k in SEMANTIC_KEYS if k not in modemap]
        if missing:
            raise TokenError(f"color.{mode} is missing: {', '.join(missing)}")
        unknown = [k for k in modemap if k not in SEMANTIC_KEYS]
        if unknown:
            raise TokenError(f"color.{mode} has unknown keys: {', '.join(unknown)}")

    # Colour themes: the base (color.light/dark) is "default"; color.themes adds presets.
    brand = color.get("brandGroup", "brand")
    keys = list(color.get("palette", {}).get(brand, {}).keys())
    base = {"light": color["light"], "dark": color["dark"]}
    meta_default = color.get("defaultTheme", {})
    themes = [{"id": "default", "label": _label(meta_default.get("label"), "Default"),
               "swatch": color["light"]["primary"], "light": {}, "dark": {}, "palette": {}}]
    for tid, spec in color.get("themes", {}).items():
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", tid) or tid in ("default", "custom"):
            raise TokenError(f"theme id {tid!r} must be lowercase letters/digits/hyphens and not 'default'/'custom'")
        light, dark, palette = {}, {}, {}
        if "seed" in spec:
            sch = scheme_from_seed(spec["seed"], base, keys)
            if sch is None:
                raise TokenError(f"theme {tid}: no accessible primary could be derived from seed {spec['seed']}")
            light, dark, palette = dict(sch["light"]), dict(sch["dark"]), sch["palette"]
        light.update(spec.get("light", {}))
        dark.update(spec.get("dark", {}))
        for mode_map in (light, dark):
            bad = [k for k in mode_map if k not in SEMANTIC_KEYS]
            if bad:
                raise TokenError(f"theme {tid}: unknown keys {', '.join(bad)}")
        # A key overridden in one mode must be explicit in the other, so CSS cascade can't leak light values into dark.
        for k in set(light) - set(dark):
            dark[k] = base["dark"][k]
        for k in set(dark) - set(light):
            light[k] = base["light"][k]
        themes.append({"id": tid, "label": _label(spec.get("label"), tid.replace("-", " ").title()),
                       "swatch": spec.get("seed", light.get("primary", base["light"]["primary"])),
                       "light": light, "dark": dark, "palette": palette})
    t["_themes"] = themes
    t["_brand"] = brand
    t["_brand_keys"] = keys
    t["_custom"] = bool(color.get("customColor", True))
    return t


def check_contrast(t: dict) -> list[str]:
    problems = []
    for theme in t["_themes"]:
        for mode in ("light", "dark"):
            c = {**t["color"][mode], **theme[mode]}
            for fg, bg, minimum in CONTRAST_PAIRS:
                ratio = contrast(c[fg], c[bg])
                if ratio + 1e-9 < minimum:
                    where = mode if theme["id"] == "default" else f"theme {theme['id']} / {mode}"
                    problems.append(f"{where}: {fg} {c[fg]} on {bg} {c[bg]} = {ratio:.2f}:1 (needs {minimum}:1)")
    return problems


# ---------------------------------------------------------------- generators
HEADER = "GENERATED from {src} by build_tokens.py — do not edit. Change the tokens and run `just tokens`."


def gen_css(t: dict, src: str) -> str:
    L: list[str] = [f"/* {HEADER.format(src=src)} */", "", "@theme {"]
    for group, shades in t["color"].get("palette", {}).items():
        for shade, val in shades.items():
            parse_hex(val)
            L.append(f"  --color-{group}-{shade}: {val};")
    fam = t.get("font", {}).get("family", {})
    for k, v in fam.items():
        L.append(f"  --font-{k}: {css_font(v)};")
    if "body" in fam:
        L.append("  --font-sans: var(--font-body);")
    for k, v in t.get("font", {}).get("weight", {}).items():
        L.append(f"  --font-weight-{k}: {v};")
    for k, v in t.get("text", {}).items():
        L.append(f"  --text-{k}: {css_len(v['size'])};")
        if "lineHeight" in v:
            L.append(f"  --text-{k}--line-height: {css_len(v['lineHeight'])};")
        if "letterSpacing" in v:
            L.append(f"  --text-{k}--letter-spacing: {v['letterSpacing']};")
    if "base" in t.get("space", {}):
        L.append(f"  --spacing: {css_len(t['space']['base'])};")
    for k, v in t.get("radius", {}).items():
        L.append(f"  --radius-{k}: {css_len(v)};")
    for k, v in t.get("shadow", {}).items():
        parts = [f"{css_len(s['offsetX'])} {css_len(s['offsetY'])} {css_len(s['blur'])} {css_len(s['spread'])} {s['color']}"
                 for s in shadow_list(v)]
        L.append(f"  --shadow-{k}: {', '.join(parts)};")
    for k, v in t.get("motion", {}).get("easing", {}).items():
        L.append(f"  --ease-{k}: cubic-bezier({', '.join(num(x) for x in v)});")
    for k, v in t.get("motion", {}).get("duration", {}).items():
        L.append(f"  --duration-{k}: {ms(v)}ms;")
    for k, v in t.get("breakpoint", {}).items():
        L.append(f"  --breakpoint-{k}: {css_len(v)};")
    L += ["}", "", "/* Semantic colours — use these (bg-primary, text-foreground…), not palette shades, in components. */",
          "@theme inline {"]
    L += [f"  --color-{k}: var(--{k});" for k in SEMANTIC_KEYS]
    L += ["}", "", ":root {", "  color-scheme: light;"]
    L += [f"  --{k}: {t['color']['light'][k]};" for k in SEMANTIC_KEYS]
    dark = [f"  --{k}: {t['color']['dark'][k]};" for k in SEMANTIC_KEYS]
    L += ["}", "", ".dark,", '[data-theme="dark"] {', "  color-scheme: dark;", *dark, "}", "",
          "@media (prefers-color-scheme: dark) {", '  :root:not([data-theme="light"]):not(.light) {', "    color-scheme: dark;",
          *["  " + d for d in dark], "  }", "}", ""]
    themes = [th for th in t["_themes"] if th["id"] != "default"]
    if themes:
        L += ["/* Colour themes — selected at runtime with <html data-color-theme=\"id\"> (see theme.js). */"]
        brand = t["_brand"]
        for th in themes:
            light = [f"  --{k}: {v};" for k, v in th["light"].items()]
            light += [f"  --color-{brand}-{k}: {v};" for k, v in th["palette"].items()]
            dark = [f"  --{k}: {v};" for k, v in th["dark"].items()]
            sel = f'[data-color-theme="{th["id"]}"]'
            L += [f"{sel} {{", *light, "}",
                  f'.dark{sel},', f'[data-theme="dark"]{sel} {{', *dark, "}",
                  "@media (prefers-color-scheme: dark) {", f'  :root:not([data-theme="light"]):not(.light){sel} {{',
                  *["  " + d for d in dark], "  }", "}", ""]
    durations = t.get("motion", {}).get("duration", {})
    if durations:
        L += ["/* Respect users who ask for less motion. */", "@media (prefers-reduced-motion: reduce) {", "  :root {"]
        L += [f"    --duration-{k}: 0ms;" for k in durations]
        L += ["  }", "}", ""]
    return "\n".join(L)


def gen_dart(t: dict, src: str, material_import: str, runtime_import: str | None = None) -> str:
    L: list[str] = [f"// {HEADER.format(src=src)}", "// ignore_for_file: type=lint", "",
                    f"import '{material_import}';", ""]
    if runtime_import:
        L += [f"import '{runtime_import}';", ""]
    # palette
    L.append("abstract final class AppPalette {")
    for group, shades in t["color"].get("palette", {}).items():
        for shade, val in shades.items():
            suffix = str(shade) if str(shade).isdigit() else camel(shade)[:1].upper() + camel(shade)[1:]
            L.append(f"  static const {camel(group)}{suffix} = {dart_color(val)};")
    L += ["}", ""]
    # semantic colours as ThemeExtension
    fields = [camel(k) for k in SEMANTIC_KEYS]
    L += ["@immutable", "class AppColors extends ThemeExtension<AppColors> {", "  const AppColors({"]
    L += [f"    required this.{f}," for f in fields]
    L += ["  });", ""]
    L += [f"  final Color {f};" for f in fields]
    for mode in ("light", "dark"):
        L += ["", f"  static const {mode} = AppColors("]
        L += [f"    {camel(k)}: {dart_color(t['color'][mode][k])}," for k in SEMANTIC_KEYS]
        L.append("  );")
    L += ["", "  @override", "  AppColors copyWith({"]
    L += [f"    Color? {f}," for f in fields]
    L += ["  }) =>", "      AppColors("]
    L += [f"        {f}: {f} ?? this.{f}," for f in fields]
    L += ["      );", "", "  @override", "  AppColors lerp(ThemeExtension<AppColors>? other, double t) {", "    if (other is! AppColors) return this;",
          "    return AppColors("]
    L += [f"      {f}: Color.lerp({f}, other.{f}, t)!," for f in fields]
    L += ["    );", "  }", "}", ""]
    # spacing / radius
    L.append("abstract final class AppSpace {")
    for k, v in t.get("space", {}).get("scale", {}).items():
        L.append(f"  static const double {camel(k)} = {num(px(v))};")
    L += ["}", "", "abstract final class AppRadius {"]
    for k, v in t.get("radius", {}).items():
        L.append(f"  static const double {camel(k)} = {num(px(v))};")
    L += ["}", "", "abstract final class AppShadows {"]
    for k, v in t.get("shadow", {}).items():
        items = ", ".join(
            f"BoxShadow(offset: Offset({num(px(s['offsetX']))}, {num(px(s['offsetY']))}), blurRadius: {num(px(s['blur']))}, "
            f"spreadRadius: {num(px(s['spread']))}, color: {dart_color(s['color'])})" for s in shadow_list(v))
        L.append(f"  static const {camel(k)} = <BoxShadow>[{items}];")
    L += ["}", ""]
    # motion
    L.append("/// Motion tokens. Use with `MediaQuery.disableAnimationsOf(context)` → Duration.zero.")
    L.append("abstract final class AppMotion {")
    for k, v in t.get("motion", {}).get("duration", {}).items():
        L.append(f"  static const {camel(k)} = Duration(milliseconds: {ms(v)});")
    for k, v in t.get("motion", {}).get("easing", {}).items():
        L.append(f"  static const {camel(k)} = Cubic({', '.join(num(x) for x in v)});")
    L += ["}", ""]
    # typography
    fam = t.get("font", {}).get("family", {})
    L.append("abstract final class AppType {")
    for k, v in fam.items():
        L.append(f"  static const String {camel(k)} = '{font_stack(v)[0]}';")
    for k, v in t.get("text", {}).items():
        L.append(f"  static const double {camel(k)} = {num(px(v['size']))};")
    L += ["}", ""]
    text = t.get("text", {})

    def style(size_key: str, family: str, weight: str) -> str:
        if size_key not in text:
            return ""
        v = text[size_key]
        size = px(v["size"])
        height = f", height: {px(v['lineHeight']) / size:.3f}" if "lineHeight" in v else ""
        fam_arg = f"fontFamily: AppType.{camel(family)}, " if family in fam else ""
        return f"TextStyle({fam_arg}fontSize: {num(size)}{height}, fontWeight: FontWeight.w{weight})"

    roles = [  # Material role, size token, family, weight
        ("displayLarge", "5xl", "heading", "700"), ("displayMedium", "4xl", "heading", "700"),
        ("displaySmall", "3xl", "heading", "700"), ("headlineLarge", "3xl", "heading", "600"),
        ("headlineMedium", "2xl", "heading", "600"), ("headlineSmall", "xl", "heading", "600"),
        ("titleLarge", "xl", "heading", "600"), ("titleMedium", "lg", "body", "600"),
        ("titleSmall", "base", "body", "600"), ("bodyLarge", "lg", "body", "400"),
        ("bodyMedium", "base", "body", "400"), ("bodySmall", "sm", "body", "400"),
        ("labelLarge", "base", "body", "600"), ("labelMedium", "sm", "body", "600"), ("labelSmall", "xs", "body", "500"),
    ]
    density = {"compact": "VisualDensity.compact", "comfortable": "VisualDensity.comfortable",
               "standard": "VisualDensity.standard"}.get(str(t.get("density", "standard")), "VisualDensity.standard")
    # Preset colour themes (data for the runtime in app_theme.dart)
    def dart_overrides(base_name: str, over: dict) -> str:
        if not over:
            return f"AppColors.{base_name}"
        args = ", ".join(f"{camel(k)}: {dart_color(v)}" for k, v in over.items())
        return f"AppColors.{base_name}.copyWith({args})"
    L += ["/// Colour themes users can choose (Appearance settings). 'default' is the base direction.",
          "abstract final class AppThemes {",
          f"  static const bool customColorEnabled = {'true' if t['_custom'] else 'false'};",
          f"  static const List<String> paletteKeys = [{', '.join(repr(k) for k in t['_brand_keys'])}];",
          "  static final List<AppThemeOption> all = ["]
    for th in t["_themes"]:
        lab = th["label"]
        L += ["    AppThemeOption(",
              f"      id: {json.dumps(th['id'])},",
              f"      labelEn: {json.dumps(lab['en'], ensure_ascii=False)},",
              f"      labelSw: {json.dumps(lab['sw'], ensure_ascii=False)},",
              f"      swatch: {dart_color(th['swatch'])},",
              f"      light: {dart_overrides('light', th['light'])},",
              f"      dark: {dart_overrides('dark', th['dark'])},",
              "    ),"]
    L += ["  ];", "",
          "  static AppThemeOption byId(String id) => all.firstWhere((t) => t.id == id, orElse: () => all.first);",
          "}", ""]
    L += ["/// Builds ThemeData for one brightness. Pass [colors] for a preset/custom theme (see appThemeProvider).",
          "ThemeData buildAppTheme(Brightness brightness, [AppColors? colors]) {",
          "  final c = colors ?? (brightness == Brightness.dark ? AppColors.dark : AppColors.light);",
          "  final scheme = ColorScheme(",
          "    brightness: brightness,",
          "    primary: c.primary, onPrimary: c.primaryForeground,",
          "    secondary: c.secondary, onSecondary: c.secondaryForeground,",
          "    tertiary: c.accent, onTertiary: c.accentForeground,",
          "    error: c.danger, onError: c.dangerForeground,",
          "    surface: c.surface, onSurface: c.foreground, onSurfaceVariant: c.foregroundMuted,",
          "    surfaceContainerHighest: c.surfaceMuted, surfaceContainerHigh: c.surfaceRaised,",
          "    outline: c.border, outlineVariant: c.input,",
          "  );",
          "  const textTheme = TextTheme("]
    for role, size_key, family, weight in roles:
        s = style(size_key, family, weight)
        if s:
            L.append(f"    {role}: {s},")
    L += ["  );",
          "  return ThemeData(",
          "    useMaterial3: true,",
          "    brightness: brightness,",
          "    colorScheme: scheme,",
          "    scaffoldBackgroundColor: c.background,",
          *([f"    fontFamily: AppType.{camel('body')},"] if "body" in fam else []),
          "    textTheme: textTheme.apply(bodyColor: c.foreground, displayColor: c.foreground),",
          f"    visualDensity: {density},",
          "    extensions: [c],",
          "  );",
          "}",
          "",
          "extension AppThemeX on BuildContext {",
          "  AppColors get colors => Theme.of(this).extension<AppColors>()!;",
          "}",
          ""]
    return "\n".join(L)



# ---------------------------------------------------------------- web runtime (theme.js / theme.d.ts / React hook / init)
def theme_data(t: dict) -> dict:
    return {
        "storageKey": t.get("meta", {}).get("themeStorageKey", "app-theme"),
        "brandGroup": t["_brand"],
        "paletteKeys": t["_brand_keys"],
        "customColor": t["_custom"],
        "base": {m: {"background": t["color"][m]["background"], "surface": t["color"][m]["surface"]} for m in ("light", "dark")},
        "themes": [{"id": th["id"], "label": th["label"], "swatch": th["swatch"]} for th in t["_themes"]],
    }


JS_ENGINE = r"""
const STORAGE_KEY = DATA.storageKey;
const VARS_KEY = DATA.storageKey + "-vars";
const DEFAULT_PREFERENCE = Object.freeze({ mode: "system", theme: "default", customColor: null });

/** Available colour themes (ids, en/sw labels, swatch colour) for the Appearance settings UI. */
export const THEMES = DATA.themes;
/** Whether users may pick any colour as their brand colour. */
export const CUSTOM_COLOR_ENABLED = DATA.customColor;

// ---- colour engine (same algorithm as build_tokens.py and the Flutter runtime) ----
const RAMP_LIGHTNESS = { "50": 0.971, "100": 0.936, "200": 0.88, "300": 0.805, "400": 0.715, "500": 0.625,
  "600": 0.535, "700": 0.455, "800": 0.38, "900": 0.3, "950": 0.22 };
const LIGHT_ORDER = ["600", "700", "500", "800", "900", "950"];
const DARK_ORDER = ["300", "400", "200", "500", "100", "50"];

const cbrt = (x) => (x < 0 ? -Math.pow(-x, 1 / 3) : Math.pow(x, 1 / 3));
const toLinear = (v) => (v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));
const fromLinear = (v) => (v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(v, 1 / 2.4) - 0.055);

function parseHex(c) {
  let s = String(c).trim().replace(/^#/, "");
  if (s.length === 3) s = s.split("").map((ch) => ch + ch).join("");
  if (s.length === 8) s = s.slice(0, 6);
  if (!/^[0-9a-fA-F]{6}$/.test(s)) throw new Error("Invalid colour: " + c);
  return [0, 2, 4].map((i) => parseInt(s.slice(i, i + 2), 16));
}
const toHex = (rgb) => "#" + rgb.map((v) => v.toString(16).padStart(2, "0").toUpperCase()).join("");

function luminance(c) {
  const [r, g, b] = parseHex(c).map((v) => toLinear(v / 255));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
/** WCAG contrast ratio between two colours. */
export function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

function hexToOklch(c) {
  const [r, g, b] = parseHex(c).map((v) => toLinear(v / 255));
  const l = cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  const L = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
  const A = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s;
  const B = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s;
  return [L, Math.sqrt(A * A + B * B), Math.atan2(B, A)];
}
function oklchToRgb(L, C, h) {
  const a = C * Math.cos(h), b = C * Math.sin(h);
  const l = Math.pow(L + 0.3963377774 * a + 0.2158037573 * b, 3);
  const m = Math.pow(L - 0.1055613458 * a - 0.0638541728 * b, 3);
  const s = Math.pow(L - 0.0894841775 * a - 1.291485548 * b, 3);
  return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s];
}
const inGamut = (rgb) => rgb.every((v) => v >= -1e-4 && v <= 1 + 1e-4);
const rgbToHex = (rgb) => toHex(rgb.map((v) => {
  const x = Math.round(fromLinear(Math.max(0, Math.min(1, v))) * 255);
  return Math.max(0, Math.min(255, x));
}));

/** Palette ramp (50…950) sharing the seed's hue. */
export function rampFromSeed(seed, keys = Object.keys(RAMP_LIGHTNESS)) {
  const [, c0, h] = hexToOklch(seed);
  const out = {};
  for (const k of keys) {
    const L = RAMP_LIGHTNESS[k];
    if (L === undefined) continue;
    let c = Math.max(0, c0 * (1 - 0.7 * Math.pow((L - 0.62) / 0.62, 2)));
    for (let i = 0; i < 200 && !inGamut(oklchToRgb(L, c, h)); i++) c *= 0.96;
    out[k] = rgbToHex(oklchToRgb(L, c, h));
  }
  return out;
}

/** Accessible primary / foreground / ring (light + dark) plus palette from ANY colour, or null. */
export function schemeFromSeed(seedColor) {
  const seed = toHex(parseHex(seedColor));
  const keys = DATA.paletteKeys.length ? DATA.paletteKeys : Object.keys(RAMP_LIGHTNESS);
  const palette = rampFromSeed(seed, keys);
  const full = rampFromSeed(seed);
  const fgs = [DATA.base.light.surface, DATA.base.dark.background];
  const pick = (bgs, order) => {
    for (const cand of [seed, ...order.map((k) => full[k])]) {
      if (Math.min(...bgs.map((bg) => contrast(cand, bg))) < 3) continue;
      const fg = fgs.reduce((best, f) => (contrast(f, cand) > contrast(best, cand) ? f : best));
      if (contrast(fg, cand) >= 4.5) return [cand, fg];
    }
    return null;
  };
  const light = pick([DATA.base.light.background, DATA.base.light.surface], LIGHT_ORDER);
  const dark = pick([DATA.base.dark.background, DATA.base.dark.surface], DARK_ORDER);
  if (!light || !dark) return null;
  return {
    palette,
    light: { primary: light[0], "primary-foreground": light[1], ring: light[0] },
    dark: { primary: dark[0], "primary-foreground": dark[1], ring: dark[0] },
  };
}

// ---- the ONE place theme state lives ----
const hasDom = typeof document !== "undefined";
const media = hasDom && typeof matchMedia === "function" ? matchMedia("(prefers-color-scheme: dark)") : null;
const listeners = new Set();
let preference = readStored();
let appliedVarNames = [];

function readStored() {
  try {
    const raw = typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    const p = raw ? JSON.parse(raw) : {};
    return sanitize({ ...DEFAULT_PREFERENCE, ...p });
  } catch {
    return DEFAULT_PREFERENCE;
  }
}
function sanitize(p) {
  const mode = ["light", "dark", "system"].includes(p.mode) ? p.mode : "system";
  let theme = DATA.themes.some((t) => t.id === p.theme) || (p.theme === "custom" && DATA.customColor) ? p.theme : "default";
  let customColor = null;
  if (theme === "custom") {
    try { customColor = toHex(parseHex(p.customColor)); } catch { theme = "default"; }
  }
  return Object.freeze({ mode, theme, customColor });
}

/** "light" or "dark" — the mode actually shown (resolves "system"). */
export function resolvedMode(p = preference) {
  if (p.mode !== "system") return p.mode;
  return media && media.matches ? "dark" : "light";
}

function apply() {
  if (!hasDom) return;
  const root = document.documentElement;
  const mode = resolvedMode();
  root.dataset.theme = mode;
  root.classList.toggle("dark", mode === "dark");
  root.style.colorScheme = mode;
  root.dataset.colorTheme = preference.theme;
  for (const name of appliedVarNames) root.style.removeProperty(name);
  appliedVarNames = [];
  let stored = null;
  if (preference.theme === "custom" && preference.customColor) {
    const scheme = schemeFromSeed(preference.customColor);
    if (scheme) {
      const vars = {};
      for (const [k, v] of Object.entries(scheme[mode])) vars["--" + k] = v;
      for (const [k, v] of Object.entries(scheme.palette)) vars["--color-" + DATA.brandGroup + "-" + k] = v;
      for (const [name, value] of Object.entries(vars)) root.style.setProperty(name, value);
      appliedVarNames = Object.keys(vars);
      stored = { light: {}, dark: {} };
      for (const m of ["light", "dark"]) {
        for (const [k, v] of Object.entries(scheme[m])) stored[m]["--" + k] = v;
        for (const [k, v] of Object.entries(scheme.palette)) stored[m]["--color-" + DATA.brandGroup + "-" + k] = v;
      }
    }
  }
  try {
    if (stored) localStorage.setItem(VARS_KEY, JSON.stringify(stored)); else localStorage.removeItem(VARS_KEY);
  } catch { /* storage unavailable — theme still applies for this session */ }
}

/** Current preference (stable object; safe for useSyncExternalStore). */
export function getThemePreference() {
  return preference;
}

/** Change mode, preset theme and/or custom colour. Persists, applies and notifies subscribers. */
export function setThemePreference(patch) {
  const next = sanitize({ ...preference, ...patch, ...(patch.customColor ? { theme: "custom" } : {}) });
  if (next.mode === preference.mode && next.theme === preference.theme && next.customColor === preference.customColor) return;
  preference = next;
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(preference)); } catch { /* ignore */ }
  apply();
  listeners.forEach((l) => l());
}
export const setMode = (mode) => setThemePreference({ mode });
export const setTheme = (theme) => setThemePreference({ theme, customColor: null });
export const setCustomColor = (color) => setThemePreference({ theme: "custom", customColor: color });
export const resetTheme = () => setThemePreference({ ...DEFAULT_PREFERENCE });

/** Subscribe to preference changes (and system dark/light changes while in "system" mode). */
export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

let initialised = false;
/** Call once at app start (before render). Applies the stored theme and follows OS changes in system mode. */
export function initTheme() {
  if (initialised) return;
  initialised = true;
  apply();
  if (media) media.addEventListener("change", () => {
    if (preference.mode === "system") { apply(); listeners.forEach((l) => l()); }
  });
  if (typeof window !== "undefined") window.addEventListener("storage", (e) => {
    if (e.key === STORAGE_KEY) { preference = readStored(); apply(); listeners.forEach((l) => l()); }
  });
}
"""

JS_DTS = """// {header}
/* eslint-disable */
export type ThemeMode = "light" | "dark" | "system";
export type ThemeId = {ids} | "custom";
export interface ThemePreference {{
  readonly mode: ThemeMode;
  readonly theme: ThemeId;
  /** #RRGGBB when theme is "custom", otherwise null */
  readonly customColor: string | null;
}}
export interface ThemeOption {{
  readonly id: ThemeId;
  readonly label: {{ readonly en: string; readonly sw: string }};
  readonly swatch: string;
}}
export interface ColorScheme {{
  palette: Record<string, string>;
  light: {{ primary: string; "primary-foreground": string; ring: string }};
  dark: {{ primary: string; "primary-foreground": string; ring: string }};
}}
export declare const THEMES: readonly ThemeOption[];
export declare const CUSTOM_COLOR_ENABLED: boolean;
export declare function initTheme(): void;
export declare function getThemePreference(): ThemePreference;
export declare function setThemePreference(patch: Partial<ThemePreference>): void;
export declare function setMode(mode: ThemeMode): void;
export declare function setTheme(theme: ThemeId): void;
export declare function setCustomColor(color: string): void;
export declare function resetTheme(): void;
export declare function resolvedMode(p?: ThemePreference): "light" | "dark";
export declare function subscribe(listener: () => void): () => void;
export declare function schemeFromSeed(seed: string): ColorScheme | null;
export declare function rampFromSeed(seed: string, keys?: string[]): Record<string, string>;
export declare function contrast(a: string, b: string): number;
"""

JS_REACT = """// {header}
/* eslint-disable */
import {{ useSyncExternalStore }} from "react";
import {{
  CUSTOM_COLOR_ENABLED, THEMES, getThemePreference, resetTheme, resolvedMode, setCustomColor, setMode, setTheme, subscribe,
}} from "{module}";

/**
 * The single hook for theme UI (Appearance settings, theme toggles). Never store theme state anywhere else.
 * Call `initTheme()` once in main.tsx before rendering.
 */
export function useTheme() {{
  const preference = useSyncExternalStore(subscribe, getThemePreference, getThemePreference);
  return {{
    ...preference,
    resolvedMode: resolvedMode(preference),
    themes: THEMES,
    customColorEnabled: CUSTOM_COLOR_ENABLED,
    setMode,
    setTheme,
    setCustomColor,
    resetTheme,
  }};
}}
"""

JS_INIT = """/* {header}
   Load as a blocking script in <head> (before CSS-dependent paint) to avoid a flash of the wrong theme. */
(function () {{
  try {{
    var key = {key};
    var p = JSON.parse(localStorage.getItem(key) || "{{}}");
    var mode = p.mode === "light" || p.mode === "dark" ? p.mode
      : (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    var root = document.documentElement;
    root.dataset.theme = mode;
    root.classList.toggle("dark", mode === "dark");
    root.style.colorScheme = mode;
    root.dataset.colorTheme = typeof p.theme === "string" ? p.theme : "default";
    if (p.theme === "custom") {{
      var vars = JSON.parse(localStorage.getItem(key + "-vars") || "null");
      if (vars && vars[mode]) for (var n in vars[mode]) root.style.setProperty(n, vars[mode][n]);
    }}
  }} catch (e) {{ /* fall back to CSS defaults */ }}
}})();
"""


def gen_js(t: dict, src: str) -> str:
    data = json.dumps(theme_data(t), ensure_ascii=False, indent=2)
    return (f"// {HEADER.format(src=src)}\n/* eslint-disable */\n"
            f"// Theme runtime: the ONE place web theme state lives (mode, preset theme, custom colour).\n\nconst DATA = {data};\n{JS_ENGINE}")


def gen_dts(t: dict, src: str) -> str:
    ids = " | ".join(json.dumps(th["id"]) for th in t["_themes"])
    return JS_DTS.format(header=HEADER.format(src=src), ids=ids)


def gen_react(t: dict, src: str, module: str) -> str:
    return JS_REACT.format(header=HEADER.format(src=src), module=module)


def gen_init(t: dict, src: str) -> str:
    return JS_INIT.format(header=HEADER.format(src=src), key=json.dumps(theme_data(t)["storageKey"]))


# ---------------------------------------------------------------- Flutter runtime (app_theme.dart)
DART_RUNTIME = r"""
// Theme runtime: the ONE place Flutter theme state lives (mode, preset theme, custom colour).
//
// Wire-up (once):
//   1. Implement ThemePreferenceStore (e.g. SharedPreferences / secure storage / user profile API).
//   2. In bootstrap:  final store = MyThemeStore(); final saved = await store.load();
//      runApp(ProviderScope(overrides: [
//        themePreferenceStoreProvider.overrideWithValue(store),
//        initialThemePreferenceProvider.overrideWithValue(saved ?? AppThemePreference.initial),
//      ], child: const App()));
//   3. In App:  final theme = ref.watch(appThemeProvider);
//      MaterialApp.router(theme: theme.light, darkTheme: theme.dark, themeMode: theme.mode, ...)
//   4. Appearance settings call ref.read(appThemeControllerProvider.notifier).setMode/setTheme/setCustomColor.

import 'dart:async';
import 'dart:math' as math;

import 'package:flutter_riverpod/flutter_riverpod.dart';

enum AppThemeMode { light, dark, system }

@immutable
class AppThemeOption {
  const AppThemeOption({
    required this.id,
    required this.labelEn,
    required this.labelSw,
    required this.swatch,
    required this.light,
    required this.dark,
  });

  final String id;
  final String labelEn;
  final String labelSw;
  final Color swatch;
  final AppColors light;
  final AppColors dark;

  String label(Locale locale) => locale.languageCode == 'sw' ? labelSw : labelEn;
}

@immutable
class AppThemePreference {
  const AppThemePreference({required this.mode, required this.themeId, this.customColor});

  static const initial = AppThemePreference(mode: AppThemeMode.system, themeId: 'default');

  final AppThemeMode mode;

  /// A preset id from [AppThemes.all], or 'custom' (then [customColor] is set).
  final String themeId;
  final Color? customColor;

  AppThemePreference copyWith({AppThemeMode? mode, String? themeId, Color? customColor, bool clearCustom = false}) =>
      AppThemePreference(
        mode: mode ?? this.mode,
        themeId: themeId ?? this.themeId,
        customColor: clearCustom ? null : (customColor ?? this.customColor),
      );

  Map<String, Object?> toJson() => {
        'mode': mode.name,
        'theme': themeId,
        'customColor': customColor == null ? null : AppColorEngine.toHex(customColor!),
      };

  factory AppThemePreference.fromJson(Map<String, Object?> json) {
    final mode = AppThemeMode.values.where((m) => m.name == json['mode']).firstOrNull ?? AppThemeMode.system;
    var theme = json['theme'] is String ? json['theme']! as String : 'default';
    Color? custom;
    if (theme == 'custom') {
      custom = AppColorEngine.tryParseHex(json['customColor']);
      if (custom == null || !AppThemes.customColorEnabled) theme = 'default';
    } else if (!AppThemes.all.any((t) => t.id == theme)) {
      theme = 'default';
    }
    return AppThemePreference(mode: mode, themeId: theme, customColor: theme == 'custom' ? custom : null);
  }

  @override
  bool operator ==(Object other) =>
      other is AppThemePreference && other.mode == mode && other.themeId == themeId && other.customColor == customColor;

  @override
  int get hashCode => Object.hash(mode, themeId, customColor);
}

/// Persists the preference. Implement with SharedPreferences, secure storage or the user's profile API.
abstract interface class ThemePreferenceStore {
  Future<AppThemePreference?> load();
  Future<void> save(AppThemePreference preference);
}

final themePreferenceStoreProvider = Provider<ThemePreferenceStore>(
  (ref) => throw UnimplementedError('Override themePreferenceStoreProvider in bootstrap'),
);

/// Loaded before runApp so the first frame already has the right theme.
final initialThemePreferenceProvider = Provider<AppThemePreference>((ref) => AppThemePreference.initial);

class AppThemeController extends Notifier<AppThemePreference> {
  @override
  AppThemePreference build() => ref.watch(initialThemePreferenceProvider);

  void setMode(AppThemeMode mode) => _update(state.copyWith(mode: mode));

  void setTheme(String themeId) {
    if (!AppThemes.all.any((t) => t.id == themeId)) return;
    _update(state.copyWith(themeId: themeId, clearCustom: true));
  }

  void setCustomColor(Color color) {
    if (!AppThemes.customColorEnabled) return;
    _update(state.copyWith(themeId: 'custom', customColor: color.withAlpha(255)));
  }

  void reset() => _update(AppThemePreference.initial);

  void _update(AppThemePreference next) {
    if (next == state) return;
    state = next;
    unawaited(ref.read(themePreferenceStoreProvider).save(next));
  }
}

final appThemeControllerProvider =
    NotifierProvider<AppThemeController, AppThemePreference>(AppThemeController.new);

@immutable
class AppThemeData {
  const AppThemeData({required this.light, required this.dark, required this.mode});

  final ThemeData light;
  final ThemeData dark;
  final ThemeMode mode;
}

/// Everything MaterialApp needs, derived from the single preference above.
final appThemeProvider = Provider<AppThemeData>((ref) {
  final pref = ref.watch(appThemeControllerProvider);
  var light = AppColors.light;
  var dark = AppColors.dark;
  if (pref.themeId == 'custom' && pref.customColor != null) {
    final scheme = AppColorEngine.schemeFromSeed(pref.customColor!);
    if (scheme != null) {
      light = light.copyWith(primary: scheme.light.primary, primaryForeground: scheme.light.onPrimary, ring: scheme.light.primary);
      dark = dark.copyWith(primary: scheme.dark.primary, primaryForeground: scheme.dark.onPrimary, ring: scheme.dark.primary);
    }
  } else {
    final option = AppThemes.byId(pref.themeId);
    light = option.light;
    dark = option.dark;
  }
  return AppThemeData(
    light: buildAppTheme(Brightness.light, light),
    dark: buildAppTheme(Brightness.dark, dark),
    mode: switch (pref.mode) {
      AppThemeMode.light => ThemeMode.light,
      AppThemeMode.dark => ThemeMode.dark,
      AppThemeMode.system => ThemeMode.system,
    },
  );
});

@immutable
class SeedPair {
  const SeedPair(this.primary, this.onPrimary);
  final Color primary;
  final Color onPrimary;
}

@immutable
class SeedScheme {
  const SeedScheme({required this.palette, required this.light, required this.dark});
  final Map<String, Color> palette;
  final SeedPair light;
  final SeedPair dark;
}

/// Same algorithm as build_tokens.py and the web theme.js: any colour → accessible primary for light and dark.
abstract final class AppColorEngine {
  static const _rampLightness = <String, double>{
    '50': 0.971, '100': 0.936, '200': 0.880, '300': 0.805, '400': 0.715, '500': 0.625,
    '600': 0.535, '700': 0.455, '800': 0.380, '900': 0.300, '950': 0.220,
  };
  static const _lightOrder = ['600', '700', '500', '800', '900', '950'];
  static const _darkOrder = ['300', '400', '200', '500', '100', '50'];

  static List<int> _rgb(Color c) {
    final v = c.toARGB32();
    return [(v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF];
  }

  static String toHex(Color c) =>
      '#${_rgb(c).map((v) => v.toRadixString(16).padLeft(2, '0').toUpperCase()).join()}';

  static Color? tryParseHex(Object? value) {
    if (value is! String) return null;
    var s = value.trim().replaceFirst('#', '');
    if (s.length == 3) s = s.split('').map((ch) => '$ch$ch').join();
    if (s.length == 8) s = s.substring(0, 6);
    if (!RegExp(r'^[0-9a-fA-F]{6}$').hasMatch(s)) return null;
    return Color(0xFF000000 | int.parse(s, radix: 16));
  }

  static double _cbrt(double x) => x < 0 ? -math.pow(-x, 1 / 3).toDouble() : math.pow(x, 1 / 3).toDouble();
  static double _toLinear(double v) => v <= 0.04045 ? v / 12.92 : math.pow((v + 0.055) / 1.055, 2.4).toDouble();
  static double _fromLinear(double v) => v <= 0.0031308 ? 12.92 * v : 1.055 * math.pow(v, 1 / 2.4).toDouble() - 0.055;

  static double _luminance(Color c) {
    final rgb = _rgb(c).map((v) => _toLinear(v / 255)).toList();
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
  }

  /// WCAG contrast ratio.
  static double contrast(Color a, Color b) {
    final la = _luminance(a), lb = _luminance(b);
    final hi = math.max(la, lb), lo = math.min(la, lb);
    return (hi + 0.05) / (lo + 0.05);
  }

  static List<double> _toOklch(Color c) {
    final rgb = _rgb(c).map((v) => _toLinear(v / 255)).toList();
    final r = rgb[0], g = rgb[1], b = rgb[2];
    final l = _cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    final m = _cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    final s = _cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    final bigL = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s;
    final a = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s;
    final bb = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s;
    return [bigL, math.sqrt(a * a + bb * bb), math.atan2(bb, a)];
  }

  static List<double> _oklchToRgb(double bigL, double c, double h) {
    final a = c * math.cos(h), b = c * math.sin(h);
    final l = math.pow(bigL + 0.3963377774 * a + 0.2158037573 * b, 3).toDouble();
    final m = math.pow(bigL - 0.1055613458 * a - 0.0638541728 * b, 3).toDouble();
    final s = math.pow(bigL - 0.0894841775 * a - 1.2914855480 * b, 3).toDouble();
    return [
      4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
      -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
      -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    ];
  }

  static bool _inGamut(List<double> rgb) => rgb.every((v) => v >= -1e-4 && v <= 1 + 1e-4);

  static Color _rgbToColor(List<double> rgb) {
    final ch = rgb.map((v) {
      final x = (_fromLinear(math.max(0.0, math.min(1.0, v))) * 255).round();
      return math.max(0, math.min(255, x));
    }).toList();
    return Color(0xFF000000 | (ch[0] << 16) | (ch[1] << 8) | ch[2]);
  }

  /// Palette ramp (50…950) sharing the seed's hue.
  static Map<String, Color> rampFromSeed(Color seed, [Iterable<String>? keys]) {
    final lch = _toOklch(seed);
    final out = <String, Color>{};
    for (final k in keys ?? _rampLightness.keys) {
      final bigL = _rampLightness[k];
      if (bigL == null) continue;
      final t = (bigL - 0.62) / 0.62;
      var c = math.max(0.0, lch[1] * (1 - 0.7 * t * t));
      for (var i = 0; i < 200 && !_inGamut(_oklchToRgb(bigL, c, lch[2])); i++) {
        c *= 0.96;
      }
      out[k] = _rgbToColor(_oklchToRgb(bigL, c, lch[2]));
    }
    return out;
  }

  /// Accessible primary + on-primary for light and dark from ANY colour, or null.
  static SeedScheme? schemeFromSeed(Color seedColor) {
    final seed = seedColor.withAlpha(255);
    final full = rampFromSeed(seed);
    final fgs = [AppColors.light.surface, AppColors.dark.background];

    SeedPair? pick(List<Color> bgs, List<String> order) {
      for (final cand in [seed, ...order.map((k) => full[k]!)]) {
        final worst = bgs.map((bg) => contrast(cand, bg)).reduce((a, b) => a < b ? a : b);
        if (worst < 3.0) continue;
        final fg = fgs.reduce((best, f) => contrast(f, cand) > contrast(best, cand) ? f : best);
        if (contrast(fg, cand) >= 4.5) return SeedPair(cand, fg);
      }
      return null;
    }

    final light = pick([AppColors.light.background, AppColors.light.surface], _lightOrder);
    final dark = pick([AppColors.dark.background, AppColors.dark.surface], _darkOrder);
    if (light == null || dark == null) return null;
    return SeedScheme(palette: rampFromSeed(seed, AppThemes.paletteKeys), light: light, dark: dark);
  }
}
"""


def gen_dart_runtime(t: dict, src: str, material_import: str, tokens_import: str) -> str:
    body = DART_RUNTIME.replace(
        "import 'dart:async';\nimport 'dart:math' as math;\n\nimport 'package:flutter_riverpod/flutter_riverpod.dart';\n", "")
    return (f"// {HEADER.format(src=src)}\n// ignore_for_file: type=lint\n\n"
            "import 'dart:async';\nimport 'dart:math' as math;\n\n"
            f"import '{material_import}';\nimport 'package:flutter_riverpod/flutter_riverpod.dart';\n\n"
            f"import '{tokens_import}';\n" + body)


def gen_preview(t: dict, src: str) -> str:
    """Standalone HTML page showing the design direction (palette, type, components, motion) in light and dark."""
    # Browsers ignore Tailwind's @theme at-rules, so inline the same variables as plain :root CSS.
    plain_vars = gen_css(t, src).replace("@theme inline {", ":root {").replace("@theme {", ":root {")
    generic = {"serif", "sans-serif", "monospace", "system-ui", "ui-sans-serif", "ui-serif", "ui-monospace", "cursive"}
    families = []
    for v in t.get("font", {}).get("family", {}).values():
        first = font_stack(v)[0]
        if first not in generic and first not in families:
            families.append(first)
    fonts_link = ""
    if families:  # preview only — production apps self-host / bundle their fonts
        q = "&".join(f"family={f.replace(' ', '+')}:wght@400;500;600;700" for f in families)
        fonts_link = f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{q}&display=swap">'
    engine = gen_js(t, src).replace("</script", "<\\/script")
    meta = t.get("meta", {})
    name = meta.get("name", "Design preview")
    direction = meta.get("direction", "")
    swatches = []
    for group, shades in t["color"].get("palette", {}).items():
        cells = "".join(f'<div class="sw" style="background:var(--color-{group}-{k}, {v})"><span>{k}</span></div>' for k, v in shades.items())
        swatches.append(f'<h3>{group}</h3><div class="row">{cells}</div>')
    semantic = "".join(
        f'<div class="sem" style="background:var(--{k});color:var(--{fg})"><b>{k}</b><small>on {fg}</small></div>'
        for k, fg in [("background", "foreground"), ("surface", "foreground"), ("surface-muted", "foreground-muted"),
                      ("primary", "primary-foreground"), ("secondary", "secondary-foreground"), ("accent", "accent-foreground"),
                      ("success", "success-foreground"), ("warning", "warning-foreground"), ("danger", "danger-foreground"),
                      ("info", "info-foreground")])
    sizes = "".join(f'<p style="font-size:var(--text-{k});line-height:var(--text-{k}--line-height);font-family:var(--font-{"heading" if k in ("2xl","3xl","4xl","5xl") else "body"})">{k} — Soko la mifugo, haraka na salama</p>'
                    for k in t.get("text", {}))
    eases = "".join(f'<div class="ease"><span>{k}</span><div class="track"><div class="dot" style="transition-timing-function:var(--ease-{k})"></div></div></div>'
                    for k in t.get("motion", {}).get("easing", {}))
    return f"""<!doctype html>
<!-- {HEADER.format(src=src)} -->
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} — design preview</title>
{fonts_link}
<style>
{plain_vars}
* {{ box-sizing: border-box }}
body {{ margin:0; background:var(--background); color:var(--foreground); font-family:var(--font-body); }}
main {{ max-width:1100px; margin:0 auto; padding:32px 16px 96px }}
h1,h2,h3 {{ font-family:var(--font-heading); }} h1 {{ font-size:var(--text-4xl); margin:0 }} h3 {{ text-transform:capitalize; margin:20px 0 8px }}
.muted {{ color:var(--foreground-muted) }}
.row {{ display:flex; flex-wrap:wrap; gap:8px }}
.sw {{ width:92px; height:72px; border-radius:var(--radius-md); padding:6px; display:flex; flex-direction:column; justify-content:flex-end; font-size:11px; color:#000; border:1px solid var(--border) }}
.sw span, .sw code {{ background:#ffffffcc; border-radius:4px; padding:0 4px; width:fit-content }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:10px }}
.sem {{ padding:14px; border-radius:var(--radius-lg); border:1px solid var(--border); display:flex; flex-direction:column; gap:4px }}
.card {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-xl); padding:24px; box-shadow:var(--shadow-md); max-width:420px }}
.btn {{ font:inherit; font-weight:600; border:0; border-radius:var(--radius-md); padding:10px 18px; cursor:pointer;
  transition: transform var(--duration-fast) var(--ease-standard), box-shadow var(--duration-fast) var(--ease-standard), background-color var(--duration-fast) var(--ease-standard) }}
.btn:hover {{ transform:translateY(-1px); box-shadow:var(--shadow-sm) }} .btn:active {{ transform:scale(.98) }}
.btn:focus-visible, input:focus-visible {{ outline:3px solid var(--ring); outline-offset:2px }}
.primary {{ background:var(--primary); color:var(--primary-foreground) }}
.secondary {{ background:var(--secondary); color:var(--secondary-foreground) }}
.accent {{ background:var(--accent); color:var(--accent-foreground) }}
input {{ font:inherit; width:100%; padding:10px 12px; border-radius:var(--radius-md); border:1px solid var(--input); background:var(--surface); color:var(--foreground) }}
.ease {{ display:grid; grid-template-columns:120px 1fr; align-items:center; gap:12px; margin:8px 0 }}
.track {{ height:28px; background:var(--surface-muted); border-radius:var(--radius-full); position:relative }}
.dot {{ position:absolute; top:4px; left:4px; width:20px; height:20px; border-radius:50%; background:var(--primary); transition-property:left; transition-duration:var(--duration-slow) }}
body.play .dot {{ left:calc(100% - 24px) }}
.toolbar {{ position:sticky; top:0; background:var(--surface); border-bottom:1px solid var(--border); padding:10px 16px; display:flex; flex-wrap:wrap; align-items:center; gap:8px; z-index:1 }}
select {{ font:inherit; padding:8px 10px; border-radius:var(--radius-md); border:1px solid var(--input); background:var(--surface); color:var(--foreground) }}
.pick {{ display:flex; align-items:center; gap:6px; font-size:var(--text-sm) }} .pick input {{ width:40px; height:32px; padding:0; border:0; background:none }}
</style></head>
<body>
<div class="toolbar">
<select id="mode" aria-label="Mode"><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select>
<select id="theme" aria-label="Colour theme"></select>
<label class="pick" id="customWrap">Any colour <input type="color" id="custom" value="#7c3aed"></label>
<button class="btn primary" onclick="document.body.classList.toggle('play')">Play motion</button></div>
<script type="module">
{engine}
initTheme();
const mode = document.getElementById("mode"), theme = document.getElementById("theme"), custom = document.getElementById("custom");
for (const t of THEMES) theme.add(new Option(t.label.en + " / " + t.label.sw, t.id));
if (CUSTOM_COLOR_ENABLED) theme.add(new Option("Custom / Rangi yako", "custom")); else document.getElementById("customWrap").hidden = true;
const sync = () => {{ const p = getThemePreference(); mode.value = p.mode; theme.value = p.theme; if (p.customColor) custom.value = p.customColor.toLowerCase(); }};
mode.onchange = () => setMode(mode.value);
theme.onchange = () => theme.value === "custom" ? setCustomColor(custom.value) : setTheme(theme.value);
custom.oninput = () => setCustomColor(custom.value);
subscribe(sync); sync();
</script>
<main>
<p class="muted">Design preview</p><h1>{name}</h1><p class="muted">{direction}</p>
<h2>Semantic colours</h2><div class="grid">{semantic}</div>
<h2>Palette</h2>{''.join(swatches)}
<h2>Typography</h2>{sizes}
<h2>Components</h2>
<div class="card"><h3 style="margin-top:0;text-transform:none">Ng'ombe wa maziwa — Arusha</h3>
<p class="muted">Dairy cow, 3 years · TSh 1,850,000</p>
<label>Jina / Name<input placeholder="Andika jina lako"></label>
<div class="row" style="margin-top:16px"><button class="btn primary">Nunua sasa</button><button class="btn secondary">Hifadhi</button><button class="btn accent">Ofa</button></div></div>
<h2>Motion</h2><p class="muted">Durations and easing curves (disabled when the OS asks for reduced motion).</p>{eases}
</main></body></html>
"""


# ---------------------------------------------------------------- main
def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    config_path = Path(argv[0]).resolve()
    check = "--check" in argv[1:]
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    base = config_path.parent
    tokens_path = (base / cfg.get("tokens", "tokens.json")).resolve()
    try:
        tokens = load(tokens_path)
        problems = check_contrast(tokens)
        if problems:
            print("✗ contrast check failed (WCAG 2.2):", *problems, sep="\n  ", file=sys.stderr)
            return 1
        src = tokens_path.name
        outputs = cfg.get("outputs", {})
        generated: dict[Path, str] = {}
        if outputs.get("css"):
            generated[(base / outputs["css"]).resolve()] = gen_css(tokens, src)
        if outputs.get("dart"):
            import os
            mat = cfg.get("dartMaterialImport", "package:flutter/material.dart")
            dart_path = (base / outputs["dart"]).resolve()
            runtime_path = dart_path.with_name("app_theme.dart")
            generated[dart_path] = gen_dart(tokens, src, mat, runtime_path.name)
            generated[runtime_path] = gen_dart_runtime(tokens, src, mat, dart_path.name)
        if outputs.get("js"):
            js_path = (base / outputs["js"]).resolve()
            generated[js_path] = gen_js(tokens, src)
            generated[js_path.with_suffix(".d.ts")] = gen_dts(tokens, src)
            if outputs.get("react"):
                react_path = (base / outputs["react"]).resolve()
                import os
                module = os.path.relpath(js_path.with_suffix(""), react_path.parent).replace(os.sep, "/")
                module = module if module.startswith(".") else "./" + module
                generated[react_path] = gen_react(tokens, src, module)
        if outputs.get("themeInit"):
            generated[(base / outputs["themeInit"]).resolve()] = gen_init(tokens, src)
        if outputs.get("preview"):
            generated[(base / outputs["preview"]).resolve()] = gen_preview(tokens, src)
    except (TokenError, KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"✗ tokens error: {e}", file=sys.stderr)
        return 1

    stale = []
    for path, content in generated.items():
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"✓ wrote {path}")
    if stale:
        print("✗ generated token files are out of date — run `just tokens` and commit:", *map(str, stale), sep="\n  ", file=sys.stderr)
        return 1
    if check:
        print("✓ tokens OK (contrast passes, generated files up to date)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
