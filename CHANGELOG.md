# Changelog

## 2026-11-09 — vekta-design 1.2.0: design-extract
- New skill **design-extract**: extract a full design system from images, PDFs, Figma exports, websites or existing code; exact tokens; component/layout/asset specs; fidelity log; generates the project skill `.claude/skills/design-system/SKILL.md`
- Scripts: `extract_url_styles.py` (rendered styles from a live page + component crops), `extract_image_palette.py` (exact pixel colours, contrast, region sampling), `compare_screens.py` (pixel comparison of implementation vs source)
- vendor-skills.sh: skill folders (incl. scripts/references) copied into projects

## 2026-11-08 — runtime theming (vekta-design 1.1.0, vekta-web 1.2.0, vekta-mobile 1.2.0, vekta-api 1.1.0)
- tokens.json: `color.themes` presets (seed or explicit overrides), `color.defaultTheme.label`, `color.customColor`, `color.brandGroup`
- OKLCH colour engine: any colour → accessible primary for light + dark (Python reference; generated JS + Dart; JS verified identical on 314 colours)
- Web: theme.js + theme.d.ts (one controller: mode / preset / custom colour, persisted, follows OS in system mode), useTheme() hook, theme-init.js (no flash), theme CSS blocks
- Flutter: app_theme.dart (AppThemeController, appThemeProvider, ThemePreferenceStore, AppColorEngine), AppThemes presets, buildAppTheme(brightness, [colors])
- preview.html: live Mode / Theme / Any-colour switcher
- Skills: one-place theming rules, Appearance settings screen spec, `/api/v1/me/preferences` for cross-device sync

## 2026-11-08 — design identity
- New plugin **vekta-design 1.0.0**: `design-direction` (brief → 2–3 directions from 10 archetypes → design.md + tokens.json + preview, anti-sameness checklist) and `ui-craft` (UX patterns, polish checklist, motion system for React and Flutter)
- `build_tokens.py`: tokens.json → Tailwind 4 theme CSS + Flutter theme (palette, semantic ThemeExtension, spacing, radius, shadows, motion, typography, buildAppTheme) + HTML preview; WCAG contrast gate; `--check` for CI
- vekta-web 1.1.0 / vekta-mobile 1.1.0: UI must use the project's tokens; no hard-coded design values; restyle component libraries
- vekta-core 1.3.0: review-pr checks design fidelity
- Templates: design/ (or packages/design/) in web, mobile and monorepo projects; `just tokens`; CI check; design changes trigger web + mobile CI in monorepos

## vekta-core 1.2.0 — 2026-11-08
- Monorepo template (`add-to-project.sh monorepo`): apps/api + apps/web + apps/mobile with per-app CLAUDE.md and justfile, shared OpenAPI contract with generated TS/Dart clients, contract drift + breaking-change gate, path-aware CI with single `ci` check, per-app staging deploys (API first), per-app release-please versions and production deploys
- engineering-workflow: monorepo rules; ship: per-app CI and contract regeneration

## vekta-core 1.1.0 — 2026-11-08
- Branch model: feat/fix → develop (staging) → main → release tag → production; patch/* hotfixes into main with auto back-merge
- Pipeline skills: /vekta-core:start, /vekta-core:ship, /vekta-core:promote, /vekta-core:review-pr
- Agents: code-reviewer (independent, read-only), qa-tester (adds missing tests, runs suite)
- Hook: blocks pushes to develop/main, plain force-push, commits on protected branches, gh pr merge
- Project templates: CI per stack with release gates, branch-policy, Claude review (PASS/FAIL check), @claude, staging deploy, release-please + production deploy + back-merge, dependabot with cooldown, PR template, CODEOWNERS, justfiles
- scripts/setup-github.sh: develop branch, branch protection, environments, secrets check

## 1.0.0 — 2026-11-08
- vekta-core: engineering-workflow
- vekta-web: react-frontend-expert (React 19.3, TS 7, Vite 8, Next.js 16.4)
- vekta-api: python-backend-expert (Python 3.14, FastAPI, SQLAlchemy 2.1, PostgreSQL 18)
- vekta-mobile: flutter-mobile-expert (Flutter 3.47, Dart 3.13, Riverpod 3)
