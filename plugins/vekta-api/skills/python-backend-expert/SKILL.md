---
name: python-backend-expert
description: Use when building or changing any Python backend or API: production-grade FastAPI services that are secure, fast, horizontally scalable and handle high concurrency.
---

# Python Backend Expert (FastAPI)

You write backend code like a principal engineer responsible for a system serving hundreds of thousands of concurrent users and real money (mobile money, cards). Correctness and security first, then performance, then convenience. Rules are enforced by tooling, not memory.
Repo, CI and PR conventions live in the **engineering-workflow** skill; testing depth lives in the **software-testing-expert** skill. Project-specific facts in the repo's `CLAUDE.md` override this skill.

## 0. Version baseline (verified Nov 2026)

Python 3.14 · FastAPI 0.16x · Starlette 1.x · Uvicorn 0.5x · Pydantic 2.14 · pydantic-settings 2.16 · SQLAlchemy 2.1 · psycopg 3.3 · Alembic 1.20 · PostgreSQL 18 · uv 0.13 · Ruff 0.17 · mypy 2.x · import-linter · pytest 9 + pytest-asyncio 1.x · Celery 5.7 · PyJWT 2.x · pwdlib · Babel · Locust.
Check official release notes before starting a project or when an API looks unfamiliar.

## 1. Stack (default)

| Concern | Choice |
|---|---|
| Runtime | Python 3.14, **uv** (`uv.lock`; `exclude-newer` cooldown, see §13) |
| Framework | FastAPI (`fastapi[standard]`), async, lifespan only |
| Validation | Pydantic v2 (`extra="forbid"` inputs); `response_model`/return types |
| Settings | pydantic-settings with **default-secret guard** |
| Database | PostgreSQL 18 + SQLAlchemy 2.1 async + psycopg 3 + Alembic |
| IDs | `uuidv7()` |
| Cache / limits / locks | Redis |
| Jobs | Celery 5.7 workers + a **separate scheduler process** (Celery beat or APScheduler) |
| Files | S3-compatible object storage with presigned uploads |
| Server | `fastapi run --workers N` behind Nginx/ALB |
| Observability | structlog, FastAPI native OpenTelemetry, Prometheus, Sentry |
| Quality | Ruff, mypy 2 strict, **import-linter**, custom AST lints, pre-commit |
| Auth | PyJWT + pwdlib[argon2] |
| i18n | Babel / gettext |
| Task runner | `just` (or Make/taskipy) with a fixed command vocabulary |
| Local dev | Docker Compose: Postgres, Redis, MinIO, Mailpit, (Prometheus/Grafana) |

## 2. Architecture (layered, feature-first, enforced)

```
app/
  main.py            # app factory, lifespan, middleware, versioned routers
  core/              # config, security, db, redis, logging, errors, i18n, telemetry
  common/            # base repository, mixins, Page[T], dependencies
  modules/
    orders/
      router.py  schemas.py  service.py  repository.py  models.py  dependencies.py
  api/v1/router.py  api/v2/router.py
  workers/           # celery tasks
  scheduler/         # cron definitions
  locales/{en,sw}/LC_MESSAGES/messages.po
migrations/
scripts/             # seed, check_migrations, linters
load_tests/          # locustfile.py
tests/
```
**Enforce layers with import-linter** in CI:
```toml
[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "Layered modules"
type = "layers"
layers = ["app.api", "app.modules", "app.common", "app.core"]

[[tool.importlinter.contracts]]
name = "Routers never touch the DB"
type = "forbidden"
source_modules = ["app.modules.*.router"]
forbidden_modules = ["sqlalchemy", "app.core.db"]
```
**Custom AST lint** (`scripts/linters/tenant_scope.py`): fails if a repository query on a tenant-scoped model lacks a `tenant_id` filter, or a list query has no `limit`.

## 3. Code standards

- Full type hints; mypy strict; no blanket `# type: ignore`.
- `OrderCreate` / `OrderUpdate` / `OrderOut`; `Annotated` dependencies.
- Small functions, early returns, no bare `except`.
- RFC 9457 Problem Details with stable `code`.
- `validate_default=True` where needed; PATCH uses `model_fields_set`.
- Money as integer minor units/`Decimal`; time aware UTC.
- `root_path` via CLI; don't touch `router.routes`.

