# LMS Backend — Frontend Integration Summary

**Audience:** Frontend (MFE) team
**Backend:** Modular multi-tenant monolith — FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · Redis · JWT
**Status:** API surface complete and seeded; ready for FE integration.

---

## 1. The big picture

One backend deployment serves **many tenants (clients)**. Each tenant licenses a
different subset of **six modules**, and each module maps 1:1 to a **micro-frontend (MFE)**.

| Module | Code | Route prefix | Consuming MFE | Always on? |
|---|---|---|---|---|
| Authentication | `AUTH` | `/api/v1/auth` | Authentication | ✅ core |
| Course Catalog | `COURSES` | `/api/v1/courses` | Course Catalog | licensed |
| Learning | `LEARNING` | `/api/v1/learning` | Learning | licensed |
| Assignments | `ASSIGNMENTS` | `/api/v1/assignments` | Assignment | licensed |
| Dashboard | `DASHBOARD` | `/api/v1/dashboard` | Dashboard | licensed |
| Admin | `ADMIN` | `/api/v1/admin` | Admin | licensed |

**Every route is always served.** If a tenant has not licensed a module, calls to
it return `403 { "code": "module_not_enabled" }`. Enabling a module is a data change
(no deploy). FE implication: **drive MFE/nav visibility off the licensed-module list**,
and still handle `module_not_enabled` defensively.

- **Base URL (current dev deployment):** `https://pct-dual-comparisons-spotlight.trycloudflare.com`
  This is a Cloudflare Quick Tunnel. The subdomain changes on every `cloudflared`
  restart — backend team runs `scripts/update_tunnel.sh <new-url>` to swap it.
  For a stable URL, pin a named tunnel (see `docs/TUNNEL.md`) before production.
- **Base URL (local):** `http://localhost:8000` (uvicorn) · `http://lms.local` (nginx reverse proxy)
- **API prefix:** `/api/v1`
- **Interactive docs:** `/docs` (Swagger) · `/redoc` · machine-readable `/openapi.json`
- **Health:** `GET /health` (liveness) · `GET /health/ready` (DB + Redis check)

**Env var per MFE** (set in each `apps/<mfe>/.env.local`):
```
NEXT_PUBLIC_API_URL=https://pct-dual-comparisons-spotlight.trycloudflare.com
```

> Generate a typed client from `/openapi.json` (`openapi-typescript` / `orval`) rather
> than hand-writing types — the contract below is authoritative but the spec is canonical.

---

## 2. Tenancy — every request carries a tenant

- **Pre-auth** (login, register, refresh, forgot/reset password): send header
  `X-Tenant-ID: <slug-or-uuid>` (e.g. `full-lms`).
- **Post-auth**: the tenant is read from the JWT `tid` claim. **The JWT always wins** —
  a header can never escalate to another tenant. You can keep sending the header; it's ignored once authenticated.

Missing/unresolvable tenant on a pre-auth call → `400 { "code": "tenant_required" }`.

---

## 3. Auth & session model

JWT, two tokens:

| Token | TTL | Use |
|---|---|---|
| `access_token` | **900s (15 min)** | `Authorization: Bearer <token>` on every call |
| `refresh_token` | **30 days**, **rotating** | exchange at `/auth/refresh`; old token is revoked on use |

- Tokens carry **identity only** (`sub`, `tid`, `type`, `jti`). **Permissions are NOT in
  the token** — they're resolved per request, so role/permission changes and logout take
  effect immediately. Don't decode permissions client-side; call `/auth/me`.
- `/auth/refresh` **rotates**: the old refresh token is invalidated. Reusing it → `401`.
  Implement a single-flight refresh queue so concurrent 401s don't double-spend the token.

### Auth endpoints (`/api/v1/auth`, core — no license needed)

| Method | Path | Body | Returns | Notes |
|---|---|---|---|---|
| POST | `/register` | `{ email, password(≥8), full_name? }` | `UserOut` | self-service → **Student** role; needs `X-Tenant-ID` |
| POST | `/login` | `{ email, password }` | `TokenResponse` | rate-limited **10/min**; needs `X-Tenant-ID` |
| POST | `/refresh` | `{ refresh_token }` | `TokenResponse` | rotating |
| POST | `/logout` | `{ refresh_token? }` | `{ message }` | revokes the session |
| POST | `/forgot-password` | `{ email }` | `{ message }` | rate-limited 10/min; always 200 (no user enumeration) |
| POST | `/reset-password` | `{ token, new_password }` | `{ message }` | |
| GET | `/me` | — | `MeOut` | current user + roles + **resolved permissions** |

`TokenResponse`: `{ access_token, refresh_token, token_type: "bearer", expires_in: 900 }`
`MeOut`: `UserOut` + `permissions: string[]` (e.g. `["course:read","course:enroll",...]`)

---

## 4. RBAC — permission-based

Routes are gated by **permissions** (e.g. `course:create`), not role names. Roles just
bundle permissions. **Build the UI off `permissions` from `/auth/me`** (show/hide/disable
actions), but treat the server as the source of truth — a missing permission → `403 permission_denied`.

