---
name: engineering-workflow
description: Use when setting up or changing a repo, CI/CD pipeline, PR process, release flow, feature flags or ops practices for any React, Python or Flutter project.
---

# Engineering Workflow

How elite teams (Sentry, Grafana, Supabase, Cal.com, Polar, PostHog, Immich, Very Good Ventures) keep code quality high at scale: **every rule that matters is enforced by a machine**, changes are small and reviewed, releases are boring and reversible. Use this together with react-frontend-expert, python-backend-expert, flutter-mobile-expert, software-testing-expert and code-review-expert. Project-specific facts in the repo's `CLAUDE.md` override this skill.

## 1. Repository essentials

Every repo has:
```
README.md            # what it is, quick start (≤ 5 commands), architecture sketch, links
AGENTS.md            # commands, conventions, boundaries for AI agents (CLAUDE.md may point here)
CONTRIBUTING.md      # branching, commit style, PR process, how to run tests
SECURITY.md          # how to report vulnerabilities
.github/
  CODEOWNERS
  pull_request_template.md
  ISSUE_TEMPLATE/{bug.yml,feature.yml}
  dependabot.yml | renovate.json
  workflows/
docs/
  specs/<feature>/{design.md,decisions.md}   # lightweight design + decision log
  runbooks/                                  # one per alert / operation
.editorconfig  .gitignore  .env.example
justfile (or Makefile)                       # fixed command vocabulary
```
- **Standard commands** (same names in every repo): `just setup`, `just dev`, `just test`, `just lint`, `just typecheck`, `just format`, `just build`, `just seed`, `just gen` (codegen/clients/l10n), `just e2e`. CI calls the same commands.
- **Decision log**: any non-obvious choice (library, pattern, trade-off) gets a short entry — context, decision, consequences, date. Never relitigate without a new entry.
- **Local dev parity**: `docker compose up` brings up all dependencies; `.env.example` complete; seed data in English and Swahili.

### Monorepo (API + Web + Mobile in one repository)

Preferred for a product with a backend, web app and mobile app, so one change can update all three together.
```
apps/api  apps/web  apps/mobile     each with its own CLAUDE.md (names its skill), justfile, CHANGELOG
packages/contract/openapi.json       API contract exported from apps/api, committed
scripts/gen-clients.sh               regenerates the web TS types + mobile Dart client from the contract
justfile                             root; modules: just api::test, just web::dev, just mobile::ci
```
- **Per-app skills**: Claude reads the root `CLAUDE.md` plus the `CLAUDE.md` of the app it is working in, and applies only that app's stack skill there.
- **Contract first**: API change → `just gen` → web/mobile use the generated clients. CI fails if the contract or clients are stale, or if the contract has a breaking change vs the base branch.
- **No cross-app imports**; share only through `packages/contract`.
- **Commit scopes per app** (`feat(api):`, `fix(mobile):`); release-please versions each app separately from the files changed (`api-v1.4.0`, `web-v2.1.0`, `mobile-v1.8.0`) and deploys only released apps.
- **CI is path-aware**: PRs into `develop` check only affected apps; PRs into `main` check everything. A final `ci` job is the single required check.
- **Deploy order**: API first, then web and mobile, so new endpoints exist before clients use them.
- **Parallel work**: after the contract is done, web and mobile parts can go to separate subagents, each limited to its app folder and skill.

## 2. Branch model & Claude pipeline

```
feat/* ─┐                       (squash)            (merge commit)
fix/*  ─┴─► PR ─► develop ──► staging ──► PR ─► main ──► Release PR ─► tag vX.Y.Z ─► production
                    ▲                                │
                    └────── auto back-merge PR ◄─────┤
patch/* ──────────────────────────► PR ─► main ──────┘   (urgent production fixes)
```

| Branch | Created from | Merges into | Merge style | Meaning |
|---|---|---|---|---|
| `feat/<issue>-<slug>` | `develop` | `develop` | squash | new functionality |
| `fix/<issue>-<slug>` | `develop` | `develop` | squash | bug fix before production |
| `patch/<issue>-<slug>` | `main` | `main`, then auto back-merged to `develop` | squash | urgent production hotfix |
| `develop` | — | `main` | merge commit | integration + testing; auto-deploys to **staging** |
| `main` | — | — | — | production-ready; release-please opens the Release PR |
| release | tag `vX.Y.Z` on `main` | — | — | GitHub Release + **production** deploy (approval gate) |

**Who does what**

