# <Project name> — Web frontend

## Skills to follow
This project uses the VektaIO shared skills (enabled in `.claude/settings.json`):
- `vekta-core:engineering-workflow`
- `vekta-design:design-direction` and `vekta-design:ui-craft`
- `vekta-web:react-frontend-expert`

Facts in THIS file override the skills when they conflict.

## Project specifics (edit me)
- Product: <one sentence: what it does and for whom>
- Default locale: sw (fallback en)
- Framework: <Vite SPA | Next.js>
- API base URL: <https://api.example.co.tz/api/v1>
- Deviations from the skills: <e.g. "uses Bloc, not Riverpod" — or "none">

## Design (unique to this product)
- Direction: `design/design.md` · tokens: `design/tokens.json` · preview: `design/preview.html`
- Create/change with `/vekta-design:design-direction`; build UI with `vekta-design:ui-craft`.
- `just tokens` regenerates the theme; never hand-edit generated token files or hard-code colours/sizes/durations.

## Pipeline (Claude does everything up to the PR; humans merge)
- `/vekta-core:start feat|fix|patch <description> [issue]` — branch from develop (feat/fix) or main (patch) and plan
- `/vekta-core:ship` — checks, tests (qa-tester), review (code-reviewer), commit, push, open PR
- `/vekta-core:promote` — release candidate PR develop → main
- `/vekta-core:review-pr <number>` — review any PR
- On GitHub: comment `@claude <request>` on a PR or issue

## Commands
- `just setup` — install dependencies
- `just dev` — run locally
- `just test` / `just lint` / `just typecheck`
- `just gen` — code generation (clients, l10n, models)

## Boundaries
- Never commit secrets; use `.env` (see `.env.example`).
- Ask before changing database migrations that are already released.
