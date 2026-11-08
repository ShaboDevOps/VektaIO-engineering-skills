# VektaIO Engineering Skills

Shared Claude skills that encode VektaIO's production standards. One repo, used by every project and every team member.

| Plugin | Skills | Use in |
|---|---|---|
| `vekta-core` | `engineering-workflow`, pipeline skills `start` · `ship` · `promote` · `review-pr`, agents `code-reviewer` · `qa-tester`, git guard hook (+ `software-testing-expert`, `code-review-expert` coming) | **Every** project |
| `vekta-web` | `react-frontend-expert` | React / Next.js web apps |
| `vekta-api` | `python-backend-expert` | FastAPI backends |
| `vekta-mobile` | `flutter-mobile-expert` | Flutter apps |
| `vekta-design` | `design-direction`, `ui-craft` | Every project with a UI (web, mobile, monorepo) |

## 1. Publish this repo (once)

1. This repo lives at `ShaboDevOps/VektaIO-engineering-skills` (public, so projects and the Claude GitHub App can read it).
   If you use a different org/repo name, update `templates/*/.claude/settings.json`.
2. Teammates need read access to the repo and working git credentials (`gh auth login`).

## 2. Add skills to a project

From the project root:

```bash
# pick one: web | api | mobile | monorepo
curl -fsSL https://raw.githubusercontent.com/ShaboDevOps/VektaIO-engineering-skills/main/scripts/add-to-project.sh | bash -s -- api
# or, with this repo cloned locally:
~/code/engineering-skills/scripts/add-to-project.sh api
```

This copies two files into the project:

- `.claude/settings.json` — registers the marketplace and enables the right plugins
- `CLAUDE.md` — project-specific facts (edit the `<placeholders>`)

Commit both. Every teammate who opens the project in Claude Code and trusts the folder gets the same skills automatically.

**Different project, different skills:** edit `enabledPlugins` in `.claude/settings.json`, e.g. a backend-only service enables just `vekta-core` + `vekta-api`. A project on another stack (e.g. NestJS) enables only `vekta-core` and states its stack in `CLAUDE.md`.

### One repo for API + Web + Mobile (monorepo)

```bash
mkdir soko-la-mifugo && cd soko-la-mifugo && git init
~/code/engineering-skills/scripts/add-to-project.sh monorepo
```
You get `apps/api`, `apps/web`, `apps/mobile` (each with its own `CLAUDE.md` naming its skill and a `justfile`), `packages/contract/openapi.json` (the shared API contract), `docker-compose.yml`, a root `justfile` (`just api::test`, `just web::dev`, `just gen`, `just ci`), path-aware CI with one required `ci` check, and per-app releases (`api-v…`, `web-v…`, `mobile-v…`). Then ask Claude: *"Scaffold apps/api, apps/web and apps/mobile following their skills."*

Claude works on all three at once: it reads the root `CLAUDE.md` plus the app's own `CLAUDE.md`, changes the API contract first, regenerates the web and mobile clients with `just gen`, then updates each app with its own skill — in one feature branch and one PR.

## Give every product its own look (design tokens)

Every web/mobile/monorepo project gets a `design/` folder (`packages/design/` in a monorepo):

| File | What it is |
|---|---|
| `design.md` | the direction: personality, colour/type/shape/motion rules, voice (en + sw), do/don't |
| `tokens.json` | design tokens (W3C DTCG-style): palette, light + dark semantic colours, fonts, type scale, spacing, radius, shadows, motion durations + easings |
| `preview.html` | generated preview — open it in a browser (light/dark toggle, motion demo) |

1. In Claude Code run **`/vekta-design:design-direction`** and give it whatever you have: a Figma/Tokens Studio export, brand colours or logo, reference apps/sites/screenshots, or just three mood words. Claude proposes 2–3 distinct directions (from 10 archetypes such as *Grounded & Earthy*, *Clinical Calm*, *Ocean & Tide*, *Market Bold*, *Night Signal*), checks it differs from your other products, then writes `design.md` + `tokens.json`.
2. `just tokens` generates the **Tailwind 4 theme** (`tokens.css`) and the **Flutter theme** (`app_tokens.dart` with `buildAppTheme()`), and fails if any text/background pair is below WCAG contrast.
3. The React and Flutter skills only use these tokens (no hard-coded colours, sizes or durations), restyle the component library to the direction, and follow `vekta-design:ui-craft` for UX and motion. CI runs `just tokens --check`; Claude's PR review checks design fidelity.

Change the look later by editing the tokens (or re-running the skill) and `just tokens` — web and mobile update together.

### Theme switching for users — one place

Each app gets one generated theme controller, so users can choose **System / Light / Dark**, a **preset colour theme** (defined in `tokens.json` → `color.themes`), or **any colour** they like:

