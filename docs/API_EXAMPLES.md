# API examples

Base URL: `http://localhost:8000/api/v1`. All requests carry a tenant:
pre-auth via `X-Tenant-ID: <slug-or-uuid>`, post-auth via the JWT `tid` claim
(the JWT wins — a header can't escalate to another tenant).

Responses below are abbreviated. Full contract: `GET /openapi.json` or `/docs`.

---

## 1. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-ID: full-lms' \
  -d '{"email":"student@full-lms.com","password":"Learn123!"}'
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

Use the access token on every subsequent call: `-H "Authorization: Bearer <access_token>"`.

## 2. Register (self-service → Student role)

```bash
curl -X POST .../auth/register -H 'X-Tenant-ID: full-lms' \
  -H 'Content-Type: application/json' \
  -d '{"email":"new@full-lms.com","password":"Passw0rd!","full_name":"New User"}'
```

## 3. Current user (roles + resolved permissions)

```bash
curl .../auth/me -H "Authorization: Bearer $AT"
```

```json
{
  "id": "…", "email": "student@full-lms.com", "tenant_id": "…",
  "roles": [{"code": "student", "name": "Student"}],
  "permissions": ["assignment:read","assignment:submit","course:enroll",
                  "course:read","grade:read","lesson:read","progress:read"]
}
```

## 4. Refresh (rotating) / logout

```bash
curl -X POST .../auth/refresh -H 'X-Tenant-ID: full-lms' \
  -H 'Content-Type: application/json' -d '{"refresh_token":"'"$RT"'"}'
# old refresh token is revoked on use (rotation). 401 if reused.

curl -X POST .../auth/logout -H 'Content-Type: application/json' \
  -d '{"refresh_token":"'"$RT"'"}'
```

## 5. Course catalog (search + filters + pagination)

```bash
curl ".../courses?search=python&level=beginner&page=1&size=20" \
  -H "Authorization: Bearer $AT"
```

```json
{"items":[{"id":"…","title":"Python for Beginners","status":"published", "...":""}],
 "total":1,"page":1,"size":20,"pages":1}
```

## 6. Enroll

```bash
curl -X POST .../courses/$COURSE_ID/enroll -H "Authorization: Bearer $AT"
# 201 EnrollmentOut · 409 if already enrolled · publishes CourseEnrolledEvent
```

## 7. Lessons + progress (Learning)

```bash
curl .../learning/courses/$COURSE_ID/lessons -H "Authorization: Bearer $AT"
curl -X POST .../learning/lessons/$LESSON_ID/complete \
  -H "Authorization: Bearer $AT" -H 'Content-Type: application/json' \
  -d '{"last_position_seconds": 540}'
curl .../learning/progress -H "Authorization: Bearer $AT"
```

## 8. Quiz submission → auto-grading (Assignments)

```bash
curl -X POST .../assignments/$ASSIGNMENT_ID/submit \
  -H "Authorization: Bearer $AT" -H 'Content-Type: application/json' \
  -d '{"answers": {"<question_id>": ["<answer_id>"]}}'
```

```json
{"id":"…","status":"graded",
 "grade":{"points":"10.00","max_points":"10.00","is_auto":true}}
```

Manual grading (needs `grade:write`):

```bash
curl -X POST .../assignments/submissions/$SUBMISSION_ID/grade \
  -H "Authorization: Bearer $INSTRUCTOR_AT" -H 'Content-Type: application/json' \
  -d '{"points": 8, "feedback": "Good work"}'
```

## 9. Dashboard (aggregated read model)

```bash
curl .../dashboard -H "Authorization: Bearer $AT"
```

```json
{"enrolled_courses":1,"completed_lessons":2,"pending_assignments":1,
 "submissions":1,"recent_activity":[{"action":"auth.login","resource":"user","...":""}]}
```

## 10. Admin — course & user management (RBAC-gated)

```bash
# create course (course:create)
curl -X POST .../admin/courses -H "Authorization: Bearer $ADMIN_AT" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Advanced Python","slug":"advanced-python","level":"advanced"}'

# publish it
curl -X PUT .../admin/courses/$COURSE_ID -H "Authorization: Bearer $ADMIN_AT" \
  -H 'Content-Type: application/json' -d '{"status":"published"}'

# create user with roles (user:create)
curl -X POST .../admin/users -H "Authorization: Bearer $ADMIN_AT" \
  -H 'Content-Type: application/json' \
  -d '{"email":"teacher@full-lms.com","password":"Passw0rd!","role_codes":["instructor"]}'

# tenant report (report:read)
curl .../admin/reports -H "Authorization: Bearer $ADMIN_AT"
```

## 11. Module licensing administration (super admin — `tenant:manage`)

```bash
# provision a new tenant with a module subscription
curl -X POST .../admin/tenants -H "Authorization: Bearer $ROOT_AT" \
  -H 'Content-Type: application/json' \
  -d '{"name":"New Client","slug":"new-client","modules":["COURSES","LEARNING"]}'

# inspect a tenant's module flags
curl .../admin/tenants/$TENANT_ID/modules -H "Authorization: Bearer $ROOT_AT"

# enable/disable a module at runtime (no deploy)
curl -X PUT .../admin/tenants/$TENANT_ID/modules -H "Authorization: Bearer $ROOT_AT" \
  -H 'Content-Type: application/json' -d '{"code":"ASSIGNMENTS","enabled":true}'
```

## Error envelope

```json
{ "error": "Module not enabled for tenant", "code": "module_not_enabled",
  "request_id": "…" }
```

Common codes: `unauthenticated` (401) · `permission_denied` (403) ·
`module_not_enabled` (403) · `not_found` (404) · `conflict` (409) ·
`validation_error` (422) · `rate_limited` (429).
