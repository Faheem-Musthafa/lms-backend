# Deploy to GCP — Cloud Run + Cloud SQL (POC, Web Console)

Step-by-step through the GCP web console. No CLI needed except one build step
in Cloud Shell (the terminal icon in the console top bar).

Cloud Run connects to Cloud SQL via **public IP + SSL**. No VPC needed.
Redis is optional (disabled by default now).

---

## Prerequisites

- GCP project with billing enabled
- Cloud SQL instance created (PostgreSQL 15+)
- This codebase pushed to a Git repo (GitHub, GitLab, or Cloud Source Repositories)

---

## Step 1 — Enable APIs

1. Go to **[APIs & Services > Library](https://console.cloud.google.com/apis/library)**
2. Search for and **Enable** each:
   - `Cloud Run API`
   - `Cloud SQL Admin API`
   - `Artifact Registry API`
   - `Cloud Build API`

---

## Step 2 — Create Cloud SQL database and user

### 2a. Create the database

1. Go to **[SQL > Databases](https://console.cloud.google.com/sql/instances)**
2. Click your instance name
3. In the left sidebar, click **Databases**
4. Click **CREATE DATABASE**
   - Name: `lms`
   - Click **CREATE**

### 2b. Create the app user

1. In the left sidebar, click **Users**
2. Click **ADD USER ACCOUNT**
   - Username: `lms`
   - Password: generate a strong password (save it!)
   - Click **ADD**

### 2c. Note your connection details

On the instance **Overview** page, write down:
- **Public IP address** (e.g. `34.123.45.67`)
- **Connection name** (e.g. `my-project:us-central1:lms-pg`)

You'll need these in later steps.

### 2d. Allow all IPs (POC only)

1. On your instance page, click **Connections** in the left sidebar
2. Under **Authorized networks**, click **ADD NETWORK**
   - Name: `allow-all`
   - Network: `0.0.0.0/0`
   - Click **DONE**
3. Click **SAVE** at the top

> This is fine for POC. For production, restrict to specific IP ranges.

---

## Step 3 — Create Artifact Registry repository

1. Go to **[Artifact Registry > Repositories](https://console.cloud.google.com/artifacts)**
2. Click **CREATE REPOSITORY**
   - Name: `lms`
   - Format: **Docker**
   - Region: match your Cloud SQL region (e.g. `us-central1`)
   - Click **CREATE**

---

## Step 4 — Build and push container image

This is the one step that needs a terminal. Open **Cloud Shell** (the `>_` icon
in the top-right of the GCP console).

### 4a. Open Cloud Shell and clone your code

```bash
# Clone your repo (adjust URL)
git clone https://github.com/YOUR_USER/lms-backend.git
cd lms-backend
```

> If your code is already in Cloud Source Repositories, clone from there instead.

### 4b. Set variables

```bash
export PROJECT_ID="your-project-id"          # find in console top bar
export REGION="us-central1"                  # match your Cloud SQL region
```

### 4c. Build and push

```bash
gcloud builds submit \
  --tag "$REGION-docker.pkg.dev/$PROJECT_ID/lms/lms-backend:v1" \
  --project="$PROJECT_ID"
```

Wait for it to finish. You should see `BUILD SUCCESS`.

### 4d. Verify the image

1. Go to **[Artifact Registry > Repositories > lms](https://console.cloud.google.com/artifacts)**
2. Click on `lms-backend`
3. You should see `v1` listed

---

## Step 5 — Deploy Cloud Run service

### 5a. Create the service

1. Go to **[Cloud Run > Services](https://console.cloud.google.com/run)**
2. Click **CREATE SERVICE**
3. Fill in:
   - **Service name**: `lms-api`
   - **Region**: same as Cloud SQL (e.g. `us-central1`)
   - **Authentication**: select **Allow unauthenticated invocations** (for POC)
   - Under **Container image**, click **SELECT** → navigate to your Artifact Registry
     repo → select `lms-backend:v1`

### 5b. Set the container port

- Under **Container port**, set to `8000`

### 5c. Add Cloud SQL connection

1. Scroll down to the **Connections** tab
2. Under **Cloud SQL connections**, click **ADD CONNECTION**
3. Select your Cloud SQL instance from the dropdown
4. Click **DONE**

### 5d. Add environment variables

Click the **Variables & Secrets** tab, then add these:

| Variable name | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://lms:YOUR_PASSWORD@YOUR_SQL_IP:5432/lms` |
| `DATABASE_SYNC_URL` | `postgresql+psycopg://lms:YOUR_PASSWORD@YOUR_SQL_IP:5432/lms` |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `LOG_LEVEL` | `INFO` |
| `JWT_SECRET_KEY` | *(generate: `openssl rand -hex 32` in Cloud Shell)* |
| `CORS_ORIGINS` | `*` *(for POC — replace with your frontend URL later)* |
| `ENABLE_ROW_LEVEL_SECURITY` | `true` |

> Replace `YOUR_PASSWORD` with the `lms` user password from Step 2b.
> Replace `YOUR_SQL_IP` with the public IP from Step 2c.
> No `REDIS_URL` — the app works fine without it.

### 5e. Adjust resources (optional)

Under **Capacity**:
- **Memory**: `512 MiB` (enough for POC)
- **CPU**: `1`
- **Request timeout**: `300` seconds
- **Max instances**: `3` (keeps costs low)

### 5f. Deploy

Click **CREATE** (or **DEPLOY**). Wait for the green checkmark.

---

## Step 6 — Run database migrations

### 6a. Create a Cloud Run Job

1. Go to **[Cloud Run > Jobs](https://console.cloud.google.com/run/jobs)**
2. Click **CREATE JOB**
3. Fill in:
   - **Job name**: `lms-migrate`
   - **Region**: same region
   - **Container image**: same `lms-backend:v1` from Artifact Registry

### 6b. Configure the job container

Under **Container**:
- **Command**: `alembic`
- **Args**: `upgrade`, `head`

### 6c. Add Cloud SQL connection

Same as Step 5c — add your Cloud SQL instance.

### 6d. Add environment variables

Same as Step 5d, but only these two:

| Variable name | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://lms:YOUR_PASSWORD@YOUR_SQL_IP:5432/lms` |
| `DATABASE_SYNC_URL` | `postgresql+psycopg://lms:YOUR_PASSWORD@YOUR_SQL_IP:5432/lms` |

### 6e. Set job properties

- **Task timeout**: `300` seconds
- **Max retries**: `0` (fail fast — check logs if it fails)

Click **CREATE**.

### 6f. Execute the migration

1. Click the three dots menu (⋮) on the right side of your job
2. Click **Execute now**
3. Wait for the execution to show **Succeeded**
4. Click into the execution → **Logs** tab to see migration output

---

## Step 7 — Seed demo data

### 7a. Create another Cloud Run Job

1. Go to **[Cloud Run > Jobs](https://console.cloud.google.com/run/jobs)**
2. Click **CREATE JOB**
3. Fill in:
   - **Job name**: `lms-seed`
   - **Region**: same region
   - **Container image**: same `lms-backend:v1`

### 7b. Configure the job container

Under **Container**:
- **Command**: `python`
- **Args**: `-m`, `scripts.seed`

### 7c. Add Cloud SQL connection + env vars

Same Cloud SQL connection. Environment variables:

| Variable name | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://lms:YOUR_PASSWORD@YOUR_SQL_IP:5432/lms` |
| `DATABASE_SYNC_URL` | `postgresql+psycopg://lms:YOUR_PASSWORD@YOUR_SQL_IP:5432/lms` |
| `JWT_SECRET_KEY` | *(same value as your service)* |

### 7d. Create and execute

Click **CREATE**, then **Execute now**. Wait for **Succeeded**.

Check logs to see: `Seeded X tenants, Y users, Z courses...`

---

## Step 8 — Verify deployment

1. Go to **[Cloud Run > Services](https://console.cloud.google.com/run)**
2. Click your `lms-api` service
3. Copy the **Service URL** (top of the page, e.g. `https://lms-api-xxxxx.a.run.app`)

### Test in your browser

Open these URLs:
- `https://YOUR-URL/health` → should show `{"status":"ok"}`
- `https://YOUR-URL/health/ready` → should show `{"status":"ready"}`
- `https://YOUR-URL/docs` → Swagger UI with all endpoints

### Test login (from Cloud Shell or terminal)

```bash
curl -X POST "https://YOUR-URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: full-lms" \
  -d '{"email":"admin@full-lms.com","password":"Learn123!"}'
```

Should return `access_token` and `refresh_token`.

---

## Step 9 — Set up Cloud Build trigger (optional, auto-deploy on push)

This makes every `git push` to `main` automatically build and deploy.

1. Go to **[Cloud Build > Triggers](https://console.cloud.google.com/cloud-build/triggers)**
2. Click **CREATE TRIGGER**
   - **Name**: `lms-deploy`
   - **Event**: Push to a branch
   - **Source**: Connect your GitHub/GitLab repo
   - **Branch**: `main`
   - **Build configuration**: Cloud Build configuration file
   - **Cloud Build configuration file location**: `cloudbuild.yaml`
3. Click **CREATE**

### Create `cloudbuild.yaml` in your repo root

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/lms/lms-backend:${SHORT_SHA}', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '${_REGION}-docker.pkg.dev/${PROJECT_ID}/lms/lms-backend:${SHORT_SHA}']
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'lms-api'
      - '--image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/lms/lms-backend:${SHORT_SHA}'
      - '--region=${_REGION}'
      - '--project=${PROJECT_ID}'
substitutions:
  _REGION: us-central1
```

Now every push to `main` builds and deploys automatically.

---

## Redeploying manually (new version)

1. Open **Cloud Shell**, `cd` into your code
2. Build new tag:
   ```bash
   gcloud builds submit --tag "REGION-docker.pkg.dev/PROJECT_ID/lms/lms-backend:v2"
   ```
3. Go to **Cloud Run > Services > lms-api**
4. Click **EDIT & DEPLOY NEW REVISION**
5. Select the new image tag `v2`
6. Click **DEPLOY**

> If schema changed, execute `lms-migrate` job first (Step 6f).

---

## Troubleshooting

| Problem | Where to check | Fix |
|---|---|---|
| Service shows red error | Cloud Run > Services > click service > **Logs** tab | Check error message |
| `connection refused` | Cloud SQL > instance > **Connections** | Add `0.0.0.0/0` to authorized networks |
| `/health/ready` returns 503 | Cloud Run > service > **Logs** | DB connection failing — check `DATABASE_URL` |
| `module_not_enabled` on all routes | Cloud Run > Jobs | Re-run `lms-migrate` and `lms-seed` jobs |
| CORS errors from frontend | Cloud Run > service > **Variables** | Update `CORS_ORIGINS` to your frontend URL, redeploy |
| Migration fails | Cloud Run > Jobs > `lms-migrate` > **Logs** | Check SQL errors in the log output |
| Image not found | Artifact Registry > repos | Re-run the `gcloud builds submit` step |

---

## What's disabled without Redis

- **Rate limiting** — all requests pass through unchecked
- **Module licensing cache** — DB queried every request (fine for POC)
- **Tenant slug cache** — DB queried every request (fine for POC)
- **Password reset tokens** — stored in-memory (lost on restart, single-instance only)

For production, add Memorystore or a managed Redis and set `REDIS_URL` env var.
