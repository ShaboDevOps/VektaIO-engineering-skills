# Extraction checklist

Tick every line or write "not in source → derived/omitted" with a reason. Record where each value came from.

## Colour
- [ ] Brand colours (primary, secondary, accent) — exact hex
- [ ] Neutrals: page background, surfaces (base, muted, raised, overlay), borders, dividers, input borders
- [ ] Text: primary, secondary/muted, disabled, inverse, link (default/visited/hover)
- [ ] Status: success, warning, danger/error, info — fill, text-on, subtle background, border
- [ ] Interactive states: hover, pressed, focus ring (colour, width, offset), selected, disabled overlay
- [ ] Gradients (angle, stops), overlays/scrims (colour + opacity), image tints
- [ ] Dark mode equivalents (or derived)
- [ ] Data-visualisation palette if charts exist
- [ ] Contrast of every text/background pair actually used

## Typography
- [ ] Families (heading, body, mono/numbers) + licence + fallbacks
- [ ] Every text style: size, weight, line height, letter spacing, case, font feature (tabular numbers)
- [ ] Map to roles: display, h1–h4, title, body-lg/md/sm, label, caption, overline, button, link, numbers/prices
- [ ] Paragraph spacing, max line length, truncation rules (1–2 lines + ellipsis?)
- [ ] Responsive changes per breakpoint

## Spacing & layout
- [ ] Base unit and spacing scale (all values used)
- [ ] Grid: columns, gutter, outer margin per breakpoint; container max-widths
- [ ] Breakpoints (web) / size classes (mobile) where layout changes
- [ ] Section spacing, card internal padding, list item height/padding, form field spacing
- [ ] Alignment rules: left edges, baselines, icon-to-text gap, centre vs start alignment
- [ ] Safe areas, sticky headers/footers, bottom bars, FAB positions

## Shape, depth, borders
- [ ] Radius scale and which components use which radius (including pill/full)
- [ ] Border widths and styles per component
- [ ] Elevation/shadow levels (offset, blur, spread, colour+opacity), which components use each
- [ ] Blur/backdrop effects, glass surfaces

## Iconography & imagery
- [ ] Icon set (name), style (outline/filled/duotone), stroke width, sizes, colour rules
- [ ] Illustration style; photo style (crop ratios, rounding, overlays); placeholder/empty-state art
- [ ] Logo usage (clear space, min size) — only for the user's own brand
- [ ] Avatars (shape, sizes, fallback initials style)

## Motion
- [ ] Durations used; easing curves; springs
- [ ] Hover/press feedback, page/route transitions, modal/sheet enter/exit, list stagger, skeleton/shimmer, loading indicators
- [ ] Reduced-motion behaviour

## Components (one spec each — see component-spec.md)
- [ ] Buttons (primary, secondary, tertiary/ghost, destructive, icon, link; sizes)
- [ ] Inputs: text, textarea, select/dropdown, search, OTP/code, phone with country, amount/currency, date, checkbox, radio, switch, slider, file/image upload
- [ ] Forms: labels, helper text, errors, required markers, field groups
- [ ] Cards (content, campaign/product, stat/KPI, list card), tiles
- [ ] Lists & tables (row, dividers, selection), list item variants
- [ ] Navigation: top app bar/header, bottom tab bar, side nav, tabs, segmented control, breadcrumbs, pagination, stepper
- [ ] Feedback: toast/snackbar, banner/alert, dialog/modal, bottom sheet, tooltip, popover, progress bar, spinner, skeleton
- [ ] Data display: badge/chip/tag (status chips), avatar, progress ring, stat, timeline, charts
- [ ] Empty, error, offline, permission states
- [ ] Media: carousel/gallery, image viewer, video
- [ ] Footer, hero/banner, CTA sections (web)

## Content & voice
- [ ] Tone, capitalisation (Sentence case?), button label style, number/currency/date formats
- [ ] Microcopy patterns (errors, empty states, confirmations)
