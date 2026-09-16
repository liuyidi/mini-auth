# mini-auth

mini-auth is the shared identity and authentication service for the Mini product family.
It started as `deepseek-chat-api` and is being evolved into a reusable identity center for web, desktop, mobile, and CLI clients.

Public site: `https://auth.liuyidi.me`

## What It Does Today

mini-auth already provides the core authentication building blocks:

- Email and password registration
- Email and password sign-in
- JWT access token and refresh token issuance
- Refresh-token rotation and session tracking
- Sign-out and session revocation
- GitHub OAuth sign-in
- Google OAuth sign-in
- OIDC / OAuth2 authorization support
- OIDC discovery and JWKS endpoints
- User profile lookup through `/api/v1/me`
- Admin APIs for registering and listing OIDC clients
- Local OIDC demo flow for end-to-end verification
- Device authorization flow for browser-assisted CLI login

## Where It Is Going

The project is being shaped into a true identity provider rather than a single-purpose backend.

Planned direction:

- Standardize all clients on OIDC Authorization Code + PKCE
- Keep JWT as the internal access token format
- Add more external identity providers through a shared account-linking layer
- Support email verification codes as a lighter login path
- Introduce passkey and MFA support
- Add SMS login and WeChat login once the required operational and compliance pieces are ready
- Expand into a unified login surface for Mini products across platforms

## Documentation

- [Platform design v1](docs/auth-platform-design.md)
- [Tencent Cloud deployment](docs/tencent-auth-deploy.md)
- [中文 README](README.zh.md)

## Architecture Summary

The current implementation is centered on four pieces:

1. Authentication APIs for registration, login, refresh, and logout
2. External identity adapters for GitHub and Google
3. OIDC services for discovery, client registration, authorization, and token exchange
4. Session and token persistence backed by PostgreSQL

Short-lived state such as verification and authorization flows is intended to stay isolated from long-term account data.

## Tech Stack

- FastAPI
- SQLAlchemy 2.0 async
- PostgreSQL
- JWT access and refresh tokens
- Alembic migrations
- Docker-based production deployment

## Local Development

### 1. Start PostgreSQL

```bash
docker run --name mini-auth-pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=mini_auth \
  -p 5432:5432 -d postgres:16
```

### 2. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mini_auth
```

### 3. Run Migrations and Start the App

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Open the docs at:

```text
http://127.0.0.1:8000/docs
```

## Demo Flows

On startup, the app seeds a local demo OIDC client:

- `client_id`: `minibot`
- `redirect_uri`: `http://127.0.0.1:8000/oidc/demo/callback`

Use it to verify the basic OIDC round trip:

1. Open `http://127.0.0.1:8000/oidc/demo`
2. Sign in or create an account first if needed
3. Click `Start OIDC Demo`
4. Complete the flow and inspect `authorize -> token -> userinfo`

For CLI-oriented device login, use the device authorization page exposed by the web app.

## API Surface

### Authentication

| Method | Path | Description |
|------|------|------|
| POST | `/api/v1/auth/register` | Register `{ email, password, nickname? }` |
| POST | `/api/v1/auth/login` | Sign in |
| POST | `/api/v1/auth/refresh` | Refresh `{ refresh_token }` |
| POST | `/api/v1/auth/logout` | Sign out `{ refresh_token }` |
| POST | `/api/v1/auth/email/start` | Send an email verification code |
| POST | `/api/v1/auth/email/verify` | Verify the email code and sign in / register |
| POST | `/api/v1/auth/demo-login` | Local demo login |

### External Identity

| Method | Path | Description |
|------|------|------|
| GET | `/api/v1/auth/github/start` | Start GitHub login |
| GET | `/api/v1/auth/github/callback` | GitHub OAuth callback |
| GET | `/api/v1/auth/google/start` | Start Google login |
| GET | `/api/v1/auth/google/callback` | Google OAuth callback |

### OIDC / OAuth

| Method | Path | Description |
|------|------|------|
| GET | `/oauth/.well-known/openid-configuration` | OIDC discovery |
| GET | `/oauth/jwks.json` | JWKS endpoint |
| GET | `/oauth/authorize` | OIDC authorization entry |
| POST | `/oauth/token` | OIDC token exchange |
| POST | `/oauth/device/start` | Start device login |
| GET | `/oauth/device/request` | Fetch device login status |
| POST | `/oauth/device/confirm` | Confirm device login |
| GET | `/oauth/userinfo` | OIDC userinfo |
| GET | `/oauth/device` | Device login page |

### OIDC / User

| Method | Path | Description |
|------|------|------|
| GET | `/api/v1/me` | Current user info |
| GET | `/oidc/demo` | Local OIDC demo entry |

### Admin and Health

| Method | Path | Description |
|------|------|------|
| POST | `/api/v1/admin/clients` | Register an OIDC client |
| GET | `/api/v1/admin/clients` | List OIDC clients |
| GET | `/api/v1/admin/stats` | Daily digest preview (users + Umami; no Feishu) |
| POST | `/api/v1/admin/daily-digest` | Build digest and send Feishu (`?send=false` to preview) |
| GET | `/health` | Health check |

## Production Deployment

See [`docs/tencent-auth-deploy.md`](docs/tencent-auth-deploy.md) and [`deploy/`](deploy/).

CI: [`Publish Auth (Tencent CVM)`](.github/workflows/publish-auth-tencent.yml)
auto-deploys on matching `main` paths and can also be run manually from GitHub Actions.

## Environment Variables

See [`.env.example`](.env.example) and [`deploy/.env.example`](deploy/.env.example).