| Step | Claude (Claude Code, locally) | GitHub (automatic) | Human |
|---|---|---|---|
| Start | `/vekta-core:start feat <desc> [issue]` — branch from the right base, plan | — | approves the plan |
| Build | writes code following the stack skills | — | — |
| Ship | `/vekta-core:ship` — format, lint, types, tests; **qa-tester** agent adds missing tests; **code-reviewer** agent reviews; fixes; conventional commits; push; open PR | CI + branch policy + **Claude PR review** (inline comments + PASS/FAIL check) | reviews and **merges** to `develop` |
| Fix review comments | comment `@claude fix …` on the PR, or rerun `/vekta-core:ship` | Claude pushes fixes to the branch | re-reviews |
| Staging | — | deploy `develop` to staging | tests on staging |
| Promote | `/vekta-core:promote` — verify develop green + staging, release-readiness review, open `develop → main` PR with release notes (en + sw), risks, rollback | full CI + e2e + Claude **release review** | approves and **merges** |
| Release | — | release-please Release PR → tag → GitHub Release → production deploy waiting for approval | merges Release PR, approves production deploy |
| Hotfix | `/vekta-core:start patch …` then `/vekta-core:ship` | CI + Claude **hotfix review**; after merge, auto back-merge PR `main → develop` | merges |

**Guardrails** (enforced, not optional):
- The vekta-core hook blocks Claude from pushing to `develop`/`main`, plain `--force`, committing on protected branches and `gh pr merge`.
- Branch protection on `develop` and `main`: PRs only, required checks (`ci`, `branch-policy`, `claude-review`), ≥ 1 approval (2 for payments/auth/migrations and for `main`), CODEOWNER review, dismiss stale approvals, no force-push, no deletion.
- `branch-policy` workflow: `develop` accepts `feat/ fix/ chore/ docs/ refactor/ test/ deps/` and back-merges from `main`; `main` accepts only `develop`, `patch/*` and release-please PRs. PR titles must be Conventional Commits.
- `production` environment requires a human approval before deploying.

**Conventions**
- Short-lived branches (≤ 2–3 days); **small PRs** (aim ≤ 400 hand-written lines); split refactors from behaviour changes; large features land behind flags.
- **Conventional Commits** (`feat:`, `fix:`, `perf:`, `refactor:`, `docs:`, `test:`, `chore:`, `feat!:`/`BREAKING CHANGE:`). PR title = squash commit on `develop`, so it is validated.
- `develop → main` and back-merges use **merge commits** so release-please sees every conventional commit.
- **CODEOWNERS** maps every path to an owner; CI checks that new paths have owners.

## 3. PR template

```markdown
## What & why
<!-- One paragraph. Link the issue/spec. -->

## How to test
<!-- Steps a reviewer can follow; test accounts/seed data. -->

## Screenshots / recordings
<!-- Before / after for UI (mobile + desktop, en + sw). -->

## Checklist
- [ ] Self-reviewed the diff
- [ ] Tests added/updated (unit / integration / e2e as relevant)
- [ ] No breaking API change, or versioned + deprecation headers
- [ ] Migrations backward compatible (expand → migrate → contract)
- [ ] Strings translated (en + sw)
- [ ] Security considered (authz, input validation, secrets, PII)
- [ ] Feature flag for risky changes
- [ ] Docs / runbook / decision log updated
```

## 4. CI pipeline (GitHub Actions)

Run on every PR; fail fast, cache aggressively, parallelize. Stages:

| Stage | React | Python | Flutter |
|---|---|---|---|
| Install (locked) | `pnpm install --frozen-lockfile` | `uv sync --locked` | `flutter pub get --enforce-lockfile` |
| Format | `prettier --check` | `ruff format --check` | `dart format --set-exit-if-changed .` |
| Lint | `eslint` (boundaries, a11y, hooks) | `ruff check`, import-linter, custom lints | `flutter analyze` + custom lints |
| Types | `tsc --noEmit` | `mypy --strict -n auto` | (analyzer) |
| Dead code / deps | `knip` | `deptry` | `dart pub outdated` report |
| Codegen check | generated API client up to date | OpenAPI snapshot up to date | `build_runner`/`gen-l10n` output committed & unchanged |
| i18n | missing/unused keys | `.po` untranslated = 0 | `untranslated-messages-file` empty |
| Unit + integration | `vitest --coverage` | `pytest -n auto --cov --cov-fail-under=85` | `flutter test --coverage --test-randomize-ordering-seed random` |
| Special checks | size-limit PR comment, Storybook a11y + visual snapshots | `check_migrations`, contract tests per API version | drift `SchemaVerifier`, goldens, permissions/manifest baseline diff |
| Build | `vite build` / `next build` | Docker image | `flutter build appbundle/ipa` per flavor (on main/release) |
| E2E | Playwright on preview deploy | API smoke tests on preview | patrol on emulator (nightly or on label) |

- **Coverage floors** (e.g. 85% backend, 80% frontend/mobile on changed code) — raise over time, never lower.
- **Ratchets for legacy code**: when adopting a strict rule on an existing codebase, record the current violation count; CI fails if it goes up; a scheduled job lowers the baseline as fixes land. Same for mypy strict module lists.
- **Flaky tests** are quarantined with an issue and owner within 24h, never ignored.
- Required checks must finish in < 10 minutes for PRs; heavier suites run nightly.