| | Web | Flutter |
|---|---|---|
| Controller | `src/shared/theme/theme.js` + `useTheme()` hook | `lib/app/theme/app_theme.dart` → `appThemeControllerProvider` |
| Apply | `theme-init.js` in `<head>` + `initTheme()` in `main.tsx` | `MaterialApp(theme/darkTheme/themeMode from appThemeProvider)` |
| Save | browser storage (+ optional `PATCH /api/v1/me/preferences`) | your `ThemePreferenceStore` (+ optional profile API) |

Any colour a user picks is passed through the same OKLCH colour engine as the presets (Python at build time, JavaScript and Dart at runtime): it keeps their exact colour when it's readable and otherwise picks the nearest readable shade of the same hue, separately for light and dark. Every preset is contrast-checked at build time.

## 3. The Claude development pipeline

```
feat/* ─┐                       (squash)            (merge commit)
fix/*  ─┴─► PR ─► develop ──► staging ──► PR ─► main ──► Release PR ─► tag vX.Y.Z ─► production
                    ▲                                │
                    └────── auto back-merge PR ◄─────┤
patch/* ──────────────────────────► PR ─► main ──────┘   (urgent production fixes)
```

| Step | You type (Claude Code) | Claude does | GitHub does automatically | Human |
|---|---|---|---|---|
| 1. Start | `/vekta-core:start feat add order cancel 42` | branches `feat/42-add-order-cancel` from `develop`, plans | — | approve plan |
| 2. Build | "implement it" | codes using the stack skills | — | — |
| 3. Ship | `/vekta-core:ship` | format, lint, types, tests → **qa-tester** adds missing tests → **code-reviewer** reviews → fixes → commits → pushes → opens PR | CI, branch policy, **Claude review** (inline comments + PASS/FAIL check) | review & **merge** to develop |
| 4. Fix feedback | comment `@claude fix the review comments` | pushes fixes to the branch | re-runs checks | re-review |
| 5. Staging | — | — | deploys `develop` to staging | test on staging |
| 6. Promote | `/vekta-core:promote` | verifies develop + staging, release-readiness review, opens `develop → main` PR with release notes (en + sw), risks, rollback | full CI + release gates (e2e / migrations + contract / prod build) + Claude **release review** | approve & **merge** |
| 7. Release | — | — | release-please opens Release PR → merge tags `vX.Y.Z` → GitHub Release → production deploy | merge Release PR, **approve production deploy** |
| Hotfix | `/vekta-core:start patch fix payment timeout` then `/vekta-core:ship` | same as ship, PR into `main` | CI + Claude hotfix review; after release, auto back-merge PR `main → develop` | merge |

**Safety rails:** a hook stops Claude from pushing to `develop`/`main`, force-pushing, committing on protected branches or merging PRs. Branch protection, the `branch-policy` check and the production approval gate enforce the same rules for everyone.

### Set up a project's pipeline (once per repo)

```bash
./scripts/add-to-project.sh api          # or monorepo; adds .claude/, CLAUDE.md, .github/ workflows, justfile, release-please
git checkout -b chore/pipeline && git add -A && git commit -m "chore: add VektaIO pipeline" && git push -u origin HEAD
# merge that PR into main, then:
./scripts/setup-github.sh api            # develop branch, protection, environments, checks
claude setup-token                       # copy the token, then:
gh secret set CLAUDE_CODE_OAUTH_TOKEN    # paste it
```
Then in Claude Code run `/install-github-app` (installs the Claude GitHub App), and optionally add a `RELEASE_PLEASE_TOKEN` secret (fine-grained PAT with contents + pull requests write) so CI runs on Release and back-merge PRs.

Requirements and notes:
- The Claude GitHub App must be able to read this skills repo, or make this repo public (it holds standards, no secrets).
- Branch protection and production approvals on **private** repos need a paid GitHub plan.
- GitHub doesn't let authors approve their own PRs — solo developers need a teammate reviewer (or `APPROVALS_DEVELOP=0`).
- Fill the `deploy` recipes in `justfile` (and the cloud login step in the deploy workflows) for your hosting.

## 4. Use the skills

Claude picks the right skill automatically from the task. To force one:

```
/vekta-api:python-backend-expert build the orders module
```

Install manually (without project settings):

```
/plugin marketplace add ShaboDevOps/VektaIO-engineering-skills
/plugin install vekta-api@vektaio-skills
```

## 5. Update the skills

1. Edit a `SKILL.md`, bump `version` in that plugin's `.claude-plugin/plugin.json`, add a line to `CHANGELOG.md`.
2. Open a PR — CI validates the structure. Merge.
3. Projects have `autoUpdate: true`; teammates can also run `/plugin marketplace update vektaio-skills` then `/reload-plugins`.

## 6. Claude app (Cowork / claude.ai)

The same plugins can be added in the Claude app from a GitHub repo (connect GitHub and grant access). On Team/Enterprise plans an Owner can make them installed-by-default or required for the whole organization.

## Rules for changing skills

- Skills describe defaults; project `CLAUDE.md` holds project facts and deviations.
- Keep the version baseline in each skill current — re-verify against official docs every quarter.
- Anything that can be enforced by a tool (lint, CI) should be — the skill says so and the project config does it.
