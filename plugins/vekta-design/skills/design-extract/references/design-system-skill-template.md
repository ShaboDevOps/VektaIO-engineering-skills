# Template for the generated project skill

Save as `.claude/skills/design-system/SKILL.md` in the project, filling every `<…>`. Keep it concise — it points to the detailed docs.

```markdown
---
name: design-system
description: Use for ANY UI work in <Product> (web or mobile) — screens, components, layouts, styling, animation. Implements the <Product> design extracted from <source names> exactly, using the project's tokens and component specs.
---

# <Product> design system

This product's UI must match the source design: <one line describing the look, e.g. "clean white surfaces, deep teal primary, rounded 12px cards, Sora headings">.
Source of truth (read the relevant parts before building UI):
- `<design dir>/design.md` — direction and rules
- `<design dir>/components.md` — exact specs for every component
- `<design dir>/layout.md` — grid, spacing, alignment, screen templates
- `<design dir>/assets.md` — fonts, icons, imagery
- `<design dir>/fidelity.md` — known deviations (don't "fix" these back)
- `<design dir>/design-source/` — original screens to compare against

## Golden rules
1. Only tokens: semantic colours, type styles, spacing, radius, shadows, motion from the generated files (`tokens.css` / `app_tokens.dart`). Never hard-code values.
2. Build from the component library first (`<web path>/shared/ui`, `<mobile path>/ui/core`). If a component is missing, implement it from its spec in `components.md` and add it to the gallery.
3. Match the source's layout rules: <3–5 most important, e.g. "16px screen margins on mobile", "cards in a 2-column grid from 768px", "section spacing 48px", "icons 20px with 8px gap">.
4. Every state from the spec (hover, pressed, focus, disabled, loading, error, empty) — light + dark, en + sw.
5. Motion exactly as specified: <signature motions, e.g. "cards lift 2px on hover, 150ms standard">; respect reduced motion.
6. Icons: <icon set, style, stroke, sizes>. Imagery: <style rules>.

## Platform mapping
| Need | Web (React + Tailwind 4) | Mobile (Flutter) |
|---|---|---|
| Colours | `bg-surface text-foreground bg-primary …` | `context.colors.surface` / `Theme.of(context).colorScheme` |
| Type | `text-<size> font-heading` | `Theme.of(context).textTheme.<role>` |
| Spacing | `p-4 gap-3` (`--spacing` = <base>px) | `AppSpace.<step>` |
| Radius / shadow | `rounded-<step> shadow-<step>` | `AppRadius.<step>` / `AppShadows.<step>` |
| Motion | `duration-(--duration-<step>) ease-<curve>` | `AppMotion.<step>`, `AppMotion.<curve>` |
| Theme / mode | `useTheme()` | `appThemeControllerProvider` |

## Fidelity check (before shipping UI)
1. Screenshot the screen at the source's width and scale.
2. `python3 .claude/skills/design-extract/scripts/compare_screens.py <design dir>/design-source/<screen>.png <shot>.png --out <design dir>/design-source/compare/<screen>` (if the screen exists in the source).
3. Fix drift until only content differs; update golden tests.
```
