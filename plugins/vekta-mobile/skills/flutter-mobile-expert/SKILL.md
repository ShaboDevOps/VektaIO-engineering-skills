---
name: flutter-mobile-expert
description: Use when building or changing any Flutter mobile app: production-grade Dart with Riverpod, clean architecture, smooth 60fps UI, offline-first and secure by default.
---

# Flutter Mobile Expert

You build Flutter apps like a senior mobile lead shipping to millions of users on low-end Android devices, tablets and foldables with unreliable networks. The app must be smooth, crash-free, secure, offline-tolerant, adaptive, bilingual (English/Swahili) and pass Google Play and App Store review the first time. Rules are enforced by tooling, not memory.
Repo, CI and PR conventions live in the **engineering-workflow** skill; testing depth lives in the **software-testing-expert** skill. Project-specific facts in the repo's `CLAUDE.md` override this skill.

## 0. Version baseline (verified Nov 2026)

Flutter 3.47 · Dart 3.13 · flutter_riverpod 3.x · go_router 18 · freezed 4 · json_serializable 6.15 · dio 5.11 · drift 2.35 · flutter_secure_storage 11 · firebase_messaging · workmanager · pigeon · very_good_analysis 11 · mocktail 1.x · patrol 4 · sentry_flutter 10 / firebase_crashlytics 6.
Android: compile/target SDK 36, minSdk 24, AGP 9. iOS: min iOS 15, Xcode 26+ SDK, Swift Package Manager.
Check Flutter release notes and package changelogs before starting or upgrading.

## 1. Stack (default)

| Concern | Choice |
|---|---|
| Design widgets | Material 3 from `material_ui` (+ `cupertino_ui`) |
| State / DI | Riverpod 3 (codegen), **global retry policy**, **Mutations** for user actions |
| Navigation | go_router 18 (typed routes, redirects, `StatefulShellRoute`) |
| Models | freezed 4 + json_serializable |
| Networking | dio 5 + interceptors (auth refresh, version/locale headers, retry) |
| Offline DB | drift with **committed schema snapshots + migration tests** |
| Background work | workmanager behind a `SyncManager` interface |
| Push | firebase_messaging behind a `PushService` interface |
| Native APIs | **Pigeon**-generated typed channels (no raw `MethodChannel` strings) |
| Secure storage | flutter_secure_storage 11 |
| Logging | `logging` package → console (debug) + persistent ring-buffer log + Sentry breadcrumbs |
| Analytics | `AnalyticsService` interface (Firebase/PostHog prod, no-op demo, recording stub in tests) |
| i18n | flutter_localizations + `intl` + ARB via `gen-l10n`, synced with a TMS (Weblate/Crowdin) |
| Splash | flutter_native_splash with a startup gate |
| Quality | very_good_analysis 11 + custom lints (analyzer plugin / custom_lint), `dart format` |
| Testing | flutter_test, mocktail, golden tests, patrol |
| Workspace | Dart pub workspaces |
| Flavors | `dev`, `staging`, `prod` + **`demo`** (local data) via `--dart-define-from-file` |

## 2. Architecture (official Flutter guide + Riverpod)

```
lib/
  main_dev.dart main_staging.dart main_prod.dart main_demo.dart
  app/        # App, router, theme, bootstrap/startup gate, locale controller
  core/       # Result, failures, network, storage, logging, monitors, app version
  data/
    services/      # API, DB, push, platform (Pigeon) — one source each
    repositories/  # abstract + remote impl + local/demo impl
    models/        # DTOs
  domain/models/   # (use_cases/ only when logic spans repositories)
  ui/<feature>/{view_models,widgets}/
  l10n/app_en.arb app_sw.arb
test/  testing/   # fakes, fixtures, pumpApp (see software-testing-expert)
drift_schemas/   # committed schema JSON snapshots
pigeons/         # Pigeon interface definitions
```
Multi-app: `apps/*`, `packages/{design_system,api_client,core,testing}`.
Rules: UI (View + ViewModel) separate from data (Repository + Service); one-way data flow; no logic in widgets; repositories return `Result`; role-based names; widgets ≤ ~200 lines.

## 3. Code standards

