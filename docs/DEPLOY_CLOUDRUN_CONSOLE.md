# Deploy to Cloud Run — GCP Console (web)

Deploy the API + the migrate Job through the browser. Assumes the prereqs from
`docs/DEPLOY_GCP.md` exist: **Cloud SQL** (`lms-pg`, db `lms`, user `lms`),
**Memorystore** (`lms-redis`) + **Serverless VPC connector** (`lms-conn`),
**Secret Manager** secrets `lms-database-url` and `lms-jwt-secret`, and a runtime
**service account** `lms-run` with `cloudsql.client` + `secretmanager.secretAccessor`.

> The container listens on `$PORT` (Cloud Run sets 8080) — already handled in the
> Dockerfile. Keep the Cloud Run **container port = 8080**.

---

## 1. Get the image into Artifact Registry

Open **Cloud Shell** (terminal icon, top-right of the console) — it's part of the
web console — then:

```bash
gcloud config set project PROJECT_ID
gcloud artifacts repositories create lms --repository-format=docker --location=REGION  # once
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT_ID/lms/lms-backend:v1
```

(Skip this and use **Deploy from source** in step 2B to build from a connected
Git repo instead.)

## 2A. Create the service — from the image

1. Console → **Cloud Run** → **Deploy container → Service**.
2. **Container image URL** → *Select* → Artifact Registry →
   `lms/lms-backend:v1`.
3. **Service name** `lms-api`, **Region** = your region.
4. **Authentication**: ✅ *Allow unauthenticated invocations* (MFEs call it;
   auth is the app's JWT).
5. **Billing**: Request-based. **Ingress**: All.
6. Expand **Container(s), Volumes, Networking, Security**:
   - **Container** tab → **Container port** `8080`.
   - **Resources** → Memory `512 MiB`, CPU `1`.
   - **Variables & Secrets** tab:
     - **Environment variables** (Add for each):
       | Name | Value |
       |---|---|
       | `ENVIRONMENT` | `production` |
       | `WEB_CONCURRENCY` | `1` |
       | `DB_POOL_SIZE` | `5` |
       | `DB_MAX_OVERFLOW` | `5` |
       | `REDIS_URL` | `redis://REDIS_HOST:6379/0` |
       | `CORS_ORIGINS` | `https://app.example.com` |
     - **Secrets exposed as environment variables** (Reference a secret):
       | Env name | Secret | Version |
       |---|---|---|
       | `DATABASE_URL` | `lms-database-url` | latest |
       | `JWT_SECRET_KEY` | `lms-jwt-secret` | latest |
   - **Settings** tab → **Service account** → `lms-run`.
   - **Networking** tab → ✅ *Connect to a VPC for outbound traffic* → use
     Serverless VPC connector `lms-conn` → *Route only requests to private IPs*
     (lets Cloud Run reach Memorystore).
   - **Security/Connections** → **Cloud SQL connections** → *Add connection* →
     `lms-pg`.
   - (Optional) **Container → Health checks** → add **Startup probe**, HTTP,
     path `/health/ready`, port `8080` — traffic waits until DB+Redis are up.
7. **Autoscaling**: Min instances `1`, Max instances `10`. **Request concurrency**
   `80`.
8. **Create**. Console may prompt to grant the secret-accessor role — accept.

## 2B. Alternative — Deploy from source (build from Git)

1. Cloud Run → **Deploy container → Service** → *Deploy one revision from a source
   repository* → **Set up with Cloud Build**.
2. Connect GitHub/Cloud Source repo + branch. Build type: **Dockerfile**.
3. Fill the same service settings as 2A (step 4–8). Each push to the branch
   rebuilds + redeploys.

## 3. Run migrations — Cloud Run Job (Console)

Do this **before** serving traffic on a release that adds migrations.

1. Cloud Run → **Jobs** → **Create job**.
2. **Container image** = same `lms-backend:v1`. **Job name** `lms-migrate`,
   **Region** = same.
3. **Container → Command** = `alembic`, **Arguments** = `upgrade` and `head`
   (two separate argument entries).
4. **Variables & Secrets** → env `ENVIRONMENT=production`; secret
   `DATABASE_URL` = `lms-database-url:latest`.
5. **Connections** → Cloud SQL → add `lms-pg`. (No VPC/Redis needed for migrate.)
6. **Settings** → Service account `lms-run`. **Create**.
7. Open the job → **Execute**. Wait for success.

> Seed (users/roles): create a second Job `lms-seed` the same way, but
> Command `python`, Args `-m` + `scripts.seed`, and **add** the VPC connector +
> `REDIS_URL` env (seed touches Redis). Execute once.

## 4. Verify

Service page → copy the **URL**, then in Cloud Shell:

```bash
curl -s "$URL/health/ready"            # {"status":"ready"} = DB + Redis reachable
curl -s -X POST "$URL/api/v1/auth/login" -H 'Content-Type: application/json' \
  -H 'X-Tenant-ID: full-lms' -d '{"email":"student@full-lms.com","password":"Learn123!"}'
```

Docs UI: `https://<service-url>/docs`.

## 5. New releases

Build a new tag (`:v2`) → Cloud Run service → **Edit & deploy new revision** →
pick the new image → Deploy. Run the `lms-migrate` Job first if the release adds
migrations. With 2B (source deploy) this is automatic on push.

## Gotchas

- **Container port must be 8080** (Cloud Run's `$PORT`); the app honors it.
- **Cloud SQL** = add via *Cloud SQL connections* (mounts the `/cloudsql/...`
  socket the `DATABASE_URL` secret points at) — not the VPC connector.
- **Redis** = needs the **VPC connector** (private IP). Without it `/health/ready`
  fails and every request errors (licensing/rate-limit hit Redis).
- **min-instances ≥ 1** avoids cold starts on the login path.
- Connection budget: `DB_POOL_SIZE × WEB_CONCURRENCY × max-instances ≤ Cloud SQL
  max_connections` (here 5×1×10 = 50).