Seeded roles → permissions:

| Role | Permissions (summary) |
|---|---|
| **Super Admin** | everything, incl. `tenant:manage` (provision tenants, toggle modules) |
| **Tenant Admin** | everything **except** `tenant:manage` |
| **Instructor** | `course:read/create/update`, `category:manage`, `lesson:*`, `assignment:read/create/update`, `grade:read/write`, `progress:read`, `report:read`, `user:read`, `admin:access` |
| **Student** | `course:read`, `course:enroll`, `lesson:read`, `progress:read`, `assignment:read`, `assignment:submit`, `grade:read` |

---

## 5. Full endpoint reference

Required permission shown where one is enforced; otherwise any authenticated user.
All non-auth routes require a licensed module (per §1).

### Courses — `/api/v1/courses` (`COURSES`)
| Method | Path | Permission | Returns |
|---|---|---|---|
| GET | `/courses` **or** `/courses/` | auth | `Page<CourseOut>` — query: `search, level, status, is_free, category_id, page, size, sort` |
| GET | `/courses/{course_id}` | auth | `CourseDetailOut` |
| POST | `/courses/{course_id}/enroll` | `course:enroll` | `EnrollmentOut` — `201`; `409` if already enrolled |

### Learning — `/api/v1/learning` (`LEARNING`)
| Method | Path | Permission | Returns |
|---|---|---|---|
| GET | `/learning/courses/{course_id}/lessons` | `lesson:read` | `LessonOut[]` (incl. `video`/`document` assets) |
| POST | `/learning/lessons/{lesson_id}/complete` | auth | `LessonProgressOut` — body `{ last_position_seconds }` |
| GET | `/learning/progress` | `progress:read` | learner progress |

### Assignments — `/api/v1/assignments` (`ASSIGNMENTS`)
| Method | Path | Permission | Returns |
|---|---|---|---|
| GET | `/assignments` | `assignment:read` | `Page<AssignmentOut>` — query: `course_id, type, page, size` |
| GET | `/assignments/{assignment_id}` | `assignment:read` | `AssignmentOut` (incl. `quiz` w/ questions+answers) |
| POST | `/assignments/{assignment_id}/submit` | `assignment:submit` | `SubmissionOut` — body `{ content?, file_url?, answers? }`; **quizzes auto-grade** |
| POST | `/assignments/submissions/{submission_id}/grade` | `grade:write` | `GradeOut` — body `{ points, feedback? }` (manual grading) |
| GET | `/assignments/grades/me` | `grade:read` | my grades |

Quiz answers shape: `answers: { "<question_id>": ["<answer_id>", ...] }`.

### Dashboard — `/api/v1/dashboard` (`DASHBOARD`)
| Method | Path | Permission | Returns |
|---|---|---|---|
| GET | `/dashboard` **or** `/dashboard/` | auth | `DashboardOut` — `{ enrolled_courses, completed_lessons, pending_assignments, submissions, recent_activity[] }` |

### Admin — `/api/v1/admin` (`ADMIN`)
| Method | Path | Permission |
|---|---|---|
| POST | `/admin/courses` | `course:create` |
| PUT | `/admin/courses/{course_id}` | `course:update` (publish via `{ "status": "published" }`) |
| DELETE | `/admin/courses/{course_id}` | `course:delete` (soft delete) |
| GET | `/admin/users` | `user:read` |
| POST | `/admin/users` | `user:create` (body incl. `role_codes[]`) |
| PUT | `/admin/users/{user_id}` | `user:update` |
| GET | `/admin/reports` | `report:read` |
| POST | `/admin/tenants` | `tenant:manage` (super admin — provision tenant + modules) |
| GET | `/admin/tenants/{tenant_id}/modules` | `tenant:manage` |
| PUT | `/admin/tenants/{tenant_id}/modules` | `tenant:manage` (toggle a module at runtime) |

---

## 6. Response & error conventions

**Pagination envelope** (`Page<T>`):
```json
{ "items": [ ... ], "total": 42, "page": 1, "size": 20, "pages": 3 }
```
Query params: `page` (≥1, default 1), `size` (1–100, default 20), `search` (≤200 chars),
`sort` (`field` or `-field` for desc).

**Error envelope** (every error, consistent):
```json
{ "error": "human message", "code": "machine_code", "request_id": "...", "details": ... }
```
Branch on `code`, surface `request_id` in bug reports. `details` carries field errors on `422`.

| Code | HTTP | Meaning / FE action |
|---|---|---|
| `unauthenticated` | 401 | no/expired access token → refresh, else route to login |
| `permission_denied` | 403 | user lacks the permission → hide/disable the action |
| `module_not_enabled` | 403 | tenant hasn't licensed the module → hide the MFE |
| `tenant_required` | 400 | missing `X-Tenant-ID` on a pre-auth call |
| `not_found` | 404 | |
| `conflict` | 409 | e.g. duplicate enrollment |
| `validation_error` | 422 | `details` = field errors |
| `rate_limited` | 429 | back off (see §7) |

