# Tunnel Setup

## Quick Tunnel (dev, disposable URL)

Good for ad-hoc demos. URL randomizes every `cloudflared` restart.

```bash
cloudflared tunnel --url http://localhost:8000
# copy the https://xxx.trycloudflare.com URL
./scripts/update_tunnel.sh https://xxx.trycloudflare.com
```

## Stable Named Tunnel (recommended)

One-time setup, fixed URL that never changes. Requires a free Cloudflare account.

```bash
# 1. Authenticate (opens browser)
cloudflared tunnel login

# 2. Create named tunnel
cloudflared tunnel create lms-backend
# writes credentials to ~/.cloudflared/<UUID>.json

# 3. Route DNS (requires a domain on Cloudflare, e.g. lms-dev.yourdomain.com)
cloudflared tunnel route dns lms-backend lms-dev.yourdomain.com

# 4. Create config file
cat > ~/.cloudflared/lms-backend.yml <<'EOF'
tunnel: lms-backend
credentials-file: /home/faheem/.cloudflared/<UUID>.json

ingress:
  - hostname: lms-dev.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# 5. Run (or install as systemd service)
cloudflared tunnel run lms-backend

# Or as a systemd user service:
cloudflared service install
systemctl --user enable --now cloudflared
```

Then in `.env`:
```
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://lms-dev.yourdomain.com
CORS_ORIGIN_REGEX=https://([a-z0-9-]+\.)?(lms-mf-es-shell\.vercel\.app|yourdomain\.com)$
```

## Tunnel-less alternatives

| Option | Pros | Cons |
|---|---|---|
| **ngrok** | Stable subdomain (free tier), inspector UI | Requires signup, rate-limits |
| **localtunnel** | No signup | Unreliable, slow |
| **serveo.net** | SSH-based, no install | Often down |
| **Tailscale Funnel** | Works if FE also on tailnet | Needs Tailscale on both sides |
