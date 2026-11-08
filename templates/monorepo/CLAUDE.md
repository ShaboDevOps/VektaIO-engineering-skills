# <Product name> — monorepo (API + Web + Mobile)

One repository, three apps, one API contract. Each app has its own `CLAUDE.md` with its skill and commands — **read the app's `CLAUDE.md` before changing anything inside it.** Facts in these files override the shared skills.

## Layout

```
apps/
  api/        FastAPI backend        → skill: vekta-api:python-backend-expert   (apps/api/CLAUDE.md)
  web/        React web app          → skill: vekta-web:react-frontend-expert   (apps/web/CLAUDE.md)
  mobile/     Flutter app            → skill: vekta-mobile:flutter-mobile-expert (apps/mobile/CLAUDE.md)
packages/
  contract/   openapi.json — the API contract, exported from apps/api, committed
  design/     design.md + tokens.json — this product's own look; `just tokens` → web tokens.css + mobile app_tokens.dart
scripts/      gen-clients.sh, check-contract.sh
docker-compose.yml   local Postgres, Redis, MinIO, Mailpit
justfile             root commands; per-app commands via modules (just api::test, just web::dev, just mobile::test)
```
Always applies: `vekta-core:engineering-workflow` (branches, PRs, CI, releases).

## Rules for working across apps

1. **Contract first.** A feature that changes the API starts in `apps/api`: schemas + endpoint + tests → `just gen` (exports `packages/contract/openapi.json` and regenerates the web TypeScript client and the mobile Dart client). Web and mobile code only use the generated clients — never hand-written request/response types.
2. **Never break deployed clients.** Mobile apps in users' hands stay old for months: API changes are additive or versioned (`/api/v2`) with deprecation headers. CI runs a breaking-change check on the contract.
3. **One feature, one branch.** A cross-app feature (API + web + mobile) goes in one `feat/*` branch. Use commit scopes per app: `feat(api): …`, `feat(web): …`, `feat(mobile): …` — releases are computed per app from the files changed.
4. **Stay in your lane.** When working inside `apps/<x>`, follow only that app's skill and commands. Don't import code across apps; share only through `packages/contract`.
5. **Parallel work.** For a large cross-app feature, after the contract is done you may delegate the web and mobile parts to separate subagents — each told to work only inside its app folder, follow its `CLAUDE.md` and skill, and run its own `just <app>::ci`.
6. **One design identity for web and mobile.** Both apps use the tokens generated from `packages/design/tokens.json` and follow `packages/design/design.md` (create/change with `/vekta-design:design-direction`; build UI with `vekta-design:ui-craft`). Never hard-code colours, sizes or durations, never hand-edit generated token files.
7. **Shared conventions:** English + Swahili everywhere (same error `code`s mapped to translations in web and mobile), money as integer TZS, UTC timestamps, E.164 phone numbers.

## Pipeline (Claude does everything up to the PR; humans merge)
- `/vekta-core:start feat|fix|patch <description> [issue]`
- `/vekta-core:ship` — runs `just ci` for every app the branch touched, tests, review, commit, push, PR
- `/vekta-core:promote` — release candidate PR `develop → main`
- `/vekta-core:review-pr <number>`; on GitHub comment `@claude <request>`

## Commands (root)
- `just setup` — install everything · `just up` / `just down` — local services
- `just dev-api` · `just dev-web` · `just dev-mobile`
- `just gen` — export contract + regenerate clients · `just tokens` — regenerate design tokens
- `just ci` — CI for all apps · `just api::ci` / `just web::ci` / `just mobile::ci` for one
- `just changed` — which apps this branch touched

## Releases
Each app is versioned and released on its own (`api-v1.4.0`, `web-v2.1.0`, `mobile-v1.8.0`). Merging the Release PR deploys only the apps that got a new version.

## Project specifics (edit me)
- Product: <one sentence>
- Default locale: sw (fallback en)
- Payments: <provider, e.g. Snippe> — idempotency keys on all payment endpoints
- Hosting: API <host>, Web <host>, Mobile: Google Play + App Store
- Deviations from the skills: <none>
