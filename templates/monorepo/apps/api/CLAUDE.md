# API (apps/api)

Skill: **vekta-api:python-backend-expert** (+ vekta-core:engineering-workflow). Root rules: `../../CLAUDE.md`.

- Run everything from this folder, or from the root with `just api::<recipe>`.
- `just dev` · `just test` · `just lint` · `just typecheck` · `just migrate` · `just makemigration "<name>"` · `just seed` · `just ci`
- The contract is generated from this app: after changing routes or schemas run `just gen` **at the repo root** and commit `packages/contract/openapi.json` and the regenerated clients.
- Breaking API changes need a new version (`/api/v2`) + `Deprecation`/`Sunset` headers — the mobile app can't update instantly.
- Specifics: <database, payments provider, multi-tenant yes/no, background jobs>