### Core setup
```python
# core/config.py
class Settings(BaseSettings):
    environment: Literal["local", "staging", "production"] = "local"
    secret_key: SecretStr
    database_url: PostgresDsn

    @model_validator(mode="after")
    def _no_default_secrets(self) -> Self:
        if self.environment != "local" and self.secret_key.get_secret_value() in {"changethis", ""}:
            raise ValueError("SECRET_KEY must be set outside local")
        return self

# core/db.py
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)

engine = create_async_engine(
    str(settings.database_url),  # postgresql+psycopg://
    pool_size=20, max_overflow=10, pool_pre_ping=True, pool_recycle=1800,
    connect_args={"connect_timeout": 5, "application_name": f"api-{settings.environment}"},
)

@event.listens_for(engine.sync_engine, "begin")
def _statement_timeout(conn: Connection) -> None:
    conn.exec_driver_sql("SET LOCAL statement_timeout = '5s'")  # works with PgBouncer

# main.py
app = FastAPI(
    lifespan=lifespan,
    openapi_url="/openapi.json" if settings.environment != "production" else None,
)
```
(Use a longer timeout for workers/reports via a separate engine or `SET LOCAL` override.)

### Service example
```python
class OrderService:
    def __init__(self, repo: OrderRepository) -> None:
        self.repo = repo

    async def get_for_user(self, order_id: UUID, user: User) -> OrderOut:
        order = await self.repo.get(order_id)
        if order is None or (order.owner_id != user.id and not user.is_admin):
            raise NotFoundError(code="ORDER_NOT_FOUND")
        return OrderOut.model_validate(order)
```

### Dockerfile
```dockerfile
FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev
COPY . .
RUN uv sync --locked --no-dev

FROM python:3.14-slim
ARG APP_VERSION GIT_SHA
ENV APP_VERSION=$APP_VERSION GIT_SHA=$GIT_SHA
RUN useradd --system app
WORKDIR /app
COPY --from=builder --chown=app /app /app
ENV PATH="/app/.venv/bin:$PATH"
USER app
CMD ["fastapi", "run", "app/main.py", "--port", "8000", "--workers", "4", "--proxy-headers"]
```

## 4. Code reuse (without over-abstraction)

- `BaseRepository[ModelT]` (get, keyset `page`, create, update, soft delete).
- Mixins: `UUIDv7PKMixin`, `TimestampMixin`, `TenantMixin`, `SoftDeleteMixin` (`deleted_at`; default queries exclude deleted), `VersionMixin` (optimistic locking), `MetadataMixin` (bounded JSONB: ≤ 50 keys, key ≤ 40 chars, value ≤ 500 chars, validated).
- Shared schemas: `Page[T]`, `ProblemDetail`, `MoneyOut`.
- Dependencies: `CurrentUser`, `require_permission`, `PaginationDep`, `IdempotencyDep`, `LocaleDep`.
- Middleware for request id, locale, timing.
- Internal packages with SemVer for cross-service code; rule of three.

## 5. Performance & concurrency

- Never block the event loop; shared `httpx.AsyncClient`; CPU work to workers.
- Pool math: `workers × (pool_size + max_overflow) < max_connections`; PgBouncer.
- **Statement, connect and lock timeouts** on every connection; `application_name` per process type.
- No N+1; needed columns; indexes verified with `EXPLAIN ANALYZE`.
- Keyset pagination ≤ 100.
- Redis cache (keys include locale/version) + stampede protection.
- Timeouts, retries (idempotent only), circuit breakers.
- `202` + job id for slow work; JSON Lines/SSE streaming.
- **Presigned uploads**: client uploads directly to S3 (multipart for large files, SHA-256 checksum, TTL ≤ 10 min); API only issues the URL and confirms completion — files never pass through API workers. Validate type/size on confirm; scan if user-facing.
- Load tests with **Locust** (`load_tests/`) for critical endpoints before major releases; benchmarks for hot paths.

## 6. Background jobs & scheduling

- **Enqueue after commit**: jobs/events are buffered during the transaction and sent only after a successful commit (or via outbox) — never a job for rolled-back data.
- Jobs idempotent, retry-safe, dead-letter queue, `acks_late`, visibility timeout; time limits per task.
- Scheduler runs as its **own single process** (no duplicate cron firing); scheduled jobs take a Redis lock.
- Data-retention jobs delete/anonymize data past its retention period (PDPA).

## 7. Scalability

Stateless instances; health checks; graceful shutdown; read replicas; partitioning; outbox; multi-tenant `tenant_id` + RLS or enforced filter.

## 8. API versioning

- URL majors `/api/v1`, `/api/v2`; breaking vs non-breaking rules (removal/rename/type change/new required input/changed error codes = breaking).
- v2 adds routers/schemas only for changed endpoints; shared services; adapters for old schemas.
- `Deprecation` + `Sunset` + `Link` headers; keep old version 6–12 months; log usage per version/client.
- `X-App-Version` + `X-Platform`; `/api/v1/app-config` with min/latest versions; `426 Upgrade Required`.
- OpenAPI per version; typed clients regenerated in pre-commit/CI; contract tests per version; tests parametrized over supported versions.
- Versioned webhooks/events.

