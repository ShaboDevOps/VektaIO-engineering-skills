## What & why
<!-- One paragraph. Link the issue: Closes #123 -->

## How to test
<!-- Steps a reviewer can follow; seed data / test accounts. -->

## Test evidence
<!-- Commands run and results (just test / just e2e), coverage change. -->

## Review summary
<!-- What the code-reviewer agent found and how it was addressed. -->

## Screenshots / recordings
<!-- UI changes: before / after, mobile + desktop, en + sw. -->

## Risk & rollback
<!-- What could go wrong, how to roll back (revert, flag off, previous tag). -->

## Checklist
- [ ] Self-reviewed the diff
- [ ] Tests added/updated (unit / integration / e2e as relevant); regression test for fixes
- [ ] No breaking API change, or versioned with deprecation headers
- [ ] Migrations backward compatible (expand → migrate → contract) and reversible
- [ ] Strings translated (en + sw)
- [ ] Security considered (authz, input validation, secrets, PII)
- [ ] Feature flag for risky changes
- [ ] Docs / runbook / decision log updated
