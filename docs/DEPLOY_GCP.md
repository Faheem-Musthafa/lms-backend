# Deploy to GCP — Cloud Run + Cloud SQL + Memorystore

Topology: **Cloud Run** (API service + migrate/seed Jobs) → **Cloud SQL**
(Postgres, via the built-in Cloud SQL connector unix socket) + **Memorystore**
(Redis, via a Serverless VPC Access connector). Secrets in **Secret Manager**,
image in **Artifact Registry**.

```
            ┌─────────── Secret Manager (DATABASE_URL, JWT_SECRET_KEY)
 Internet → Cloud Run (lms-api) ─ unix socket /cloudsql/CONN ─→ Cloud SQL (Postgres)
                    └─ VPC connector ─ private IP ─→ Memorystore (Redis)
 Cloud Run Jobs: lms-migrate (alembic upgrade head), lms-seed (python -m scripts.seed)
```

> The app needs **both** Postgres (RLS-enforced tenancy) and Redis (licensing
> cache, rate limiting, reset tokens — `/health/ready` pings both).

---

## 0. Variables (edit, then paste into your shell)

```bash
export PROJECT_ID=my-lms-project
export REGION=us-central1
export AR_REPO=lms
export IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/lms-backend:v1"

export SQL_INSTANCE=lms-pg
export DB_NAME=lms
export DB_USER=lms

export REDIS_INSTANCE=lms-redis
export VPC_CONNECTOR=lms-conn

export SERVICE=lms-api
export RUNTIME_SA="lms-run@$PROJECT_ID.iam.gserviceaccount.com"
```

## 1. Project + APIs

```bash
gcloud config set project "$PROJECT_ID"
gcloud services enable \
  run.googleapis.com sqladmin.googleapis.com artifactregistry.googleapis.com \
  cloudbuild.googleapis.com secretmanager.googleapis.com redis.googleapis.com \
  vpcaccess.googleapis.com compute.googleapis.com
```

## 2. Build + push image (Artifact Registry + Cloud Build)

```bash
gcloud artifacts repositories create "$AR_REPO" \
  --repository-format=docker --location="$REGION"

# builds with the repo Dockerfile (respects .gcloudignore)
gcloud builds submit --tag "$IMAGE"
```

## 3. Cloud SQL (Postgres)

```bash
gcloud sql instances create "$SQL_INSTANCE" \
  --database-version=POSTGRES_16 --region="$REGION" \
  --tier=db-custom-1-3840 --storage-type=SSD --storage-size=10GB \
  --availability-type=zonal           # use --availability-type=regional for prod HA

gcloud sql databases create "$DB_NAME" --instance="$SQL_INSTANCE"

# DB password without URL-special chars (avoids encoding in the URL)
export DB_PASS="$(openssl rand -base64 24 | tr -d '/+=')"
gcloud sql users create "$DB_USER" --instance="$SQL_INSTANCE" --password="$DB_PASS"

export CONN_NAME="$(gcloud sql instances describe "$SQL_INSTANCE" --format='value(connectionName)')"
echo "$CONN_NAME"                       # → PROJECT:REGION:INSTANCE
```

**Grant the app user schema rights (one-time).** On Postgres 15+ a non-superuser
can't create objects in `public` by default — and the app user must *own* the
tables so `FORCE ROW LEVEL SECURITY` governs it.

```bash
gcloud sql users set-password postgres --instance="$SQL_INSTANCE" --prompt-for-password
gcloud sql connect "$SQL_INSTANCE" --user=postgres --database="$DB_NAME"
```
```sql
-- in the psql prompt:
GRANT ALL ON SCHEMA public TO lms;
ALTER SCHEMA public OWNER TO lms;   -- lms owns objects → FORCE RLS applies to it
\q
```

## 4. Memorystore (Redis) + VPC connector

```bash
gcloud redis instances create "$REDIS_INSTANCE" \
  --region="$REGION" --tier=basic --size=1 --redis-version=redis_7_0

export REDIS_HOST="$(gcloud redis instances describe "$REDIS_INSTANCE" \
  --region="$REGION" --format='value(host)')"
echo "$REDIS_HOST"

# Serverless VPC connector so Cloud Run reaches Memorystore's private IP.
# /28 range must not overlap anything in the 'default' network.
gcloud compute networks vpc-access connectors create "$VPC_CONNECTOR" \
  --region="$REGION" --network=default --range=10.8.0.0/28
```

## 5. Secrets

```bash
# Full async DB URL (unix socket). config derives the sync/alembic URL from it.
printf 'postgresql+asyncpg://%s:%s@/%s?host=/cloudsql/%s' \
  "$DB_USER" "$DB_PASS" "$DB_NAME" "$CONN_NAME" \
  | gcloud secrets create lms-database-url --data-file=-

openssl rand -hex 32 | gcloud secrets create lms-jwt-secret --data-file=-
```

