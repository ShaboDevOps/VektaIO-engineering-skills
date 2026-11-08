---
name: react-frontend-expert
description: Use when building, refactoring or scaffolding any web frontend: production-grade React + TypeScript that is fast, secure, accessible and scales to many users.
---

# React Frontend Expert

You write frontend code the way a senior staff engineer at a top product company would: typed end to end, fast on low-end Android phones over 3G, secure by default, accessible, responsive, bilingual (English/Swahili) and easy for the next developer to read. Rules are enforced by tooling, not memory. Never ship demo-quality code.
Repo, CI and PR conventions live in the **engineering-workflow** skill; testing depth lives in the **software-testing-expert** skill. Project-specific facts in the repo's `CLAUDE.md` override this skill.

## 0. Version baseline (verified Nov 2026)

React 19.3 · React Compiler 1.0 · TypeScript 7.0 · Vite 8 (Rolldown) · Next.js 16.4 · React Router 8 · TanStack Query v5 · Zustand 5 · Zod 4 · @hookform/resolvers 5 · Tailwind CSS 4 · shadcn/ui (Base UI default) · ESLint 10 · Vitest 5 · Playwright 1.6x · MSW 2 · Sentry JS v11 · pnpm 11 · Node.js 24/26 LTS.
Check official changelogs before starting a project or when an API looks unfamiliar.

## 1. Stack (default — deviate only with a stated reason)

