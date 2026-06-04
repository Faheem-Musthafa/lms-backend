# LMS Backend — Modular Multi-Tenant Monolith

Production-ready backend powering an MFE-based LMS. One deployment serves many
tenants (clients), each licensing a different subset of modules. Built as a
**modular monolith** with **DDD** boundaries so modules can be extracted into
microservices later with minimal churn.

- **Stack:** Python 3.13+, FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL,
  Redis, JWT.
- **Patterns:** modular monolith · DDD · API-first · CQRS read side (dashboard)
  · domain events · hybrid multi-tenancy with Postgres RLS.

See [`docs/adr/0001-architecture.md`](docs/adr/0001-architecture.md) for the
full design rationale.

---

## Modules → MFEs

| Module | Code | Route prefix | Consuming MFE | Core? |
|---|---|---|---|---|
| Authentication | `AUTH` | `/api/v1/auth` | Authentication | ✅ always on |
| Course Catalog | `COURSES` | `/api/v1/courses` | Course Catalog | licensed |
| Learning | `LEARNING` | `/api/v1/learning` | Learning | licensed |
| Assignments | `ASSIGNMENTS` | `/api/v1/assignments` | Assignment | licensed |
| Dashboard | `DASHBOARD` | `/api/v1/dashboard` | Dashboard | licensed |
| Admin | `ADMIN` | `/api/v1/admin` | Admin | licensed |

Every module router is **always mounted**. A `require_module(...)` dependency
gates non-core modules at request time, so enabling/disabling a module for a
tenant is a **data change, not a deploy** → `403 {"error": "Module not enabled
for tenant"}`.

## Three-layer tenant isolation (hybrid)

Default = shared schema + `tenant_id` discriminator. Enforced at three layers:

1. **Request context** (`contextvar`) — tenant resolved from the JWT `tid` claim
   (post-auth) or the `X-Tenant-ID` header (pre-auth).
2. **Repository** — `TenantRepository` auto-filters every read by `tenant_id`
   and stamps it on every write.
3. **Postgres RLS** — `FORCE`d policies keyed on `app.tenant_id` (set per
   request transaction). Even a forgotten filter can't leak across tenants.

Promotion path (no code change): move a heavy tenant to its own schema/DB by
switching `search_path`/connection in `tenant_session()`; repositories + RLS are
unchanged.

## Layout

```
app/
  core/          # config, db (base/session/repository), security, events,
                 # licensing, audit, tenancy, middleware, cache
  modules/       # auth, courses, learning, assignments, dashboard, admin
                 #   each: models · schemas · repository · service · router
                 #         · events · permissions
  shared/        # schemas (pagination/envelopes), exceptions
  api/router.py  # /api/v1 gateway — mounts modules + module guards
  registry.py    # imports all models + registers event handlers
  main.py        # app factory, middleware, exception handlers, health
alembic/         # 0001 schema · 0002 RLS policies
scripts/seed.py  # demo tenants/roles/users/content
tests/           # unit + integration
docs/            # ADR, OpenAPI export, API examples
```

## Quick start (Docker)

```bash
cp .env.example .env          # then set JWT_SECRET_KEY: openssl rand -hex 32
docker compose up -d --build  # db, redis, minio, migrate, seed, api
# API:   http://localhost:8000
# Docs:  http://localhost:8000/docs   (ReDoc at /redoc)
```

`migrate` runs `alembic upgrade head`; `seed` loads demo data; `api` serves.

## Quick start (local, uv)

```bash
uv sync
# start Postgres + Redis (or `docker compose up -d db redis`)
uv run alembic upgrade head
uv run python -m scripts.seed
make dev                      # uvicorn --reload on :8000
make test                     # pytest (needs DB + Redis)
make lint typecheck
```

## Seeded demo (send header `X-Tenant-ID: <slug>`)

| Tenant (slug) | Licensed modules | Users (password) |
|---|---|---|
| `abc-academy` | AUTH, COURSES, LEARNING | `admin@abc-academy.com` (Admin123!), `instructor@…`, `student@…` |
| `full-lms` | all six | `admin@full-lms.com`, `student@full-lms.com` (Learn123!), `root@platform.com` (Root123!, super admin) |

Try: `abc-academy` user hitting `/api/v1/assignments` → `403 module_not_enabled`;
the same call as a `full-lms` user → `200`.

See [`docs/API_EXAMPLES.md`](docs/API_EXAMPLES.md) for end-to-end curl flows.

## Roles & permissions (RBAC)

Permission-based (`course:create`, `user:update`, …). Roles aggregate
permissions; `@require_permission("course:create")` gates routes. Seeded roles:
Super Admin, Tenant Admin, Instructor, Student. Permissions are resolved
per-request (never trusted from the token) so changes take effect immediately.

## Events & audit

Services publish domain events (`CourseEnrolledEvent`, `LessonCompletedEvent`,
`AssignmentSubmittedEvent`, `UserLoggedInEvent`, …) on an in-process async bus.
A universal consumer writes `audit_logs` for any event exposing an `audit()`
descriptor; the dashboard read-model aggregates across modules. The bus
interface is outbox-ready (swap to Redis Streams later without touching
publishers/consumers).

## Non-functional

OpenAPI docs · typed Pydantic v2 schemas · Alembic migrations · RLS tenant
security · audit logging · soft deletes · pagination + search · Redis rate
limiting · JWT auth (access + rotating refresh) · production Docker.
