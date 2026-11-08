---
name: ship
description: Finish the current feat/fix/patch branch — run all checks, test, independently review, fix, commit, push and open the pull request. Never merges.
disable-model-invocation: true
argument-hint: [--draft] [extra notes for the PR]
---

# Ship the current branch

Arguments: `$ARGUMENTS` (optional `--draft` and notes for the PR description).

The goal: the PR you open should pass CI and human review the first time. You do everything up to the PR; **a human merges**. Never run `gh pr merge`, never push to `develop` or `main`.

## 1. Check the branch

- `git rev-parse --abbrev-ref HEAD` must start with `feat/`, `fix/` or `patch/`. On `develop`/`main`/anything else: stop and tell the user to run `/vekta-core:start`.
- Base branch: `develop` for `feat/` and `fix/`; `main` for `patch/`.

## 2. Sync with the base

```
git fetch origin --prune
git rebase origin/<base>
```
Resolve conflicts carefully (keep both sides' intent; re-run tests). If a conflict is ambiguous, stop and ask.

## 3. Quality gates (fix, don't bypass)

Run the project's commands (from `CLAUDE.md`/`justfile`): `just format`, `just lint`, `just typecheck`, `just test`.
**Monorepo** (`apps/` folder exists): run `just changed` to see which apps the branch touched, then `just <app>::ci` for each of them. If `apps/api` or `packages/contract` changed, run `just gen` and commit the regenerated contract and clients, then `./scripts/check-contract.sh`. Use one commit scope per app (`feat(api): …`, `feat(web): …`).
- Fix every failure at the root cause.
- **Never** skip, delete or weaken tests, add blanket ignores (`# type: ignore`, `eslint-disable`, `// ignore:`), or lower coverage thresholds to get green.
- If a check can't pass for a reason outside this change, stop and report it.

## 4. Testing pass (qa-tester agent)

Delegate to the **qa-tester** agent with: the base branch, the goal/acceptance criteria, and the changed files. It adds missing tests for new/changed behaviour, runs the full suite and reports. Re-run `just test` yourself afterwards and confirm green.

## 5. Independent review (code-reviewer agent)

Delegate to the **code-reviewer** agent with only: the base branch and the goal — not your reasoning, so the review isn't anchored on it. It returns findings tagged **blocking / should-fix / nit**.
- Fix all **blocking** and **should-fix** findings (or write down why one is wrong).
- Re-run section 3 gates, then ask the reviewer to re-check the changed areas.
- Maximum 3 review rounds. If blocking findings remain, open the PR as **draft** and list them.

## 6. Commit

- Conventional Commits: `feat(scope): …`, `fix(scope): …`, `feat!:` / `BREAKING CHANGE:` footer for breaking changes. Imperative, ≤ 72-char subject, body explains why.
- Small logical commits; no generated noise mixed with hand-written changes.
- Before committing, scan the diff for secrets, `.env` files, debug prints, large binaries. Remove them.

## 7. Push

`git push -u origin HEAD` (after a rebase of an already-pushed branch: `git push --force-with-lease`). Never plain `--force`.

## 8. Open the pull request

```
gh pr create --base <base> --title "<conventional title>" --body-file <file> [--draft]
```
The title becomes the squash commit on `develop`, so it must be a valid Conventional Commit. Fill the body from `.github/pull_request_template.md`:
- What & why (link issue: `Closes #<n>`)
- How to test (steps, seed data, accounts)
- Test evidence: commands run and results, coverage change
- Review summary: what the code-reviewer found and how it was fixed
- Screenshots: note which UI states need screenshots (mobile + desktop, en + sw) if you can't capture them
- Checklist ticked honestly; risks and rollback

For `patch/` PRs also state the production impact and that `main` will be back-merged into `develop` automatically.

## 9. Report

Give the user: PR link, gate results, review rounds and remaining concerns, and what the human reviewer should look at most closely. Then stop — merging is a human decision.