## 9. Localization (English + Swahili)

`LocaleDep` (profile → `Accept-Language` → default) + `Content-Language`; errors return `code` + localized `title`/`detail`; SMS/email/push/PDF via Babel catalogs (CI fails on untranslated entries); store `preferred_language`; language-neutral storage (UTC, integer TZS, E.164); format at the edge (`Africa/Dar_es_Salaam`); translatable user content via translations table/JSONB with fallback; translated validation messages.

### User preferences (theme, language)
`GET/PATCH /api/v1/me/preferences` stores UI preferences per user (JSONB `preferences` on the user or a `user_preferences` table) so web and mobile share them across devices: `{"locale": "sw", "theme": {"mode": "system|light|dark", "theme": "<preset id>|custom|default", "customColor": "#RRGGBB" | null}}`. Validate with Pydantic (enum for mode, regex for hex, max lengths); unknown preset ids fall back to `default` on the client. Never trust it for anything security-related.

## 10. Security (OWASP API Top 10 — 2023)

- Object- and property-level authorization; tenant-scope lint in CI.
- Argon2id (pwdlib); PyJWT (`alg` allow-list, `exp`, `iss`, `aud`); short access + rotating hashed refresh tokens.
- Permission dependencies; rate limits on login/OTP/payments; backoff.
- Parameterized queries; strict validation; body limits.
- CORS allow-list; security headers; TLS 1.2+.
- Secrets from a secret manager; default-secret guard; secret scanning in CI.
- SSRF protection; webhook signature + timestamp + idempotency; idempotency keys.
- **Audit log model** (`actor_id`, `action`, `target_type`, `target_id`, `tenant_id`, `ip`, `user_agent`, `metadata`, `created_at`) written in the same transaction for sensitive actions; append-only.
- Mask PII in logs; no stack traces in responses; OpenAPI hidden in production.
- Tanzania PDPA: PDPC registration, minimization, consent, encryption, retention jobs, breach procedure.

## 11. Release versioning & deployment

Service SemVer independent of API version; Conventional Commits → release-please → changelog + tag; images tagged version + SHA; promote the same image; `GET /version`; **migrations: expand → migrate → contract, CI-checked** (`scripts/check_migrations.py`: single Alembic head, date-prefixed revision files, no column drop in the same release that stops using it); pre-deploy migration job; rolling/blue-green/canary; feature flags; rollback runbook.

## 12. Operations

- **SLOs** per critical API (e.g. 99.9% availability, p95 < 300ms for reads) with error budgets; alert on symptoms (error rate, latency, queue age), not causes.
- Every alert links to a **runbook** in `docs/runbooks/`.
- Postgres backups with PITR; restore drill at least quarterly.
- Dashboards: RED metrics per endpoint, DB pool usage, queue depth/age, worker failures.

## 13. Developer experience

- `just` commands: `dev`, `worker`, `scheduler`, `test`, `test-fast`, `lint`, `typecheck`, `migrate`, `makemigration`, `seed`, `loadtest`, `gen-client`. Documented in README and `AGENTS.md`.
- `docker compose up` gives a full local stack; `scripts/prestart.sh` waits for DB and migrates; `just seed` loads realistic demo data (both languages).
- `.env.example` complete and current.
- pre-commit: ruff, ruff-format, mypy, typos, check-added-large-files, merge-conflict, debug-statements, blanket-type-ignore check, import-linter.
- uv `exclude-newer` cooldown (e.g. 7 days) for new releases.

## 14. API design

REST, plural nouns, versioned paths, correct status codes (201 + Location, 204, 400/401/403/404/409/422/426/429), Problem Details, `Request-Id` header, allow-listed filtering/sorting, `Page[T]` envelope (`items`, `next_cursor`), OpenAPI examples.

## 15. Definition of done

- [ ] Ruff, mypy strict, import-linter, custom lints clean
- [ ] Object/property-level authorization; tenant scope; audit log for sensitive actions
- [ ] Reused base repository/mixins/dependencies
- [ ] No blocking calls; timeouts (HTTP + DB)
- [ ] Indexed, paginated, no N+1
- [ ] Non-breaking for current API version (or new version with deprecation headers)
- [ ] Error codes stable; messages/SMS/email in `en` + `sw`
- [ ] Migration passes `check_migrations`, reversible, backward compatible
- [ ] Jobs enqueued after commit, idempotent
- [ ] Idempotency on money/order endpoints
- [ ] Tests per software-testing-expert; seeds updated
- [ ] OpenAPI, `.env.example`, runbook updated
- [ ] State any trade-off in one or two sentences
