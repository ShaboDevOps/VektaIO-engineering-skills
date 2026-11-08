---
name: start
description: Start new work on the correct branch — a feature, a bug fix, or an urgent production patch — and agree a plan before coding.
disable-model-invocation: true
argument-hint: <feat|fix|patch> <short description> [issue-number]
---

# Start work

Arguments: `$ARGUMENTS` — first word is the type (`feat`, `fix`, `patch`), the rest is a short description, optionally an issue number.

## Branch model (VektaIO)

| Type | Branch from | Branch name | PR into | Use for |
|---|---|---|---|---|
| `feat` | `develop` | `feat/<issue>-<slug>` | `develop` | New functionality |
| `fix` | `develop` | `fix/<issue>-<slug>` | `develop` | Bugs found before production |
| `patch` | `main` | `patch/<issue>-<slug>` | `main` (auto back-merged to `develop`) | Urgent production bugs only |

`<slug>`: lowercase, hyphenated, ≤ 5 words. Omit `<issue>-` if there is no issue.

## Steps

1. **Check the type.** If it isn't `feat`, `fix` or `patch`, stop and ask. If `patch` is requested for something that isn't an urgent production bug, suggest `fix` instead.
2. **Clean tree.** Run `git status --porcelain`. If there are uncommitted changes, stop and ask whether to stash, commit or discard them — never discard on your own.
3. **Sync.** `git fetch origin --prune`.
4. **Create the branch** from the up-to-date remote base:
   `git switch -c <type>/<issue>-<slug> origin/<base>`
5. **Load context.** Read `CLAUDE.md`, and follow the stack skills it lists (react-frontend-expert, python-backend-expert, flutter-mobile-expert) plus engineering-workflow. If an issue number was given, read it with `gh issue view <n>`.
6. **Plan.** Explore the relevant code, then write a short plan:
   - goal and acceptance criteria (what "working" means)
   - files/modules to change, and anything reused
   - tests to add (unit / integration / e2e)
   - risks: API compatibility, migrations, security, i18n (en + sw), performance
   For larger features also create `docs/specs/<slug>/design.md`.
7. **Confirm.** Show the plan and wait for the user's go-ahead before writing code.
8. After coding, the user (or you, when asked) runs `/vekta-core:ship` to test, review, push and open the PR.
