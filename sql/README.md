# Raw SQL schema

Generated from the SQLAlchemy models (`python -m scripts.dump_sql`). Equivalent
to Alembic migrations `0001` (schema) + `0002` (RLS) — use **one or the other**,
not both.

## Files (run in order)

| File | Contents |
|---|---|
| `01_schema.sql` | `pgcrypto` + 9 enum types + 25 tables + indexes (FK-dependency ordered) |
| `02_rls.sql` | Row-Level Security: `ENABLE`+`FORCE`+`tenant_isolation` policy on the 19 tenant-scoped tables |
| `03_seed_modules.sql` | Module catalog rows (AUTH…ADMIN). Data only. |
| `tables/<name>.sql` | One `CREATE TABLE` per table — reference; needs the enums/FKs from `01`. |

## Apply

```bash
psql "$DSN" -v ON_ERROR_STOP=1 -f sql/01_schema.sql
psql "$DSN" -v ON_ERROR_STOP=1 -f sql/02_rls.sql
psql "$DSN" -v ON_ERROR_STOP=1 -f sql/03_seed_modules.sql
```

Or in TablePlus: open each file in a SQL tab and Run (⌘↵), in order.

## Important

- **RLS uses `FORCE`** → the role that owns these tables is also subject to the
  policies. Whatever DB user the app connects as must own them (run these files
  as that user, e.g. `lms`).
- The app sets `app.tenant_id` / `app.bypass_rls` per transaction. A plain
  TablePlus session has neither set → RLS shows **0 rows** for tenant tables.
  To browse data, run first:
  ```sql
  SET app.bypass_rls = 'on';            -- see all tenants (admin view)
  -- or scope to one tenant:
  SET app.bypass_rls = 'off';
  SET app.tenant_id  = '<tenant-uuid>';
  ```
- **Users/roles/permissions can't be seeded in pure SQL** (passwords are
  argon2-hashed). Run `python -m scripts.seed` (or the `lms-seed` Cloud Run Job).
- If you create the schema with these files, tell Alembic the DB is current so
  future migrations apply cleanly:
  ```bash
  alembic stamp head
  ```
