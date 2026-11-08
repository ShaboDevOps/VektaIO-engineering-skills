# Mobile (apps/mobile)

Skill: **vekta-mobile:flutter-mobile-expert** (+ vekta-core:engineering-workflow). Root rules: `../../CLAUDE.md`.

- Run from this folder, or from the root with `just mobile::<recipe>`.
- `just dev` · `just test` · `just lint` · `just gen` · `just ci`
- The API client lives in `packages/api_client` (generated from `packages/contract/openapi.json` at the repo root) — don't edit it; run `just gen` at the root.
- Flavors: dev (local API), staging (staging API), prod (production API), demo (local data). API URL comes from `config/<flavor>.json`.
- Specifics: Android package / iOS bundle id <tz.co.example>