---

## 7. Cross-cutting FE notes

- **CORS** (current config):
  - Exact allow list: `http://localhost:3000`, `http://localhost:5173`, `https://pct-dual-comparisons-spotlight.trycloudflare.com`
  - Regex: `https://([a-z0-9-]+\.)?(lms-mf-es-shell\.vercel\.app|trycloudflare\.com)$` —
    matches the naked shell domain, any tenant subdomain (`abc-academy.lms-mf-es-shell.vercel.app`),
    and any Cloudflare quick tunnel.
  - `allow_credentials: true`; custom headers `X-Tenant-ID` and `Authorization` are whitelisted.
  - Adding a new origin: either append to `CORS_ORIGINS` in `.env` (restart backend), or widen
    `CORS_ORIGIN_REGEX` to cover your production domain.
- **Rate limits** (Redis-backed): default **100/min**, auth endpoints **10/min**. Handle `429`.
- **IDs** are UUIDs. **Money** (`price`, `points`) is serialized as a **string decimal**
  (e.g. `"10.00"`) — parse, don't treat as float.
- **Timestamps** are ISO-8601 UTC.
- **Soft deletes** — deleted resources disappear from lists rather than hard-delete.
- **Domain events / audit** are server-side; `recent_activity` in the dashboard is the
  FE-visible slice.

---

## 8. Local dev & seeded test data

```bash
cp .env.example .env          # set JWT_SECRET_KEY: openssl rand -hex 32
# Prereqs: PostgreSQL running locally, uv installed
make migrate                  # apply Alembic migrations
make seed                     # load demo tenants/users/roles
make dev                      # uvicorn on http://localhost:8000 (reload)
```

For remote access from MFEs deployed on Vercel, backend team runs:
```bash
cloudflared tunnel --url http://localhost:8000
./scripts/update_tunnel.sh https://<new-subdomain>.trycloudflare.com
```

Seeded tenants (send `X-Tenant-ID: <slug>`):

| Tenant slug | Licensed modules | Test users (password) |
|---|---|---|
| `abc-academy` | AUTH, COURSES, LEARNING | `admin@abc-academy.com` (`Admin123!`), `instructor@…`, `student@…` |
| `full-lms` | all six | `admin@full-lms.com`, `student@full-lms.com` (`Learn123!`), `root@platform.com` (`Root123!`, super admin) |

Good licensing smoke test: `abc-academy` user hitting `/api/v1/assignments` → `403 module_not_enabled`;
same call as a `full-lms` user → `200`.

End-to-end curl flows: [`docs/API_EXAMPLES.md`](API_EXAMPLES.md). Design rationale:
[`docs/adr/0001-architecture.md`](adr/0001-architecture.md).

---

## 9. Recommended FE integration order

1. **Auth shell** — login/register/refresh/logout, token storage, single-flight refresh, `401` interceptor.
2. **`/auth/me` bootstrap** — cache `roles` + `permissions` + licensed modules; drive nav/MFE mounting and action gating.
3. **Global error handling** — map the error `code` table to toasts/redirects; carry `request_id`.
4. **Per-MFE wiring** — Courses → Learning → Assignments → Dashboard → Admin, generating types from `/openapi.json`.

**Open items to confirm with us:** production base URL (once you move off the quick tunnel — see `docs/TUNNEL.md`).

---

## 10. Quick-start smoke test (copy-paste)

Set the tunnel URL once:
```bash
export LMS_API=https://pct-dual-comparisons-spotlight.trycloudflare.com
export TENANT=abc-academy
```

**Health:**
```bash
curl $LMS_API/health
# {"status":"ok"}
```

**Login (returns access + refresh token):**
```bash
curl -X POST $LMS_API/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: $TENANT" \
  -d '{"email":"admin@abc-academy.com","password":"Admin123!"}'
```

**Authenticated request:**
```bash
TOKEN=<paste access_token>
curl $LMS_API/api/v1/auth/me -H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: $TENANT"
curl $LMS_API/api/v1/courses/ -H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: $TENANT"
```

**Licensing smoke test (expect 403 vs 200):**
```bash
# abc-academy doesn't license ASSIGNMENTS:
curl -o /dev/null -w "%{http_code}\n" $LMS_API/api/v1/assignments \
  -H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: $TENANT"    # → 403

# full-lms licenses everything:
FULL_TOKEN=$(curl -s -X POST $LMS_API/api/v1/auth/login \
  -H "Content-Type: application/json" -H "X-Tenant-ID: full-lms" \
  -d '{"email":"student@full-lms.com","password":"Learn123!"}' | jq -r .access_token)
curl -o /dev/null -w "%{http_code}\n" $LMS_API/api/v1/assignments \
  -H "Authorization: Bearer $FULL_TOKEN" -H "X-Tenant-ID: full-lms"   # → 200
```
