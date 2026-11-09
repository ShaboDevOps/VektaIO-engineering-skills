# Component spec template (one section per component in components.md)

```markdown
## <Component name>
Source: design-source/<file> (region / page / selector) · Screenshot: ![](design-source/components/<name>.png)

**Purpose** — when to use it, when not to.

**Anatomy** — parts in order (e.g. container → leading icon → label → trailing icon), with what is optional.

**Measurements** (exact, in px/dp at 1x)
| Property | Value | Token |
|---|---|---|
| Height | 48 | — |
| Padding (x / y) | 20 / 12 | space.lg / space.md |
| Gap icon–label | 8 | space.sm |
| Radius | 10 | radius.md |
| Border | 1px border | color.border |
| Shadow | none / sm | shadow.sm |
| Text style | 16 / 24, 600 | text.base + weight.semibold |
| Min width / touch target | 64 / 48 | — |

**Variants** — primary, secondary, ghost, destructive… (colours per variant as semantic tokens)

**Sizes** — sm / md / lg with the values that change

**States** (all variants) — default · hover · pressed · focus-visible (ring colour/width/offset) · disabled · loading · selected/active · error

**Behaviour** — what happens on tap/click, keyboard support, long-press, swipe, validation timing

**Motion** — property, duration token, easing token (e.g. background-color & transform, duration.fast, ease.standard; press scale 0.98)

**Content rules** — label length, truncation, Swahili length check, icon usage

**Accessibility** — role/semantics, labels, contrast checked, target size

**Implementation**
- Web: `shared/ui/<component>.tsx` — cva variants, tokens only
- Flutter: `ui/core/<component>.dart` — theme/AppColors/AppSpace tokens only
- Gallery/Storybook/Widgetbook entry + golden test

**Deviations from source** — none / what & why (also in fidelity.md)
```
