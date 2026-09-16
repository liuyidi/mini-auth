# mini-auth

mini-auth 是 Mini 产品族共用的统一身份认证服务。
它正在演进成一个可复用的统一身份中心，服务于 Web、桌面、移动端和 CLI 客户端。

公网地址：`https://auth.liuyidi.me`

## 当前已具备的能力

mini-auth 目前已经提供了核心认证能力：

- 邮箱和密码注册
- 邮箱和密码登录
- JWT access token 与 refresh token 签发
- refresh token 轮换和会话追踪
- 登出与会话撤销
- GitHub OAuth 登录
- Google OAuth 登录
- OIDC / OAuth2 授权能力
- OIDC discovery 和 JWKS 接口
- 通过 `/api/v1/me` 获取当前用户信息
- OIDC 客户端注册和查询管理接口
- 本地 OIDC demo 流程，便于端到端验证
- 适合浏览器辅助 CLI 登录的 device authorization 流程

## 未来会怎么演进

这个项目的目标不只是一个业务后端，而是一个真正的身份提供方。

接下来的演进方向：

- 将所有客户端统一到 OIDC Authorization Code + PKCE
- 继续使用 JWT 作为内部访问令牌格式
- 通过统一的账号绑定层接入更多外部身份源
- 增加邮箱验证码登录，作为更轻量的登录方式
- 引入 passkey 和 MFA
- 在条件成熟后补充短信登录和微信登录
- 逐步成为 Mini 各产品跨平台共用的统一登录入口

## 文档

- [平台一期设计](docs/auth-platform-design.md)
- [腾讯云部署](docs/tencent-auth-deploy.md)
- [English README](README.md)

## 架构概览

当前实现主要由四部分组成：

1. 认证 API，负责注册、登录、刷新和登出
2. 外部身份适配器，负责 GitHub 和 Google 登录
3. OIDC 服务，负责 discovery、客户端注册、授权和 token 交换
4. 基于 PostgreSQL 的会话和 token 持久化

短期状态，例如验证码、授权流程上下文等，应该尽量与长期账号数据分离。

## 技术栈

- FastAPI
- SQLAlchemy 2.0 异步
- PostgreSQL
- JWT access / refresh token
- Alembic 数据库迁移
- Docker 生产部署

## 本地开发

### 1. 启动 PostgreSQL

```bash
docker run --name mini-auth-pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=mini_auth \
  -p 5432:5432 -d postgres:16
```

### 2. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mini_auth
```

### 3. 执行迁移并启动服务

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

文档地址：

```text
http://127.0.0.1:8000/docs
```

## Demo 流程

启动后会自动补一个本地 demo OIDC client：

- `client_id`：`minibot`
- `redirect_uri`：`http://127.0.0.1:8000/oidc/demo/callback`

可以通过这条链路验证标准 OIDC 流程：

1. 打开 `http://127.0.0.1:8000/oidc/demo`
2. 如有需要先登录或注册
3. 点击 `Start OIDC Demo`
4. 完成后查看 `authorize -> token -> userinfo`

面向 CLI 的 device login，可以通过 Web 端的 device authorization 页面完成。

## API 能力

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 注册 `{ email, password, nickname? }` |
| POST | `/api/v1/auth/login` | 登录 |
| POST | `/api/v1/auth/refresh` | 刷新 `{ refresh_token }` |
| POST | `/api/v1/auth/logout` | 登出 `{ refresh_token }` |
| POST | `/api/v1/auth/email/start` | 发送邮箱验证码 |
| POST | `/api/v1/auth/email/verify` | 验证邮箱验证码并登录 / 注册 |
| POST | `/api/v1/auth/demo-login` | 本地 demo 登录 |

### 外部身份

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/auth/github/start` | 发起 GitHub 登录 |
| GET | `/api/v1/auth/github/callback` | GitHub OAuth 回调 |
| GET | `/api/v1/auth/google/start` | 发起 Google 登录 |
| GET | `/api/v1/auth/google/callback` | Google OAuth 回调 |

### OIDC / OAuth

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/oauth/.well-known/openid-configuration` | OIDC discovery |
| GET | `/oauth/jwks.json` | JWKS 接口 |
| GET | `/oauth/authorize` | OIDC 授权入口 |
| POST | `/oauth/token` | OIDC token 交换 |
| POST | `/oauth/device/start` | 设备登录初始化 |
| GET | `/oauth/device/request` | 查询设备登录状态 |
| POST | `/oauth/device/confirm` | 设备登录确认 |
| GET | `/oauth/userinfo` | OIDC userinfo |
| GET | `/oauth/device` | 设备登录页面 |

### OIDC / 用户

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/me` | 当前用户信息 |
| GET | `/oidc/demo` | 本地 OIDC demo 入口 |

### 管理与健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/admin/clients` | 注册 OIDC 客户端 |
| GET | `/api/v1/admin/clients` | 查看 OIDC 客户端 |
| GET | `/api/v1/admin/stats` | 日报预览（用户量 + Umami 访问量，不发飞书） |
| POST | `/api/v1/admin/daily-digest` | 汇总并发送飞书日报（`?send=false` 仅预览） |
| GET | `/health` | 健康检查 |

## 生产部署

见 [`docs/tencent-auth-deploy.md`](docs/tencent-auth-deploy.md) 和 [`deploy/`](deploy/)。

CI：[`Publish Auth (Tencent CVM)`](.github/workflows/publish-auth-tencent.yml)
会在匹配 `main` 相关路径时自动部署，也可以在 GitHub Actions 中手动执行。

## 环境变量

见 [`.env.example`](.env.example) 和 [`deploy/.env.example`](deploy/.env.example)。