## 5. CI & supply-chain security

- Workflows start with `permissions: {}` and grant per job (least privilege).
- Pin every third-party action to a **full commit SHA** (with version comment); Dependabot/Renovate updates them.
- Never run untrusted PR code with `pull_request_target` or secrets; use OIDC to cloud providers instead of long-lived keys.
- Lint workflows with **zizmor**; scan for secrets with **gitleaks/trufflehog** (pre-commit + CI); enable GitHub secret scanning + push protection.
- **Dependency review** on PRs (new vulns, licence check against an allowlist — MIT/BSD/Apache/ISC; block GPL/AGPL for closed apps).
- Dependabot/Renovate with a **cooldown** (≥ 3–7 days before adopting new releases), grouped minor/patch updates, auto-merge only for passing patch updates of dev tooling.
- Package-manager cooldowns: pnpm `minimumReleaseAge`, uv `exclude-newer`; lockfiles always committed.
- Containers: minimal base, non-root, scanned (Trivy/Grype); generate an **SBOM** (Syft) per release.
- CodeQL (or Semgrep) SAST on PRs.

## 6. Environments & deployments

- **Preview deployment per PR** (frontend + API with seeded DB where feasible), torn down on merge; link posted to the PR.
- Environments: local → **staging** (auto-deploy from `develop`) → **production** (deploy from release tags on `main`, approval required); the **same immutable artifact** is promoted; config via env/secret manager.
- Production deploys: automated from tags/release PR, rolling/blue-green with health checks, canary for risky changes, automatic rollback on failed health/SLO burn.
- **Fast revert**: a revert PR can be created and merged with one action; reverting beats debugging in production.
- Mobile: CI builds per flavor, uploads to Play internal/TestFlight, staged rollout gates on crash-free rate.

## 7. Releases & versioning

- SemVer for apps, services, packages; Conventional Commits → **release-please** (or Changesets in JS monorepos) creates the release PR, changelog and tags.
- Every artifact knows its version + git SHA (exposed via `/version`, About screen, Sentry release).
- Release notes for users in English and Swahili.
- Public APIs/packages: deprecation policy (announce → warn → remove after N months); CI detects breaking changes in exported packages/OpenAPI (e.g. `oasdiff` for OpenAPI).

## 8. Feature flags

- OpenFeature SDKs + one provider (Unleash, Flagsmith, GrowthBook or PostHog) across web, API and mobile.
- **Typed flag registry** in code: name (`team.feature-name`), owner, description, type, default, created, expected removal date, stage (`experimental` → `beta` → `ga` → `removed`).
- Defaults are safe (off); flags evaluated server-side for security-relevant behaviour.
- CI reports flags past their removal date; removing a GA flag is part of the feature's definition of done.

## 9. Analytics

- One **event registry** per product shared by web and mobile: `object_action` snake_case names (`order_created`, `payment_failed`), typed properties, owner, description.
- No PII in events; consent respected; analytics behind an interface with no-op (dev/demo) and recording (tests) implementations.
- CI generates an events report so product and engineering agree on what's tracked.

## 10. Observability & operations

- **SLOs** for critical user journeys (login, payment, sync) with error budgets; when the budget is burned, reliability work outranks features.
- Alerts on symptoms (error rate, latency, queue age, crash-free rate), routed to an on-call owner; every alert links to a **runbook**.
- Dashboards: RED metrics per service, DB/Redis health, queue depth, mobile crash-free and ANR rates, Core Web Vitals.
- **Incidents**: declare, mitigate (revert/flag off first), communicate, then a blameless postmortem within 5 days with action items tracked.
- Backups with point-in-time recovery; restore drill quarterly; documented RPO/RTO.
- Data protection (Tanzania PDPA): data inventory, retention schedule, breach-notification procedure, DPO contact in SECURITY.md/privacy policy.

## 11. Documentation

- Docs live next to code and are updated in the same PR.
- Architecture overview (one diagram + module map) in README or `docs/architecture.md`; module dependency graph regenerated in CI for monorepos.
- API: OpenAPI per version with examples, published to frontend/mobile teams.
- Onboarding test: a new developer runs the app locally in < 30 minutes using only the README.

## 12. Definition of done (workflow)

- [ ] PR small, focused, titled as a Conventional Commit, template completed
- [ ] All required CI checks green (format, lint, types, tests, coverage, special checks)
- [ ] CODEOWNER approval (2 reviewers for payments/auth/migrations)
- [ ] No new secrets, vulnerable or disallowed-licence dependencies
- [ ] Preview deployment verified for UI/API changes
- [ ] Flag, changelog, docs, runbook and decision log updated as needed
- [ ] Rollback path known
