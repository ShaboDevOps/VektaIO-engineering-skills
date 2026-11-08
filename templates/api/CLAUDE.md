# <Project name> — Backend API

## Skills to follow
This project uses the VektaIO shared skills (enabled in `.claude/settings.json`):
- `vekta-core:engineering-workflow`
- `vekta-api:python-backend-expert`

Facts in THIS file override the skills when they conflict.

## Project specifics (edit me)
- Product: <one sentence: what it does and for whom>
- Default locale: sw (fallback en)
- Payments: <e.g. Snippe mobile money> — all payment endpoints need idempotency keys
- Multi-tenant: <yes/no>
- Deviations from the skills: <e.g. "uses Bloc, not Riverpod" — or "none">

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
