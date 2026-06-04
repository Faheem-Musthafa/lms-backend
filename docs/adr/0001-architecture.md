# ADR-0001 — Modular Monolith, Hybrid Multi-Tenancy, Module Licensing

Status: Accepted · Date: 2026-06-04

## Context
Single deployment must serve many LMS clients (tenants). Clients buy different
module subsets (AUTH, COURSES, LEARNING, ASSIGNMENTS, DASHBOARD, ADMIN). Need
strong tenant isolation, per-tenant feature flags, and a clean road to extracting
modules into microservices later.

## Decisions

### 1. Modular monolith + DDD
One codebase, one process, one DB — but hard module boundaries.
- Each module = `models / schemas / repository / service / router / events / permissions`.
- **Modules never import another module's repository or models.** Cross-module reads
  go through the other module's *service* (a published interface) or via *domain events*.
- This boundary discipline is what makes future extraction cheap: a service interface
  becomes a network client; an event becomes a queue message — callers don't change.

### 2. Hybrid multi-tenancy (chosen: "best long-term")
Default = **shared database, shared schema, `tenant_id` discriminator** on every
business row. Isolation enforced at **three layers** (defense in depth):

1. **App context** — `TenantContext` (contextvar) set by middleware from the JWT
   `tid` claim (or `X-Tenant-ID` header pre-auth).
2. **Repository scoping** — `TenantRepository` injects `WHERE tenant_id = :ctx`
   into every query and stamps `tenant_id` on every insert. No query bypasses it.
3. **Postgres Row-Level Security** — RLS policies on all tenant tables keyed on
   `current_setting('app.tenant_id')`. The DB session runs `SET LOCAL app.tenant_id`
   per request. Even a buggy/forgotten filter cannot leak across tenants.

**Why "hybrid":** the model promotes to stronger isolation **without code changes**.
A heavy/regulated tenant can be moved to its own Postgres *schema* (or DB) by
switching `search_path` (or the connection) in `tenant_session()`; repositories and
RLS keep working unchanged. Small tenants stay cheap in the shared schema.

```
            ┌──────────── default ────────────┐   ┌──── promotable ────┐
 request → TenantContext → RLS (app.tenant_id) → shared schema  | tenant schema | tenant DB
```

### 3. Module licensing
`modules` (catalog) × `tenant_modules` (per-tenant enable flag). The
`@require_module("ASSIGNMENTS")` guard checks `tenant_has_module()` (Redis-cached)
before the handler runs → `403 {"error": "Module not enabled for tenant"}`.
Routers for a module are always mounted; the guard gates them at request time, so
enabling/disabling a module is a data change, never a deploy.

### 4. RBAC
Permission-based (`course:create`, `user:update`, …). Roles (Super Admin, Tenant
Admin, Instructor, Student) aggregate permissions. `@require_permission("course:create")`
resolves the caller's effective permissions (cached) and 403s on miss.

### 5. Events
In-process async event bus now (`event_bus.publish(...)`). Consumers update
dashboard read-models, write audit logs, fan out notifications. Interface is
outbox-ready: swap the in-proc dispatcher for a Redis-Streams / transactional-outbox
backend later — publishers and consumers don't change.

### 6. API gateway layer
Everything under `/api/v1/{module}/*`, one OpenAPI doc. MFEs (Auth, Catalog,
Learning, Assignment, Dashboard, Admin) consume the same surface.

## Consequences
- Strong isolation by default; per-tenant scaling path without rewrites.
- Module boundaries cost some indirection (service calls vs direct imports) — accepted.
- RLS adds a per-request `SET LOCAL`; negligible, and the safety is worth it.