| Concern | Choice |
|---|---|
| Language | TypeScript 7: `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `verbatimModuleSyntax`, `erasableSyntaxOnly`, `moduleResolution: "bundler"`; no `any` |
| Framework | **Vite 8** SPA/PWA for dashboards/portals; **Next.js 16** (App Router, Turbopack, Cache Components) when SEO/SSR matters |
| Compiler | React Compiler on; version pinned exactly |
| Server state | TanStack Query v5 with `queryOptions` factories |
| URL state | **nuqs** for filters, tabs, sort, pagination, search |
| Client state | `useState` → Zustand 5 for truly global UI state |
| Routing | React Router 8 or Next.js router; all routes lazy |
| Forms | React Hook Form + Zod 4 (`@hookform/resolvers` v5) |
| UI | Tailwind CSS 4 + shadcn/ui (Base UI) + `cva` + `tailwind-merge`, themed from the project's design tokens |
| Motion | CSS transitions + Motion (`motion/react`) + View Transitions, driven by motion tokens |
| API client | Generated from OpenAPI (`openapi-typescript` + `openapi-fetch`) + Zod at runtime |
| API mocking | **MSW 2** — one set of handlers for dev, tests and Storybook |
| Lists / tables | TanStack Table + TanStack Virtual |
| i18n | i18next + react-i18next (ICU), `Intl` |
| Feature flags | OpenFeature React SDK + provider (Unleash/Flagsmith/GrowthBook), typed flag registry |
| Analytics | Typed event registry behind an `analytics` interface (PostHog/GA provider) |
| Monorepo | pnpm workspaces + Turborepo |
| Quality | ESLint 10 (typescript-eslint strict-type-checked, react-hooks recommended, jsx-a11y, **boundaries**), Prettier, **knip** |
| Testing | Vitest 5 (Browser Mode), Testing Library, Playwright, Storybook (+ a11y, visual snapshots) |
| Monitoring | Sentry v11 + `web-vitals` v5 |

## 2. Project structure (feature-first, enforced)

```
src/
  app/            # providers, router, error boundaries, query client, i18n, flags
  features/
    orders/
      api/        # keys.ts, queries.ts, mutations.ts, schemas.ts
      components/
      hooks/
      routes/
      index.ts    # public surface
  shared/
    ui/  lib/  hooks/
    auth/         # session, permissions, <Can>
    analytics/    # events.ts registry + provider
  config/         # env (zod), constants, flags.ts registry
  locales/{en,sw}/*.json
  mocks/          # MSW handlers + data factories
```
**Enforce boundaries with ESLint** (`eslint-plugin-boundaries` or import-x `no-restricted-paths`): `shared` can't import `features`/`app`; a feature can't import another feature's internals (only its `index.ts`); `app` composes everything. CI fails on violations.
Monorepo for multi-app products: `apps/*`, `packages/{ui,api,i18n,config}`.

## 3. Code standards

- Small, pure, named components with explicit `type Props`.
- Derive state; `useEffect` only for external sync (with cleanup); `useEffectEvent` for non-reactive logic.
- Let React Compiler memoize; manual memo only with Profiler evidence.
- Validate every API response with Zod.
- No magic values; `as const` unions instead of `enum`.
- Every view handles loading (skeleton), error (retry), empty, success.
- Intent-revealing names; comments explain *why*.

## 4. Data layer conventions

Every resource follows the same template so caching never drifts:
```ts
// features/orders/api/keys.ts
export const orderKeys = {
  all: ['orders'] as const,
  lists: () => [...orderKeys.all, 'list'] as const,
  list: (f: OrderFilters) => [...orderKeys.lists(), f] as const,
  detail: (id: string) => [...orderKeys.all, 'detail', id] as const,
};

// features/orders/api/queries.ts
export const orderQueries = {
  detail: (id: string) =>
    queryOptions({
      queryKey: orderKeys.detail(id),
      queryFn: ({ signal }) => http.get(`/orders/${id}`, { signal }).then(OrderSchema.parse),
      staleTime: 30_000,
    }),
};
export const useOrder = (id: string) => useQuery(orderQueries.detail(id));

// features/orders/api/mutations.ts
export function useCancelOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      http.post(`/orders/${id}/cancel`, null, { headers: { 'Idempotency-Key': crypto.randomUUID() } }),
    onSuccess: (_, id) => {
      void qc.invalidateQueries({ queryKey: orderKeys.detail(id) });
      void qc.invalidateQueries({ queryKey: orderKeys.lists() });
    },
  });
}
```
- Always set `staleTime`; never `invalidateQueries()` without a key.
- Prefetch with `queryClient.ensureQueryData(orderQueries.detail(id))` in route loaders.
- **URL is state**: filters/tabs/sort/page live in the URL via nuqs (shareable links, working back button) and feed query keys. Don't mirror them in Zustand.

### Next.js 16 specifics
`cacheComponents` on; `'use cache'` + `cacheLife`/`cacheTag`; `updateTag`/`revalidateTag(tag, profile)`; `await` `params`/`cookies()`/`headers()`; `proxy.ts`; Server Components by default; **Server Functions validate + authorize**; `import 'server-only'` for secret modules.

## 5. Auth, permissions & feature gates in the UI

- One `useSession()` source (user, roles, permissions, tenant) loaded once and cached.
- Central `POLICIES` map + `useCan(permission | policyFn)` hook + `<Can permission="orders:approve" fallback={…}>` component; route guards use the same policies. Never sprinkle `user.role === 'admin'` checks.
- `<Feature flag="new-checkout">` / `useFlag()` from a **typed flag registry** (`config/flags.ts`: name, owner, description, default, expiry). Remove flags after full rollout.
- UI gating is UX only — the API enforces everything.

## 6. Project design identity & reusable components

**Each product has its own look.** The design direction and tokens live in `design/` (or `packages/design/` in a monorepo) and are created with the **vekta-design:design-direction** skill. `just tokens` generates `src/styles/tokens.css` (Tailwind 4 `@theme` + light/dark semantic variables + reduced-motion); import it once after `@import "tailwindcss"`. Build screens with the **vekta-design:ui-craft** skill.
- Use **semantic** utilities only: `bg-background`, `bg-surface`, `text-foreground`, `text-foreground-muted`, `bg-primary text-primary-foreground`, `border-border`, `ring-ring`, `rounded-md`, `shadow-md`, `font-heading`, `ease-standard duration-(--duration-base)`. Palette shades (`bg-brand-600`) only inside design-system components, never in features.
- **No hard-coded** hex/rgb, px font sizes, arbitrary radii/shadows or durations (`bg-[#…]`, `text-[17px]`, `duration-[350ms]`) — lint/review blocks them.
- **Restyle shadcn/Base UI** to the direction (radius, borders vs shadows, focus ring, density, motion); never ship the stock look.
- Fonts self-hosted (`@fontsource/*`), matching `font.family` in tokens.
- **Theming in one place** (generated by `just tokens`): add `<script src="/theme-init.js"></script>` as the first thing in `<head>` (no flash), call `initTheme()` in `main.tsx` before rendering, and use only the `useTheme()` hook (`mode`, `theme`, `customColor`, `resolvedMode`, `themes`, `setMode`, `setTheme`, `setCustomColor`, `resetTheme`) for theme UI. Light/dark/system, preset themes and any custom colour all flow through it; components just use semantic utilities and follow automatically. Never touch theme `localStorage` keys, `prefers-color-scheme` or `<html>` theme attributes elsewhere. Build an Appearance settings page (see `vekta-design:ui-craft`).
- Motion: CSS transitions with token utilities; Motion (`motion/react`) for complex/layout/gesture animation using the token values; `<ViewTransition>` for route transitions; always honour reduced motion.
- No `design/` folder yet? Run `/vekta-design:design-direction` before building UI.

**Layers**: tokens (generated `tokens.css`) → primitives (Base UI/Radix) → composites (`DataTable`, `FormField`, `EmptyState`, `MoneyText`, `DateText`) → feature components (in `features/*` only).
**Rules**: composition over configuration (slots, compound components); `cva` variants; accept native props + `ref`; `asChild`/`render` for polymorphism; headless hooks (`usePagination`, `useDisclosure`); rule of three; shared UI never fetches data.
**Enforced**: lint rule bans raw styled `<button>`/`<input>` and direct primitive-library imports inside `features/` — use `shared/ui`.
**Performance**: ESM, `"sideEffects": false`, subpath exports (no giant barrels), lazy heavy composites, no runtime CSS-in-JS.
**Docs**: Storybook story per component with variants, dark mode, long Swahili text; a11y addon and visual snapshot tests in CI; Changesets SemVer when shared across apps.

## 7. Responsive UI

Mobile-first breakpoints (`sm 640 / md 768 / lg 1024 / xl 1280 / 2xl 1536`); container queries for reusable components; `clamp()` fluid type; `dvh`/`svh`; `env(safe-area-inset-*)`; tables → cards, sidebar → bottom nav/drawer; `pointer: coarse` targets ≥ 44px; responsive images; test 320/375/768/1024/1440 + landscape + a foldable viewport.

## 8. Localization (English + Swahili)

- `en`, `sw` (`en-TZ`/`sw-TZ` formatting); default from profile → saved choice → browser.
- No hard-coded strings; semantic namespaced keys; namespaces lazy-loaded per route.
- ICU plurals/select; never concatenate.
- `Intl.NumberFormat(locale, { style: 'currency', currency: 'TZS', maximumFractionDigits: 0 })`, `Intl.DateTimeFormat`, `Intl.RelativeTimeFormat`; E.164 phones.
- `<html lang>`, titles, meta, aria-labels, alt text, Zod error map per locale.
- Design for 30–40% text expansion.
- Send `Accept-Language`; translate server errors via stable `code`.
- CI fails on missing/unused keys; pseudo-locale in dev; translations synced via a TMS (Weblate/Crowdin/Tolgee) rather than hand-editing.

## 9. Performance (p75 mid-range Android: LCP ≤ 2.5s, INP ≤ 200ms, CLS ≤ 0.1)

- Route splitting; heavy libs on demand; initial JS ≤ 170 KB gzipped, **size diff commented on every PR** (size-limit); `knip` removes dead code/deps.
- Virtualize > ~100 rows; state low; split contexts.
- `useDeferredValue`/`useTransition`; `<Activity>`; `<ViewTransition>`.
- Optimized images, `fetchpriority` on LCP image; self-hosted subset fonts.
- Prefetch likely next routes/data.
- PWA app shell, optimistic updates, retry with backoff, offline banner.
- `@performance`-tagged Playwright tests for key flows run in a separate CI job; Lighthouse CI on preview deployments.

## 10. Security

- Auth in `HttpOnly; Secure; SameSite` cookies; never `localStorage`.
- DOMPurify for any HTML; Trusted Types + nonce CSP; `frame-ancestors`, `Referrer-Policy`, `X-Content-Type-Options`, SRI.
- No secrets in `VITE_*`/`NEXT_PUBLIC_*`; env via Zod.
- Block `javascript:` URLs; encode params.
- Scrub PII in Sentry and analytics; mask Session Replay; analytics only after consent where required.
- Patch React/Next security releases within days.
- Supply chain: frozen lockfile; pnpm 11 `minimumReleaseAge`, `strictDepBuilds`, `blockExoticSubdeps`, script allow-list (CI details in engineering-workflow).

## 11. Observability & analytics

- Typed event registry: `analytics.track('order_cancelled', { orderId, reason })` — event names `object_action` snake_case, props typed per event; no PII. A no-op provider in dev/tests and a recording stub for assertions.
- Sentry: release + environment tags, user id (not email/phone), breadcrumbs for navigation and mutations.

## 12. API versioning (client side)

Version in one config constant; regenerate typed client per backend release (CI fails on drift); tolerate additive changes (never `.strict()` on responses); report `Deprecation`/`Sunset` headers to Sentry; migrate feature by feature behind flags.

## 13. Release versioning

SemVer per app/package; Conventional Commits → release-please/Changesets → `CHANGELOG.md` + tag; inject version + git SHA; Sentry release + private source maps; hashed assets; PWA "New version available" prompt; same artifact promoted dev → staging → prod; rollback = redeploy previous artifact; risky features behind flags.

## 14. Reliability & accessibility

- Error Boundaries (app + route) with Retry; mutations handle 401/403/409/422/429/5xx; `Idempotency-Key` on money/order mutations.
- WCAG 2.2 AA: semantic HTML, keyboard, focus, contrast ≥ 4.5:1, targets ≥ 24px, announced errors, reduced motion.

## 15. Definition of done

- [ ] `tsc`, ESLint (incl. boundaries + compiler rules), Prettier, knip: zero warnings
- [ ] Data layer follows keys/queries/mutations template; URL state via nuqs
- [ ] Permissions via `<Can>`/`useCan`; flags via registry
- [ ] Loading / error / empty / success states
- [ ] Matches the project's `design.md`; only semantic tokens (no hard-coded colours/sizes/durations); `just tokens --check` passes
- [ ] Works in light, dark, every preset theme and a custom colour; theme state only via `useTheme()`
- [ ] Reused design-system components; new ones in Storybook with a11y + visual snapshot
- [ ] Responsive 320 → 1440 + landscape
- [ ] All strings in `en` + `sw`; `Intl` formatting
- [ ] MSW handlers added/updated for new endpoints
- [ ] Analytics events typed and PII-free
- [ ] Bundle size diff acceptable
- [ ] Tests per software-testing-expert; Playwright test for critical flow
- [ ] Conventional commit; PR template completed
- [ ] State any trade-off in one or two sentences
