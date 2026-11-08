# Web (apps/web)

Skill: **vekta-web:react-frontend-expert** (+ vekta-core:engineering-workflow). Root rules: `../../CLAUDE.md`.

- Run from this folder, or from the root with `just web::<recipe>`.
- `just dev` · `just test` · `just lint` · `just typecheck` · `just e2e` · `just ci`
- API types are generated into `src/shared/api/schema.d.ts` from `packages/contract/openapi.json` — don't edit them; run `just gen` at the root.
- API base URL comes from `VITE_API_URL` (per environment); never hard-code it.
- Specifics: <Vite SPA | Next.js>, <hosting>
