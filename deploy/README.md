# mini-auth deploy assets (Tencent CVM)

Aligned with [`docs/auth-platform-design.md`](../docs/auth-platform-design.md) §9 / §14 and
[`docs/tencent-auth-deploy.md`](../docs/tencent-auth-deploy.md).

## Layout on server (`/opt/auth`)

```text
/opt/auth/
  docker-compose.yml   ← copy from deploy/docker-compose.yml
  Caddyfile            ← copy from deploy/Caddyfile
  frontend-dist/       ← build output from frontend/apps/web/dist
  .env                 ← from deploy/.env.example (secrets)
  mini-auth/           ← git clone of this repo (build context)
```

## Services

| Service | Image (DaoCloud) | Role |
|---------|------------------|------|
| `caddy` | `library/caddy:2` | Static frontend + reverse proxy → `api:8000` |
| `api` | build `Dockerfile.ecs` | FastAPI mini-auth |
| `db` | `library/postgres:16` | Persistent identity / sessions |
| `redis` | `library/redis:7-alpine` | OTP, OAuth state, PKCE, rate limit |

Postgres / Redis are on the compose `internal` network only (no host ports).

`/login` and `/login/email` are served by the frontend SPA from `frontend-dist`.
OIDC, discovery and API routes still proxy to FastAPI.

## Quick start

```bash
cd /opt/auth
cp mini-auth/deploy/docker-compose.yml .
cp mini-auth/deploy/Caddyfile .
cp mini-auth/deploy/.env.example .env
# edit .env — strong POSTGRES_PASSWORD, REDIS_PASSWORD, JWT_SECRET, CADDY_ACME_EMAIL

cd /path/to/local/mini-auth
npm run build -w @mini-auth/web
ssh -i deploy/tencent_cloud.pem ubuntu@<TENCENT_PUBLIC_IP> 'mkdir -p /opt/auth/frontend-dist'
rsync -a --delete frontend/apps/web/dist/ ubuntu@<TENCENT_PUBLIC_IP>:/opt/auth/frontend-dist/

docker compose pull db redis caddy
docker compose build api
docker compose up -d
docker compose ps
curl -fsS https://auth.liuyidi.me/health
```

邮件验证码生产配置建议：

```bash
EMAIL_PROVIDER=aliyun_directmail
EMAIL_FROM=Minibot <noreply@mail.liuyidi.me>
EMAIL_SENDER_DOMAIN=mail.liuyidi.me
EMAIL_SENDER_ACCOUNT=noreply
EMAIL_FROM_ALIAS=Minibot
EMAIL_TEMPLATE_LOGIN_CODE=auth_login_code
EMAIL_SERVICE_API_KEY=<Aliyun AccessKey ID>
EMAIL_SERVICE_SECRET=<Aliyun AccessKey Secret>
EMAIL_SERVICE_REGION=cn-hangzhou
EMAIL_DEBUG_RETURN_CODE=false
```

GitHub 登录需要先在 GitHub OAuth App 中登记回调
`https://auth.liuyidi.me/api/v1/auth/github/callback`，然后配置：

```bash
GITHUB_ENABLED=true
GITHUB_CLIENT_ID=<OAuth App client ID>
GITHUB_CLIENT_SECRET=<OAuth App client secret>
GITHUB_REDIRECT_URI=https://auth.liuyidi.me/api/v1/auth/github/callback
```

Google 登录需要先在 Google Cloud Console OAuth 客户端中登记回调
`https://auth.liuyidi.me/api/v1/auth/google/callback`，然后配置：

```bash
GOOGLE_ENABLED=true
GOOGLE_CLIENT_ID=<OAuth client ID>
GOOGLE_CLIENT_SECRET=<OAuth client secret>
GOOGLE_REDIRECT_URI=https://auth.liuyidi.me/api/v1/auth/google/callback
EXTERNAL_AUTH_ALLOWED_RETURN_ORIGINS=https://auth.liuyidi.me,https://bot.liuyidi.me
EXTERNAL_AUTH_COOKIE_SECURE=true
```

构建登录页时设置 `VITE_GITHUB_LOGIN_ENABLED=true` 和/或 `VITE_GOOGLE_LOGIN_ENABLED=true`。后端未配置完整凭据前必须保持
前后端开关为 `false`。GitHub / Google access token 仅用于当次读取用户资料，不会持久化。

