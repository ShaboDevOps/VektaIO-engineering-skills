---
name: promote
description: Prepare a release candidate — verify develop is fully tested and working, review everything since the last release, and open the develop → main pull request. Never merges.
disable-model-invocation: true
argument-hint: [notes]
---

# Promote develop → main (release candidate)

Merging into `main` means "ready for production". Your job is to prove that with evidence, then open the PR. **A human merges.**

## 1. Gather the change set

```
git fetch origin --prune
git log --oneline --no-merges origin/main..origin/develop
git diff --stat origin/main...origin/develop
```
If there is nothing to promote, stop.

## 2. Verify develop is green and deployed

- `gh run list --branch develop --limit 5` — the latest CI run on `develop` HEAD must be successful. If not, stop and report.
- Confirm the latest `develop` is deployed to **staging** (`gh run list --workflow deploy-staging.yml --limit 3`).
- Run the end-to-end / smoke suite against staging if the project has one (`just e2e` or as documented in `CLAUDE.md`). Report results.

## 3. Release-readiness review (code-reviewer agent)

Delegate to the **code-reviewer** agent in *release mode* with base `origin/main` and head `origin/develop`. Ask it to focus on:
- breaking API changes (removed/renamed fields or endpoints, changed error codes) — must be versioned with deprecation headers
- database migrations — backward compatible (expand → migrate → contract), reversible, safe on large tables
- security regressions (authz, secrets, input validation, dependency changes)
- configuration: new env vars/secrets/feature flags that production needs
- mobile: minimum app version / forced-update implications
- missing tests for risky changes; anything half-finished not behind a flag

Any **blocking** finding → do not open a ready PR. Open it as **draft**, list the blockers, and suggest `fix/` branches.

## 4. Open the PR

```
gh pr create --base main --head develop --title "release: promote develop to main ($(date +%Y-%m-%d))" --body-file <file>
```
Body:
- **Changes**: features, fixes, perf, breaking changes (grouped from conventional commits, with PR links)
- **Draft release notes** for users in English and Swahili
- **Verification evidence**: CI run link, staging deploy, e2e/smoke results
- **Migrations & config**: list, order of operations, new env vars/flags to set before deploy
- **Risk assessment** (low/medium/high per area) and **rollback plan** (previous tag, flag switches, migration safety)
- **Review summary** from the code-reviewer
- Checklist: all CI green · staging verified · migrations safe · release notes ready · rollback known

Use a **merge commit** (not squash) for this PR so release-please sees each conventional commit.

## 5. After a human merges

Merging to `main` triggers the release workflow: release-please opens/updates a **Release PR** (version bump + CHANGELOG). Merging that Release PR tags `vX.Y.Z`, publishes the GitHub Release and starts the production deploy (which waits for approval in the `production` environment). Tell the user these next steps and stop.