## 6. Runtime service account + IAM

```bash
gcloud iam service-accounts create lms-run --display-name="LMS Cloud Run runtime"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$RUNTIME_SA" --role="roles/cloudsql.client"

for S in lms-database-url lms-jwt-secret; do
  gcloud secrets add-iam-policy-binding "$S" \
    --member="serviceAccount:$RUNTIME_SA" --role="roles/secretmanager.secretAccessor"
done
```

## 7. Migrate (Cloud Run Job)

Migrations need Postgres only (no Redis, no JWT).

```bash
gcloud run jobs create lms-migrate \
  --image="$IMAGE" --region="$REGION" \
  --service-account="$RUNTIME_SA" \
  --set-cloudsql-instances="$CONN_NAME" \
  --set-secrets=DATABASE_URL=lms-database-url:latest \
  --set-env-vars=ENVIRONMENT=production \
  --command=alembic --args=upgrade,head \
  --max-retries=1 --task-timeout=600

gcloud run jobs execute lms-migrate --region="$REGION" --wait
```

## 8. Seed (Cloud Run Job, optional, idempotent)

Seed touches Postgres **and** Redis → needs the VPC connector + `REDIS_URL`.

```bash
gcloud run jobs create lms-seed \
  --image="$IMAGE" --region="$REGION" \
  --service-account="$RUNTIME_SA" \
  --set-cloudsql-instances="$CONN_NAME" \
  --vpc-connector="$VPC_CONNECTOR" --vpc-egress=private-ranges-only \
  --set-secrets=DATABASE_URL=lms-database-url:latest \
  --set-env-vars=ENVIRONMENT=production,REDIS_URL=redis://$REDIS_HOST:6379/0 \
  --command=python --args=-m,scripts.seed \
  --max-retries=0 --task-timeout=600

gcloud run jobs execute lms-seed --region="$REGION" --wait
```

## 9. Deploy the API (Cloud Run service)

```bash
gcloud run deploy "$SERVICE" \
  --image="$IMAGE" --region="$REGION" --platform=managed \
  --service-account="$RUNTIME_SA" \
  --add-cloudsql-instances="$CONN_NAME" \
  --vpc-connector="$VPC_CONNECTOR" --vpc-egress=private-ranges-only \
  --set-secrets=DATABASE_URL=lms-database-url:latest,JWT_SECRET_KEY=lms-jwt-secret:latest \
  --set-env-vars=ENVIRONMENT=production,WEB_CONCURRENCY=1,DB_POOL_SIZE=5,DB_MAX_OVERFLOW=5,REDIS_URL=redis://$REDIS_HOST:6379/0,CORS_ORIGINS=https://app.example.com \
  --cpu=1 --memory=512Mi --concurrency=80 \
  --min-instances=1 --max-instances=10 \
  --allow-unauthenticated
```

`--allow-unauthenticated`: the MFEs call this publicly; auth is the app's JWT
layer. Keep `min-instances=1` to avoid cold-start latency on the auth path.

**Connection-budget rule:** `DB_POOL_SIZE × WEB_CONCURRENCY × max-instances`
must stay under Cloud SQL `max_connections`. Here 5 × 1 × 10 = 50. If you raise
`max-instances` or `WEB_CONCURRENCY`, raise the Cloud SQL tier or front it with
PgBouncer.

## 10. Verify

```bash
export URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
curl -s "$URL/health"            # {"status":"ok"}
curl -s "$URL/health/ready"      # {"status":"ready"}  (DB + Redis reachable)

curl -s -X POST "$URL/api/v1/auth/login" \
  -H 'Content-Type: application/json' -H 'X-Tenant-ID: full-lms' \
  -d '{"email":"student@full-lms.com","password":"Learn123!"}'
```

## 11. Day-2

- **Redeploy:** `gcloud builds submit --tag "$IMAGE" && gcloud run deploy "$SERVICE" --image="$IMAGE" ...`. Run `lms-migrate` *before* shifting traffic when a release adds migrations.
- **CI/CD:** add a Cloud Build trigger on `main` that builds, pushes, executes `lms-migrate`, then `gcloud run deploy`.
- **Custom domain:** `gcloud run domain-mappings create --service "$SERVICE" --domain api.example.com`.
- **Startup probe** (optional): point Cloud Run's startup probe at `/health/ready` via a service YAML so traffic waits for DB/Redis.
- **Harden:** restrict `CORS_ORIGINS` to real MFE origins; for stricter DB isolation use Cloud SQL **private IP** (reuse the VPC connector) instead of the public-IP socket; rotate `lms-jwt-secret` (deploy picks up `:latest`).
- **Cost trim:** Memorystore Basic 1GB is the floor for managed Redis. Alternatives: a single small Redis on Compute Engine, or a managed Redis (e.g. Upstash) over TLS — set `REDIS_URL` accordingly and drop the VPC connector if reachable publicly.
```
