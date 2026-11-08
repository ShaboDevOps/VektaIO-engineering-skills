---
name: review-pr
description: Review a GitHub pull request against VektaIO standards and post inline comments plus a verdict. Used locally and by the Claude review GitHub Action.
disable-model-invocation: true
argument-hint: <owner/repo/pull/number | number> [--ci]
---

# Review a pull request

Arguments: `$ARGUMENTS` — the PR (URL, `owner/repo/pull/N` or `N`), plus `--ci` when running in GitHub Actions.

You are an expert, independent senior reviewer. Be specific, kind and decisive. Review the code, not the author. Don't approve or merge via the API — humans do that.

## 1. Load the PR

```
gh pr view <pr> --json number,title,body,baseRefName,headRefName,author,files,additions,deletions
gh pr diff <pr>
```
Read `CLAUDE.md` and apply the stack skills it lists. Read surrounding code where the diff alone isn't enough to judge.

**Mode by base branch:**
- base `develop` → **change review** (this feature/fix).
- base `main` from `develop` → **release review** (everything since last release: breaking changes, migrations, config, security, half-finished work not behind flags).
- base `main` from `patch/*` → **hotfix review** (minimal, targeted, has a regression test, safe to deploy now).

**Branch policy:** `develop` accepts `feat/*`, `fix/*`, `chore/*`, `docs/*`, `refactor/*`, `test/*`, `deps/*` and back-merges from `main`; `main` accepts only `develop`, `patch/*` and release-please PRs. A wrong source → blocking.

## 2. What to check

1. **Correctness** — does it do what the PR says? Edge cases, nulls/empty, errors, concurrency, time zones, money as integers/Decimal.
2. **Security** — object- and property-level authorization, tenant scoping, input validation, injection, secrets in code/logs, PII, tokens storage, webhook verification, idempotency on payments.
3. **Breaking changes** — API contracts, DB schema, event payloads, mobile min version. Must be versioned/expand-contract.
4. **Tests** — new/changed behaviour covered at the right level; meaningful assertions; no skipped or weakened tests; flaky patterns (sleeps, real network, shared state).
5. **Performance & scalability** — N+1, missing indexes/pagination, blocking calls in async code, unbounded lists, unnecessary re-renders/rebuilds, bundle/app size.
6. **Architecture & reuse** — layer boundaries, duplication of existing components/utilities, right abstraction level.
7. **Readability** — naming, small functions, dead code, comments explain why.
8. **UX & i18n** — loading/error/empty states, accessibility, responsive/adaptive, all strings in en + sw.
9. **Design fidelity** (UI changes) — follows the project's `design.md`; only semantic tokens (no hard-coded colours, font sizes, radii, shadows, durations); stock component-library look restyled; motion uses tokens, is interruptible and respects reduced motion; light + dark both work. Generated token files must not be hand-edited.
10. **Ops** — logging/metrics, feature flags for risky changes, migrations reversible, config documented, changelog-worthy title.

## 3. Severity

- **blocking** — bug, security issue, data loss risk, breaking change, missing critical test, policy violation. Must fix before merge.
- **should-fix** — real quality/maintainability/performance problem; fix in this PR unless justified.
- **nit** — style/preference; optional. Keep these few.

Don't report things CI already enforces (formatting, lint) unless CI missed them.

## 4. Post the review

- One **inline comment** per blocking/should-fix finding on the exact line (`mcp__github_inline_comment__create_inline_comment` in CI; `gh` locally). Format: `**[blocking]** <problem> — <why it matters>. Suggested fix: <concrete change or code>`.
- One **summary comment** (`gh pr comment <pr> --body-file <file>`):
  - Verdict: ✅ **PASS** (no blocking) or ❌ **CHANGES REQUESTED**
  - Counts by severity, top risks, what was done well (1–2 lines)
  - For release reviews: breaking changes, migrations, config to set, rollback notes
- If nothing to flag, say so briefly — don't invent issues.

## 5. CI verdict (`--ci` only)

Write exactly `PASS` or `FAIL` (FAIL if any blocking finding) to the file `.claude-review-verdict` in the repository root. The workflow fails the check on `FAIL`.
