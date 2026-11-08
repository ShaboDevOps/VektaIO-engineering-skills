# <Product> — design direction

> Replace this file by running `/vekta-design:design-direction`. Every product gets its own direction — never copy another product's.

## 1. Direction
- **Name**: <e.g. "Sunlit Savanna">
- **In one sentence**: <what it should feel like>
- **Personality (3 words)**: <e.g. warm · trustworthy · lively>
- **Audience & context**: <who, devices, light conditions, literacy/tech comfort, languages (sw/en)>
- **Differs from our other products by**: <hue family, typography, shape, motion, signature element>

## 2. Principles (3–5)
1. <e.g. "Clarity before decoration — farmers read this in sunlight on low-end phones">

## 3. Colour
- Primary <hex> — used for: main actions, active states. Never for: large backgrounds.
- Accent <hex> — used for: highlights, promotions, badges (sparingly, ≤ 10% of a screen).
- Neutrals: <warm | cool | true grey>. Status colours: success / warning / danger / info.
- Light and dark mode both designed; contrast enforced by `just tokens`.

## 4. Typography
- Headings: <font> — why. Body: <font> — why. Numbers/data: <tabular figures / mono>.
- Scale and line heights from tokens; max line length ~70 characters; Swahili text is often longer — allow 30–40% expansion.

## 5. Shape, depth & texture
- Radius: <sharp | soft | round | pill> (`radius.*`). Borders vs shadows: <which carries hierarchy>.
- Texture / signature element: <e.g. subtle grain, wave divider, stamp badges, duotone icons>.

## 6. Layout & density
- Density: <compact | comfortable | spacious>. Grid / max widths. Mobile-first; key actions within thumb reach.

## 7. Iconography & imagery
- Icon set: <Lucide outline | Phosphor duotone | Tabler | custom>, stroke width, size scale.
- Photography / illustration style: <real local people & animals, warm light | flat illustrations | none>. Alt text in en + sw.

## 8. Motion
- Character: <calm & smooth | snappy & precise | playful & springy | elegant & slow>.
- Durations: instant/fast/base/slow/page from tokens; easings `standard` (most UI), `enter`, `exit`, `emphasized` (key moments only).
- Signature moments: <e.g. listing card lifts and image zooms on press; success check draws in; pull-to-refresh with brand mark>.
- Reduced motion: everything degrades to fades or no animation.

## 9. Voice & microcopy
- Tone: <friendly, direct, respectful>. Swahili first where the audience is local; same meaning in both languages, not literal translation.
- Buttons are verbs ("Nunua sasa" / "Buy now"); errors say what happened and what to do.

## 10. Do / Don't
- Do: <…>
- Don't: <e.g. use stock component-library look, gradients on text, more than one accent per screen>

## 11. References
- <links or screenshots that inspired this direction, and what to take from each>