- `const` everywhere possible; immutable state.
- Sealed `AppFailure` in sealed `Result<T>`; exceptions mapped in repositories.
- Render every `AsyncValue` state.
- `ref.mounted` / `context.mounted` after `await`.
- Dispose controllers, streams, timers.
- No hard-coded strings, colours, sizes, breakpoints.
- **Banned by lint**: `print`/`debugPrint` (use `logging`), raw Material buttons/text fields/colours inside `ui/<feature>` (use design system), `MediaQuery.of`, `dart:io` `HttpClient` directly.

### Example
```dart
sealed class Result<T> {
  const Result();
}
final class Ok<T> extends Result<T> {
  const Ok(this.value);
  final T value;
}
final class Err<T> extends Result<T> {
  const Err(this.failure);
  final AppFailure failure;
}

@riverpod
class OrdersViewModel extends _$OrdersViewModel {
  @override
  Future<List<Order>> build() async {
    final result = await ref.watch(orderRepositoryProvider).fetchOrders();
    return switch (result) {
      Ok(:final value) => value,
      Err(:final failure) => throw failure,
    };
  }

  Future<void> refresh() async {
    ref.invalidateSelf();
    await future;
  }
}
```

### Riverpod retry policy (mandatory)
Riverpod 3 retries failing providers up to 10 times by default. Retrying auth, validation or upgrade errors hammers the API and flickers the UI:
```dart
Duration? appRetry(int retryCount, Object error) {
  if (retryCount >= 3) return null;
  if (error is AppFailure && !error.isTransient) return null; // 4xx, 401, 403, 422, 426
  return Duration(milliseconds: 300 * (1 << retryCount));
}

runApp(ProviderScope(retry: appRetry, child: const App()));
```

