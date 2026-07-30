# mini-auth deploy assets (Tencent CVM)

Aligned with [`docs/auth-platform-design.md`](../docs/auth-platform-design.md) §9 / §14 and
[`docs/tencent-auth-deploy.md`](../docs/tencent-auth-deploy.md).

## Layout on server (`/opt/auth`)

```text
/opt/auth/
  docker-compose.yml   ← copy from deploy/docker-compose.yml
  Caddyfile            ← copy from deploy/Caddyfile
  .env                 ← from deploy/.env.example (secrets)
  mini-auth/           ← git clone of this repo (build context)
```

## Services

| Service | Image (DaoCloud) | Role |
|---------|------------------|------|
| `caddy` | `library/caddy:2` | HTTPS reverse proxy → `api:8000` |
| `api` | build `Dockerfile.ecs` | FastAPI mini-auth |
| `db` | `library/postgres:16` | Persistent identity / sessions |
| `redis` | `library/redis:7-alpine` | OTP, OAuth state, PKCE, rate limit |

Postgres / Redis are on the compose `internal` network only (no host ports).

## Quick start

```bash
cd /opt/auth
cp mini-auth/deploy/docker-compose.yml .
cp mini-auth/deploy/Caddyfile .
cp mini-auth/deploy/.env.example .env
# edit .env — strong POSTGRES_PASSWORD, REDIS_PASSWORD, JWT_SECRET, CADDY_ACME_EMAIL

docker compose pull db redis caddy
docker compose build api
docker compose up -d
docker compose ps
curl -fsS https://auth.liuyidi.me/health
```

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Full stack |
| `Dockerfile.ecs` | CN-friendly API image |
| `Caddyfile` | TLS + proxy |
| `setup-docker-mirror.sh` | DaoCloud registry mirrors |
| `.env.example` | Env template |
| `host.env.example` | Local SSH hints (copy to gitignored `host.env`) |
