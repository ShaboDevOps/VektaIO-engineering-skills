---
name: ui-craft
description: Apply a product's design direction with expert UX, visual polish and motion when building or reviewing any web (React) or mobile (Flutter) screen or component. Use for layouts, components, forms, empty/loading/error states, microinteractions, transitions and animations.
---

# UI craft — UX, polish and motion

Build screens that look designed for *this* product, feel fast, and work for everyone. Always read the project's `design.md` and use only its tokens (`design/` or `packages/design/`). If there is no design direction yet, run `/vekta-design:design-direction` first.

## 1. Non-negotiables
- **Tokens only**: colours (semantic: `bg-primary`, `text-foreground`, `context.colors.primary`), fonts, sizes, spacing, radius, shadows, durations and easings come from generated tokens. No hex codes, no magic numbers, no default library look.
- **Restyle the component library**: shadcn/ui, Base UI or Material widgets are starting points — adapt radius, density, borders/shadows, focus style and motion to `design.md`. A reviewer should not be able to tell which library was used.
- **Every state designed**: default, hover, pressed, focus-visible, disabled, loading, error, empty, success — in light and dark, English and Swahili, small and large screens.
- **Accessible**: WCAG 2.2 AA contrast (enforced by tokens), visible focus ring using `ring`, touch targets ≥ 44px (web) / 48dp (mobile), labels for every input, never colour alone to convey meaning.

## 2. Theming — light, dark, system, preset themes and any colour (one place)

All theme state lives in **one controller per app**, generated from the project's tokens by `just tokens`:

| | Web | Flutter |
|---|---|---|
| Controller | `src/shared/theme/theme.js` (`initTheme`, `setMode`, `setTheme`, `setCustomColor`, `resetTheme`, `subscribe`) | `lib/app/theme/app_theme.dart` (`appThemeControllerProvider`) |
| UI access | `useTheme()` hook (`src/shared/theme/useTheme.ts`) | `ref.watch(appThemeControllerProvider)` / `.notifier` |
| Applied by | `<html data-theme data-color-theme>` + CSS variables; `public/theme-init.js` in `<head>` prevents a flash | `appThemeProvider` → `MaterialApp(theme, darkTheme, themeMode)` |
| Persisted | `localStorage` (+ optional sync to the user profile API) | `ThemePreferenceStore` you implement (SharedPreferences and/or profile API) |

Preference = **mode** (`system` default, `light`, `dark`) + **theme** (`default`, a preset id from `tokens.json` → `color.themes`, or `custom`) + **customColor** (any `#RRGGBB`).
- **Any colour is safe**: the OKLCH engine keeps the user's exact colour when it's readable, otherwise picks the nearest shade of the same hue that meets WCAG (primary ≥ 3:1 on backgrounds, text on primary ≥ 4.5:1), separately for light and dark. Never apply a raw user colour to `--primary` yourself.
- **Never** read/write theme state anywhere else (no ad-hoc `localStorage`, `prefers-color-scheme` checks, `Theme.of(context).brightness` hacks or per-screen dark flags). Components only use semantic tokens, so they follow every theme automatically.
- Preset themes change brand/primary only by default; neutrals, status colours and surfaces stay consistent so the product still feels like itself.

**Appearance settings screen** (every app with a UI has one, en + sw):
1. **Mode** — segmented control: System · Light · Dark (Mfumo · Mwanga · Giza).
2. **Colour theme** — grid of swatches from `THEMES` / `AppThemes.all` with localized labels; selected state with check icon + `aria-pressed`/`Semantics(selected:)`.
3. **Custom colour** (if `customColorEnabled`) — colour picker + hex input with live preview of a button and card; short note: "We adjust shades so text stays readable."
4. **Reset to default**.
Changes apply instantly (no save button), animate colours with `duration-fast` (or not at all with reduced motion), and are announced to screen readers.
Optionally sync the preference to the user's profile so it follows them across devices (API: `PATCH /api/v1/me/preferences`).

## 3. Layout & hierarchy
- One primary action per screen, visually dominant (`primary`); secondary actions quieter; destructive actions use `danger` and confirm.
- Hierarchy through size, weight and space before colour. Use the type scale only — no in-between sizes.
- Consistent spacing rhythm from the scale; group related items, separate groups with more space than items within them.
- Mobile-first; key actions in thumb reach on phones (bottom bars, sticky CTAs); content max-width ~70ch for reading.
- Numbers that change or compare (prices, stats) use tabular figures.