Google OAuth 同意屏幕可填写：

| 字段 | URL |
|------|-----|
| 隐私政策 | `https://auth.liuyidi.me/privacy` |
| 服务条款 | `https://auth.liuyidi.me/terms` |
| 应用首页 | `https://auth.liuyidi.me/` |

**大陆服务器无法直连 Google 时**：部署 `deploy/google-oauth-relay/` 到 Vercel（见该目录 README），
然后在 `/opt/auth/.env` 配置：

```bash
GOOGLE_RELAY_URL=https://<relay-host>/api/google/exchange
GOOGLE_RELAY_SHARED_SECRET=<与 Vercel 相同>
```

设置 `GOOGLE_RELAY_URL` 后 API 走 relay 交换 token，不再直连 `oauth2.googleapis.com`。
重启：`docker compose --env-file .env up -d api`。

## GitHub Actions 发布

工作流：[`.github/workflows/publish-auth-tencent.yml`](../.github/workflows/publish-auth-tencent.yml)

CI 在 runner 上构建 SPA，然后通过 **SCP** 将 `app/`、`alembic/`、`deploy/` 等源码同步到 CVM 的 `/opt/auth/mini-auth`（不再依赖 CVM 上的 `git fetch` 私有仓库）。服务器上的 `/opt/auth/.env` 不会被覆盖。

| 触发 | `workflow_dispatch`，或 `main` 上改动 `app/` / `frontend/` / `deploy/` 等 |
| 作用 | 拉代码 → CI 构建 SPA → 上传 `frontend-dist` → `docker compose build api && up -d` → 健康检查 → ServerlessShip / 飞书 |

仓库需配置：

| 类型 | 名 | 说明 |
|------|-----|------|
| Variable | `AUTH_HOST` | 腾讯云 CVM 公网 IP / 主机名 |
| Variable | `AUTH_SSH_USER` | 默认 `ubuntu` |
| Variable | `AUTH_SSH_PORT` | 可选，默认 `22` |
| Variable | `VITE_AUTH_BASE_URL` | 可选，默认 `https://auth.liuyidi.me` |
| Variable | `VITE_GITHUB_LOGIN_ENABLED` | 可选，默认 `true` |
| Variable | `VITE_GOOGLE_LOGIN_ENABLED` | 可选，默认 `true` |
| Variable | `SERVERLESSSHIP_RELEASE_URL` | 可选 |
| Secret | `AUTH_SSH_PRIVATE_KEY` | 对应本机 `deploy/host.env` 的 PEM 内容 |
| Secret | `AUTH_ADMIN_API_KEY` | 与 CVM `.env` 中 `AUTH_ADMIN_API_KEY` 相同（日报 workflow 用） |
| Variable | `AUTH_BASE_URL` | 可选，默认 `https://auth.liuyidi.me`（日报 workflow） |

## 每日飞书汇总

工作流：[`.github/workflows/daily-digest-feishu.yml`](../.github/workflows/daily-digest-feishu.yml)（每天 10:00 上海时区，或手动 `workflow_dispatch`）。

在 `/opt/auth/.env` 增加（Webhook 或飞书应用二选一，应用凭证可与 serverless-ship 相同）：

```bash
# Option A
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/...

# Option B (app IM)
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_TARGET_OPEN_ID=ou_xxx
FEISHU_TARGET_ID_TYPE=open_id

UMAMI_SHARE_BASE_URL=https://cloud.umami.is/analytics/us
UMAMI_SHARE_SLUG=fAjwSKOBPqy37HAd
DIGEST_TIMEZONE=Asia/Shanghai
AUTH_ADMIN_API_KEY=change-me-admin-api-key
```

然后 `docker compose --env-file .env up -d api`。预览：`GET /api/v1/admin/stats`（Header `X-Admin-Api-Key`）。

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Full stack |
| `Dockerfile.ecs` | CN-friendly API image |
| `Caddyfile` | Static frontend + API proxy |
| `nginx.auth.liuyidi.me.conf.example` | Aliyun nginx reverse proxy template |
| `setup-docker-mirror.sh` | DaoCloud registry mirrors |
| `.env.example` | Env template |
| `host.env.example` | Local SSH hints (copy to gitignored `host.env`) |
