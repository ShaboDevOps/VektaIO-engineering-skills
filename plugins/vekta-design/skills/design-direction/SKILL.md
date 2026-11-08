---
name: design-direction
description: Create or change a product's unique visual identity — design direction, design tokens (colour, type, shape, depth, motion) and a preview — from the user's brand inputs or from scratch. Use before building UI for a new product, or when asked about a project's look, theme, brand, style or design tokens.
argument-hint: [brand inputs, references or keywords]
---

# Design direction

Every product gets **its own** look. Never reuse another product's palette, type pairing or motion character, and never ship a component library's default appearance. The output of this skill is the single source of truth for every UI in the project (web and mobile):

```
design/                (single-app repo)      packages/design/   (monorepo)
  design.md            the direction: principles, colour/type/shape/motion rules, do/don't, voice
  tokens.json          design tokens (W3C DTCG-style JSON)
  design.config.json   where generated files go
  preview.html         generated visual preview (light/dark, components, motion)
```
`just tokens` (→ `scripts/tokens.sh` → `scripts/build_tokens.py`) generates the Tailwind CSS theme for web and the Flutter theme for mobile, and fails if any text/background pair is below WCAG contrast. CI runs `just tokens --check`.

## 1. Gather inputs (use whatever the user provides — all optional)

| Input | How to use it |
|---|---|
| Existing tokens (Figma Tokens Studio / DTCG JSON, Style Dictionary, CSS variables) | Map into `tokens.json` structure; keep their values; fill gaps |
| Brand guide / logo / brand colours | Derive palette from logo colours (pick brand + accent), keep brand fonts if licensed for web + app |
| Reference sites, apps, screenshots (`$ARGUMENTS`, attached images, URLs) | Extract what to borrow (palette mood, type feel, density, motion) — never copy a brand |
| Keywords / mood ("earthy, trustworthy, modern") | Pick and adapt an archetype from `presets.md` |
| Nothing | Ask the short brief below |

**Short brief** (ask only what's missing, in one message):
1. Product in one sentence, and who uses it (age, tech comfort, devices, outdoor/indoor).
2. Three personality words. Any colours or styles to **avoid**?
3. Products or sites they like the look of, and why.
4. Light-first, dark-first, or both equally?
5. Our other products' directions (or their `design.md`) so this one is clearly different.

## 2. Propose 2–3 distinct directions

Start from `presets.md` archetypes, then make each one specific to this product. For each direction show:
- **Name + one-line feel**, personality words
- **Palette**: brand, accent, neutral temperature, with hex swatches
- **Type pairing** (heading + body, both free for web and app use, e.g. Google Fonts / OFL), why it fits
- **Shape & depth**: radius scale, borders vs shadows, signature element
- **Motion character**: durations, easing, one signature moment
- **How it differs** from the user's other products

Let the user choose or mix. If they're unavailable, pick the best fit and say why.

## 3. Build the tokens

Write `tokens.json` following the structure of the template (`templates/design/tokens.json` in the skills repo):
- `color.palette` — `brand`, `accent`, `neutral` (0–950) and optional extra hues; 50–900 ramps with even perceived steps.
- `color.light` and `color.dark` — **all** semantic keys: background, surface, surface-muted, surface-raised, foreground, foreground-muted, primary(+foreground), secondary(+foreground), accent(+foreground), border, input, ring, success/warning/danger/info(+foreground). Reference palette values (`{color.palette.brand.600}`). Dark mode is designed, not inverted: lighter brand shade for primary, raised surfaces lighter than background, reduce saturation of large areas.
- `font.family` (heading, body, mono), `font.weight`, `text` scale (xs–5xl with lineHeight, tighter letterSpacing on large sizes).
- `space.base` (Tailwind spacing unit) and `space.scale` (named steps for Flutter).
- `radius`, `shadow` (objects with offsetX/offsetY/blur/spread/color; tinted with the neutral, not pure black), `motion.duration`, `motion.easing` (cubic-bezier arrays), `breakpoint`, `density`.
- `meta`: name, direction, version (optional `themeStorageKey`, default `app-theme`).
- **Colour themes** users can switch between at runtime:
  - `color.defaultTheme.label` — `{ "en": "…", "sw": "…" }` name of the base direction.
  - `color.themes` — 2–4 presets that suit the direction, each `{ "label": {en, sw}, "seed": "#hex" }` (palette + accessible primary are derived automatically) or explicit partial `light` / `dark` semantic overrides. Every preset is contrast-checked in both modes.
  - `color.customColor` — `true` to let users pick any colour (safe: the engine adjusts shades for contrast), `false` for strict brand control (e.g. regulated/health products).
  - `color.brandGroup` — palette group that themes recolour (default `brand`).

Then write `design.md` (template sections: direction, principles, colour, typography, shape/depth/texture, layout & density, iconography & imagery, motion, voice & microcopy in en + sw, do/don't, references).

## 4. Generate, verify, show

1. Run `just tokens`. Fix every contrast failure by adjusting shades (never by lowering the requirement).
2. Open/screenshot `preview.html` (use its Mode / Theme / Any colour switcher) in light and dark and every preset; check the hierarchy reads well, accent isn't overused, Swahili sample text fits.
3. Fonts: web self-hosts them (e.g. `@fontsource/<font>` packages) — no runtime Google Fonts calls in production; Flutter bundles font files under `assets/fonts/` and declares them in `pubspec.yaml` (no runtime downloading — offline and privacy).
4. Show the user the preview and a short summary of the direction. Iterate until approved.
5. Commit `design/` (or `packages/design/`) plus generated `tokens.css` / `app_tokens.dart` in one commit: `feat(design): <direction name> design direction`.

## 5. Changing an existing direction

Change `tokens.json` / `design.md`, run `just tokens`, and review every screen that uses changed tokens (visual snapshot / golden tests will show the diff). Bump `meta.version`. Large rebrands go behind a feature flag or a release note.

## Anti-sameness checklist (must differ from sibling products on at least 4)
- [ ] Primary hue family (≥ 30° apart on the colour wheel) and neutral temperature
- [ ] Heading typeface (and ideally body)
- [ ] Radius scale / shape language
- [ ] Depth model (flat + borders, soft shadows, layered surfaces)
- [ ] Motion character and signature moment
- [ ] Iconography set/style and imagery style
- [ ] Signature element (texture, divider, badge style, illustration)
