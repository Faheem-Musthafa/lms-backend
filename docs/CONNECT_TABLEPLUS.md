# Cloud SQL via the GCP Console + TablePlus

Create the Postgres instance in the **GCP web console**, connect with
**TablePlus**, then apply the raw schema from `sql/`.

## A. Create Cloud SQL (Console)

1. Console → **SQL** → **Create instance** → **PostgreSQL**.
2. Instance ID `lms-pg`, set a **postgres** password, **PostgreSQL 16**, region
   (match Cloud Run, e.g. `us-central1`).
3. Edition/preset: Enterprise, **Sandbox/Lightweight** for dev (1 vCPU / 3.75 GB).
4. **Connections**:
   - Keep **Public IP** ON for TablePlus access (or use the Auth Proxy below and
     leave it off).
   - **SSL**: set "Allow only SSL connections" (recommended).
5. Create. Wait for green check.
6. **Databases** tab → **Create database** → name `lms`.
7. **Users** tab → **Add user account** → `lms` + password.
8. Note the **Connection name** on the Overview page: `PROJECT:REGION:lms-pg`.

### One-time grant (so `lms` can create the schema + own it for FORCE-RLS)
Console → instance → **Cloud Shell** (or `gcloud sql connect lms-pg --user=postgres --database=lms`):
```sql
GRANT ALL ON SCHEMA public TO lms;
ALTER SCHEMA public OWNER TO lms;
```

## B. Connect TablePlus

### Option 1 — Cloud SQL Auth Proxy (recommended; no public IP/whitelist)
```bash
# download once: https://cloud.google.com/sql/docs/postgres/sql-proxy
gcloud auth application-default login
./cloud-sql-proxy PROJECT:REGION:lms-pg --port 5432   # listens on 127.0.0.1:5432
```
TablePlus → **New → PostgreSQL**:
- Host `127.0.0.1`, Port `5432`
- User `lms`, Password `<lms password>`, Database `lms`
- SSL mode **OFF** (the proxy encrypts the tunnel) → **Test** → **Connect**

### Option 2 — Public IP + Authorized network
1. Console → instance → **Connections → Networking → Authorized networks →
   ADD NETWORK** → your current IP `x.x.x.x/32` → Save.
2. Copy the instance **Public IP** from Overview.
3. TablePlus → New → PostgreSQL:
   - Host `<public-ip>`, Port `5432`, User `lms`, Password, Database `lms`
   - SSL mode **Require** (or **Verify-CA** with the `server-ca.pem` downloaded
     from **Connections → Security**) → **Connect**

## C. Apply the schema in TablePlus

Connected to the `lms` database, run in order (⌘O to open a file into a SQL tab,
⌘↵ to run all):

1. `sql/01_schema.sql`   — enums + tables + indexes
2. `sql/02_rls.sql`      — row-level-security policies
3. `sql/03_seed_modules.sql` — module catalog

Then seed users/roles (argon2 — not doable in SQL):
```bash
DATABASE_URL=postgresql+asyncpg://lms:PASS@127.0.0.1:5432/lms \
REDIS_URL=redis://localhost:6379/0 \
python -m scripts.seed
```

### Browsing tenant data in TablePlus
RLS hides everything unless the session GUCs are set:
```sql
SET app.bypass_rls = 'on';                       -- admin: see all tenants
-- or scope to one tenant:
SET app.bypass_rls = 'off';
SET app.tenant_id  = '00000000-0000-0000-0000-000000000000';
```

### If you used these SQL files instead of Alembic
Mark the DB as migrated so future migrations apply cleanly:
```bash
alembic stamp head
```