## 4. UX patterns
- **Forms**: single column, labels above fields, input types/keyboards matching data (`tel`, numeric for TSh), inline validation on blur, errors that say how to fix (en + sw), keep user input on error, primary button shows progress and prevents double submit.
- **Loading**: skeletons shaped like the content (not spinners) for > 300ms waits; optimistic updates for quick actions; never block the whole screen for a local action.
- **Empty states**: explain what goes here, why it's empty, and one action to fill it; brand illustration or icon from the chosen set.
- **Errors**: inline near the cause; offline banner with retry; never a dead end.
- **Feedback**: every tap/click acknowledges within 100ms (pressed state, haptic on mobile); toasts for background results; undo instead of confirm where possible.
- **Navigation**: predictable back behaviour, preserved scroll and filters, deep-linkable screens.
- **Low connectivity & low-end devices**: small images, cached data first, progressive loading, text over heavy imagery.

## 5. Motion system
Motion explains change; it never decorates for its own sake.

| Use | Duration token | Easing token |
|---|---|---|
| Hover, press, toggle, colour change | `fast` (or `instant`) | `standard` |
| Element enter (menus, toasts, cards appearing) | `base` | `enter` (decelerate) |
| Element exit | `fast` (shorter than enter) | `exit` (accelerate) |
| Page / route transition, sheets, dialogs | `page` / `base` | `standard` / `enter` |
| Key brand moment (success, onboarding, celebration) | `slow` | `emphasized` |

Rules:
- Animate **transform and opacity** only (no width/height/top/left on the web; prefer implicit/transform-based animations in Flutter) — 60fps on low-end Android.
- Larger distance/size → longer duration, but UI motion stays ≤ 400ms; staggered lists 30–50ms per item, max ~6 items staggered.
- Enter from where the element comes from (menus from their trigger, sheets from the bottom); exits are quicker and simpler.
- Use shared-element/hero transitions to connect list → detail.
- Interruptible: user input cancels or reverses running animations; never block input while animating.
- **Reduced motion**: when the OS asks (`prefers-reduced-motion` / `MediaQuery.disableAnimationsOf`), replace movement with fades or nothing. Token durations already collapse to 0 on web.
- Define 1–3 **signature moments** from `design.md` and implement them carefully; keep everything else quiet.

### Web (React)
- CSS transitions with token utilities: `transition duration-(--duration-fast) ease-standard`.
- Route/page transitions: View Transitions API (`<ViewTransition>` in React 19.3, or `document.startViewTransition`).
- Complex, gesture, layout or spring animations: **Motion** (motion.dev, `motion/react`) — pass token values (`duration: 0.24`, `ease: [0.2, 0, 0, 1]`) from a small `motion.ts` that reads the same numbers as the tokens; use `useReducedMotion()`.
- Lazy-load heavy animation (Lottie/Rive) only for signature moments; keep under budget.

### Mobile (Flutter)
- Implicit animations first (`AnimatedContainer`, `AnimatedOpacity`, `AnimatedSwitcher`, `AnimatedSize`) with `AppMotion.base` / `AppMotion.standard`.
- Page transitions via `ThemeData.pageTransitionsTheme` (keep Android predictive back); `Hero` for list → detail.
- Explicit `AnimationController` only for signature moments; dispose controllers; physics springs for drag/fling.
- Respect `MediaQuery.disableAnimationsOf(context)` → `Duration.zero`.
- Haptics (`HapticFeedback.selectionClick/lightImpact`) on meaningful taps, not everywhere.
- Rive/Lottie only for signature moments; precache; test on a low-end device in profile mode.

## 6. Visual polish checklist
- [ ] Matches `design.md` direction; would not be mistaken for a sibling product or a library default
- [ ] Only semantic tokens/utilities; no hard-coded colours, sizes, radii, durations
- [ ] All states designed (hover/press/focus/disabled/loading/empty/error/success)
- [ ] Light + dark + every preset theme + a custom colour, en + sw (long strings), 320px → desktop / compact → expanded
- [ ] Theme state only via the generated controller (`useTheme` / `appThemeControllerProvider`)
- [ ] Alignment and spacing on the scale; consistent radius and icon sizes
- [ ] Motion uses tokens, transform/opacity, interruptible, reduced-motion safe
- [ ] Contrast and focus visible; touch targets large enough
- [ ] Images sized and optimised; no layout shift
