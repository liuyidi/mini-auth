# DeepSeek Chat API

FastAPI 后端：用户注册 / 登录 / JWT 刷新 / 登出。

## 技术栈

- FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL
- JWT（access + refresh）
- Alembic 迁移
- Railway 部署

## 本地开发

### 1. 启动 PostgreSQL

```bash
docker run --name deepseek-pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=deepseek_chat \
  -p 5432:5432 -d postgres:16
```

### 2. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. 迁移 & 启动

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

文档：http://127.0.0.1:8000/docs

## API（P0 第一步）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 注册 `{ email, password, nickname? }` |
| POST | `/api/v1/auth/login` | 登录 |
| POST | `/api/v1/auth/refresh` | 刷新 `{ refresh_token }` |
| POST | `/api/v1/auth/logout` | 登出 `{ refresh_token }` |
| GET | `/health` | 健康检查 |

## Railway 部署

1. 连接 GitHub 仓库 `deepseek-chat-api`
2. 添加 **PostgreSQL** 插件（自动注入 `DATABASE_URL`）
3. 设置环境变量：
   - `JWT_SECRET`（长随机字符串）
   - `JWT_ACCESS_EXPIRE_MINUTES=30`
   - `JWT_REFRESH_EXPIRE_DAYS=30`
   - `CORS_ORIGINS=*`
4. 部署后访问 `/docs` 验证

## 环境变量

见 `.env.example`。
