---
name: design-extract
description: Extract a complete design system (colours, typography, spacing, layout, components, states, icons, imagery, motion) from a provided source — screenshots, images, PDFs, Figma or website links, design files or an existing app — turn it into exact design tokens, and generate a project skill to implement that design faithfully. Use when someone shares a design to replicate or match.
argument-hint: [source paths or links] [notes]
---

# Design extraction → tokens → faithful implementation

Goal: reproduce a provided design **as it is** — same colours, type, spacing, shapes, components and motion — in this project, with production-quality code. Measure; never eyeball when a measurement is possible. Record every deviation.

Sources: `$ARGUMENTS`, attached images, or files the user points to.

## 0. Permission check (always)

Replicate exactly only designs the user owns, commissioned, or is licensed/permitted to use (their brand guide, their Figma, their designer's mockups, their existing app, an open-source design system with a compatible licence). For a third party's product or site used as *inspiration*:
- extract the **system** (scales, spacing rhythm, component patterns, motion feel) but do **not** copy logos, wordmarks, brand names, proprietary illustrations, photography or icon sets, and don't make the result passable as that brand;
- say so to the user in one line and continue.
Fonts: use the same font only if it's licensed for the target platforms (web + app); otherwise pick the closest open-licence match and record it in `fidelity.md`.

## 1. Outputs (single-app repo: `design/` · monorepo: `packages/design/`)

```
design-source/            raw inputs + measurements (screenshots, PDFs pages, exports, reports) — committed
tokens.json               exact tokens in the project schema (see design-direction skill) — compiled by `just tokens`
design.md                 the direction, written from the source ("Extracted from: …")
components.md             every component: anatomy, variants, sizes, states, exact values, behaviour
layout.md                 grid, breakpoints, containers, spacing & alignment rules, page/screen templates
assets.md                 fonts (+ licence), icon set, illustration/photo style, logo usage rules
fidelity.md               deviations from the source and why (contrast fixes, font substitutes, derived dark mode, gaps)
.claude/skills/design-system/SKILL.md   generated project skill — how to build UI in THIS design (template in references/)
```

## 2. Workflow

### Step 1 — Intake
1. List every source and what it covers (screens, components, states, light/dark, mobile/desktop). Save copies under `design-source/` (`images/`, `pdf/`, `web/`, `figma/`).
2. Ask once for gaps that change the result: missing states (hover, pressed, focus, disabled, error, loading, empty), dark mode, mobile vs desktop, device scale factor of screenshots, brand fonts' licence. If the user can't provide them, derive them later and mark as derived.

### Step 2 — Measure (by source type)

| Source | How to measure | Fidelity |
|---|---|---|
| **Existing code / design system** (CSS, Tailwind config, theme files, Flutter ThemeData) | Read the values directly | exact |
| **Figma** | If a Figma connector/MCP tool is available: read variables, styles, components, auto-layout spacing, effects. Otherwise ask for: Variables/Tokens export (DTCG or Tokens Studio JSON), frames exported as PNG @1x and @2x, Dev Mode specs/screenshots of key components | exact |
| **Website / web app link** | `python3 scripts/extract_url_styles.py <url> --out design-source/web --widths 390,768,1280` for each key page. Gives rendered colours (by area), fonts, type scale, line heights, letter spacing, radii, shadows, borders, spacing values + base unit, containers, transitions, CSS variables, @font-face sources and component crops. For hover/focus states, open the page with Playwright, `hover()`/`focus()` the element and read `getComputedStyle` | exact (rendered) |
| **Images / screenshots / mockups** | `python3 scripts/extract_image_palette.py <images> --out design-source/images` for exact colours and contrast; `--region name:x,y,w,h` / `--point` on flat areas (button fill, heading text stroke centre, card surface). Measure sizes by cropping and zooming (open crops with the Read tool), divide by the screenshot's scale factor (2x/3x). Identify fonts by letterforms (a, g, R, numerals): give 2–3 candidates and confirm with the user — never claim certainty | exact colours, ±1px sizes |
| **PDF** (brand guide, exported mockups) | `pdffonts file.pdf` (exact embedded font names), `pdftotext` (copy, specified hex/CMYK values in brand guides), `pdftoppm -png -r 144 file.pdf design-source/pdf/page` then treat pages as images. Prefer values written in the guide over sampled pixels | exact if specified |

Scripts live in this skill's folder: `.claude/skills/design-extract/scripts/` in projects (vendored), or the `vekta-design` plugin's `skills/design-extract/scripts/` when installed as a plugin. Below, `scripts/` means that folder. They need Python 3 + Pillow; the URL script needs Playwright Chromium (`pip install playwright pillow && python -m playwright install chromium`).

### Step 3 — Extract the system
Work through `references/extraction-checklist.md` completely. Every value gets a source reference (file + region or page + selector) in your notes. Typical decisions:
- **Scales**: collect all measured values, cluster them, and name the scale steps (`text.xs…5xl`, `space.scale`, `radius.sm…full`). Keep exact values; only snap ±1px when the source clearly uses a scale (e.g. 15/16/17 → 16 when 16 dominates).
- **Colour roles**: map measured colours to semantic roles (background, surface, surface-muted, surface-raised, foreground, foreground-muted, primary(+foreground), secondary, accent, border, input, ring, success/warning/danger/info). Keep every brand colour in `color.palette` with its exact hex; build 50–950 ramps around brand colours only if the source implies tints.
- **Components**: one spec per component using `references/component-spec.md` — anatomy, exact measurements, variants, sizes, every state, behaviour and motion.
- **Layout**: grid columns, gutters, margins, container max-widths per breakpoint, section spacing, alignment rules (what aligns to what), screen templates.

### Step 4 — Write the tokens and docs
1. `tokens.json` in the project schema; `meta.source` lists the sources; `meta.direction` = "Extracted from <name>".
2. **Dark mode**: use the source's if it exists; otherwise derive a designed dark mode from the same palette and mark it `derived` in `fidelity.md`.
3. Extra themes: only if the source defines them (`color.themes`); keep `customColor` as the project prefers.
4. `design.md`, `components.md`, `layout.md`, `assets.md`, `fidelity.md` — specific, measured, with references to `design-source/` images.

### Step 5 — Generate the project design-system skill
Fill `references/design-system-skill-template.md` and save it as `.claude/skills/design-system/SKILL.md` in the project. It must point to the docs above, list the golden rules, the token usage per platform, and the fidelity check. This is what every future UI task follows.

### Step 6 — Build and verify
1. `just tokens`. If contrast fails: keep the exact palette, adjust only the failing **semantic pairing** (e.g. a darker shade of the same brand hue for text-on-brand) by the smallest step that passes, and record it in `fidelity.md`. Tell the user — accessibility is a requirement, not a preference.
2. Build a **reference gallery** (web route `/design-system` in dev only, Flutter debug screen or Widgetbook) showing every token and component in all states, light/dark, en + sw.
3. Recreate 1–3 key source screens with the real components. Capture screenshots at the source's width and scale (Playwright for web; `flutter screenshot`/golden tests for mobile) and run
   `python3 scripts/compare_screens.py design-source/<screen>.png <your-screenshot>.png --out design-source/compare/<screen>`.
   Fix spacing, type and colour drift until differences are only content or anti-aliasing (aim < 3%, no clustered red areas). Keep the comparison images in `design-source/compare/`.
4. Add golden/visual tests for the gallery so the design can't drift later.

### Step 7 — Handoff
Report: what was extracted (counts: colours, type styles, components), how it was measured, fidelity results per screen, deviations (`fidelity.md`), and open questions. From now on UI work follows `.claude/skills/design-system/SKILL.md` plus the stack skills and `ui-craft`.

## Rules
- Exact over approximate: sampled pixel values, rendered CSS, specified hex — never "close enough" guesses. When estimating (fonts from images, hidden states), say it's an estimate.
- One source of truth: values live only in `tokens.json` → generated files; components never hard-code values.
- Don't import the source's problems silently: inaccessible contrast, tiny touch targets (< 44/48px), missing focus styles — fix minimally and record.
- Kiswahili + English: check every component with longer Swahili strings; don't fix widths the source fixed for short English labels.
- Platform conventions win where copying would break them (iOS/Android back behaviour, safe areas, system text scaling) — record the adaptation.