### User actions with Mutations (Command pattern)
Each button action (submit, pay, cancel) gets its own pending/error/success state via Riverpod Mutations (or a Command class as in Flutter's Compass sample): disable the trigger while pending (no double taps), show error inline, `reset()` after handling. Don't mix action state into the screen's data state.

## 4. Project design identity & reusable UI components

**Each product has its own look.** The design direction and tokens live in `design/` (or `packages/design/` in a monorepo) and are created with the **vekta-design:design-direction** skill. `just tokens` generates `lib/app/theme/app_tokens.dart`: `AppPalette`, `AppColors` (semantic `ThemeExtension`, light + dark), `AppSpace`, `AppRadius`, `AppShadows`, `AppMotion`, `AppType` and `buildAppTheme(brightness)`. Build screens with the **vekta-design:ui-craft** skill.
- **Theming in one place**: `just tokens` also generates `lib/app/theme/app_theme.dart` — `AppThemeController` (Riverpod: `setMode`, `setTheme`, `setCustomColor`, `reset`), `appThemeProvider` and the colour engine for custom colours. Implement `ThemePreferenceStore` (SharedPreferences, optionally synced to the profile API), load it in bootstrap and override `themePreferenceStoreProvider` + `initialThemePreferenceProvider` (first frame already correct). In `App`: `final t = ref.watch(appThemeProvider); MaterialApp.router(theme: t.light, darkTheme: t.dark, themeMode: t.mode, …)`. Theme UI reads/writes only `appThemeControllerProvider`; never keep brightness/colour flags elsewhere. Build an Appearance settings screen (see `vekta-design:ui-craft`).
- Add component themes (buttons, inputs, cards, navigation, page transitions) inside `buildAppTheme`'s callers in `app/theme/` using only token values, so they follow every theme.
- Read colours with `context.colors.primary` (or `Theme.of(context).colorScheme`); spacing `AppSpace.lg`; radius `AppRadius.md`; motion `AppMotion.base` + `AppMotion.standard`.
- **No hard-coded** `Color(0x…)`, `Colors.*`, font sizes, radii or durations in `ui/` — custom lint/review blocks them. Don't use `ColorScheme.fromSeed` (it overrides the brand palette).
- Restyle Material widgets to the direction — never ship the stock Material look.
- Fonts bundled in `assets/fonts/` + `pubspec.yaml` matching `font.family` (no runtime font downloads).
- Motion: implicit animations with motion tokens, `Hero` for list → detail, `pageTransitionsTheme` (keep predictive back), honour `MediaQuery.disableAnimationsOf`.
- No `design/` folder yet? Run `/vekta-design:design-direction` before building UI.

- **Layers**: tokens (generated `app_tokens.dart`) → theme (`buildAppTheme` + component themes) → primitives (`AppButton`, `AppTextField`, `AppCard`, `Gap`) → composites (`AsyncValueView<T>`, `PaginatedListView<T>`, `EmptyState`, `ErrorView`, `ConfirmSheet`, `MoneyText`, `DateText`, `AdaptiveScaffold`) → feature widgets.
- Composition over configuration; generic widgets for repeated patterns; stateless/controlled; rule of three; shared widgets never import features.
- Catalogue in Widgetbook/Widget Previews; golden tests per variant (light/dark, large text, Swahili).
- Performance: `const`, `MediaQuery.sizeOf`/`paddingOf`, cheap `build`, `RepaintBoundary` for animations, `itemExtent`/`prototypeItem`.
- Design system enforced by lint (see §3); SemVer when shared.

## 5. Responsive, adaptive & foldables

- M3 window size classes (compact < 600, medium 600–839, expanded 840–1199, large 1200–1599, XL ≥ 1600) via `WindowSizeClass.of(context)`; decide by available space.
- Adaptive navigation (NavigationBar → NavigationRail → drawer) with `StatefulShellRoute`.
- Canonical layouts: list-detail, supporting pane, adaptive grids.
- Foldables: `MediaQuery.displayFeaturesOf` — nothing across the hinge; tabletop and book postures; state survives fold/unfold/multi-window (Riverpod state, `PageStorageKey`, restoration IDs); never lock orientation.
- Edge-to-edge insets, keyboard insets, text scaling 200%, keyboard/mouse/stylus support.
- Test matrix: small/large phone, 7"/10" tablet, Fold emulators (folded/unfolded/tabletop), landscape, split-screen; goldens at compact/medium/expanded.

## 6. Localization (English + Swahili)

`l10n.yaml` + `flutter gen-l10n`; `supportedLocales: [Locale('en'), Locale('sw')]` + global delegates; `LocaleController` (saved → device → fallback) switches instantly; `Accept-Language` on API calls; ICU plurals/select with descriptions; `NumberFormat.currency(locale: 'sw', name: 'TZS', symbol: 'TSh', decimalDigits: 0)`, `DateFormat` per locale; translate errors (server `code` → ARB key), validation, notifications, semantics, store listing; layouts grow for long Swahili text; CI fails on untranslated messages; translators work in a TMS synced to ARB.

## 7. Startup & app lifecycle

- **Startup gate**: `FlutterNativeSplash.preserve()` until bootstrap completes (config, auth session, DB open, remote config, min-version check); go_router redirect waits on a `startupProvider` — no white flash or wrong first screen.
- Defer non-critical init (analytics, image cache warm-up) until after the first frame.
- `AppLifecycleListener`: on resume refresh stale data, re-check session and pending sync; on pause flush logs and outbox.

## 8. Offline-first, background sync & push

- drift is the UI's source of truth; network refreshes it; outbox with idempotency keys; conflict policy per entity; optimistic UI with rollback; sync status + offline banner.
- **drift migrations**: bump `schemaVersion`, run `dart run drift_dev make-migrations` (commits `drift_schemas/*.json` + step-by-step migrations), and a `SchemaVerifier` test covers every old → new version pair. Never edit a released migration.
- **Background sync**: `SyncManager` interface; workmanager unique periodic work (KEEP policy) with `NetworkType.connected` constraint plus one-off work after enqueuing outbox items; tasks are idempotent and short; respect Doze/battery saver; iOS uses BGTaskScheduler limits (best effort).
- **Push notifications** (`PushService`):
  - Top-level background handler annotated `@pragma('vm:entry-point')`.
  - Handle cold start (`getInitialMessage`), background tap (`onMessageOpenedApp`), foreground (`onMessage` + local notification; iOS foreground presentation options).
  - Register/refresh token with the backend (`onTokenRefresh`), tied to user + locale; remove on logout.
  - Data-only "sync" messages trigger `SyncManager`, not UI.
  - Notification taps deep-link through go_router with validated params.
  - Ask notification permission in context (Android 13+, iOS), not at first launch.

## 9. Environment & platform abstractions

- `NetworkMonitor`, `Clock`, `TimeZoneMonitor`, `AppInfo` (version/build), `PermissionService` behind interfaces with fake implementations, so offline, time and permission logic is testable.
- Native features via **Pigeon** typed interfaces (Dart ↔ Kotlin/Swift), each wrapped in a service.
- **Demo flavor**: every repository has a local/demo implementation fed by bundled JSON, selected in DI per flavor — used for offline development, deterministic screenshots/goldens, and a **demo login for store reviewers**.

## 10. Logging & diagnostics

- One `Logger` per class (`logging` package); levels used consistently; no PII.
- Release builds keep WARN+ in a **persistent ring-buffer log** (separate small drift DB, capped e.g. 5,000 lines) viewable and shareable from Settings → "Send diagnostics" — essential when crash reports can't reach the server on poor networks.
- Crashlytics/Sentry: release = `version+build`, user id only, breadcrumbs from navigation and logs.

## 11. Analytics

Typed event constants (`AnalyticsEvent.orderCancelled`) and parameter keys; `object_action` snake_case names; no PII; consent respected; no-op in demo/dev, recording stub in tests so tests can assert events.

## 12. Performance

Impeller (also test a non-Vulkan device); builders/slivers; `select`; small widgets; `RepaintBoundary`; `Isolate.run`; cached/resized images; pagination; profile mode + DevTools (fix frames > 16ms); App Bundles; tree-shaken icons; high refresh rate where supported; minimal background work for battery and data.

## 13. API versioning (client side)

Version in config per flavor; interceptor adds `X-App-Version`, `X-Platform`, `Accept-Language`; `/app-config` drives forced/soft update (Play In-App Updates); global `426` handling; tolerant parsing (`unknownEnumValue`); log `Deprecation`/`Sunset`; old versions live for months.

## 14. Release versioning

`version: X.Y.Z+BUILD` (monotonic build from CI); Conventional Commits → release-please → changelog + tag; bilingual store notes; CI/CD with fastlane (flavors, obfuscation, symbols, signing from secrets, Play internal / TestFlight); **CI diffs release manifest permissions and Info.plist usage keys against a committed baseline** (fails if a plugin adds a permission); staged rollouts watching crash-free rate; version shown in Settings and crash tools; remote config + forced update.

## 15. Platform requirements (2026)

Android: target API 36, edge-to-edge, predictive back (`PopScope`), large-screen layouts, 16 KB page size (NDK r28+, check Play Console deadline), AGP 9 built-in Kotlin, account deletion (in-app + web), Data safety, Families policy if applicable.
iOS: SwiftPM (CocoaPods registry read-only Dec 2026), UIScene lifecycle, required Xcode/SDK, privacy manifests + required-reason APIs, age ratings.

## 16. Security (OWASP MASVS 2.1 incl. PRIVACY)

No secrets in the app; secure-storage tokens, cleared on logout, single-flight refresh; HTTPS + pinning for payment/health with rotation plan; obfuscation + symbols; no sensitive logs; validated deep links and notification payloads; screenshot protection on sensitive screens; biometric/PIN for high-risk actions; just-in-time minimal permissions; minimal data; Tanzania PDPA consent and deletion.

## 17. Definition of done

- [ ] `flutter analyze` (incl. custom lints) clean, formatted, generated code (l10n, freezed, riverpod, pigeon, drift) up to date
- [ ] Retry policy respected; actions use Mutations/Commands
- [ ] Matches the project's `design.md`; only token values (no hard-coded colours/sizes/durations); `just tokens --check` passes
- [ ] Works in light, dark, every preset theme and a custom colour; theme state only via `appThemeControllerProvider`
- [ ] Design-system widgets reused; new ones catalogued with goldens
- [ ] All states rendered; offline behaviour defined; outbox for writes
- [ ] drift schema bumped with snapshot + migration test if tables changed
- [ ] Compact/medium/expanded + foldable verified; edge-to-edge; predictive back; text 200%
- [ ] Strings in `en` + `sw`; `intl` formatting
- [ ] Demo repository implemented for new data sources
- [ ] Version/platform/locale headers; forced update handled
- [ ] No secrets; no sensitive logs; permissions baseline unchanged (or justified)
- [ ] Analytics events typed; logs via `logging`
- [ ] Tests per software-testing-expert; patrol for critical flow
- [ ] Version/build bumped; conventional commit; PR template completed
- [ ] State any trade-off in one or two sentences
