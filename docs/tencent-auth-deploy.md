# 腾讯云部署 auth.liuyidi.me（mini-auth）

独立认证服务跑在 **腾讯云 CVM**；业务（bot / mlf / kb）仍在阿里云。域名 DNS 指向腾讯云公网 IP 即可跨云互通。

## 机器信息（当前）

| 项 | 值 |
|----|-----|
| 公网 IP | `150.158.146.191` |
| SSH | `ssh -i ~/Downloads/tencent_cloud.pem ubuntu@150.158.146.191` |
| 系统 | Ubuntu 22.04，约 2C2G，40G 盘 |
| 内存 / Swap | ~1.9G + **2G swap（已启用）** |
| 域名 | `auth.liuyidi.me` → A 记录已指向上述 IP（万网 DNS） |
| 代码目录（服务器） | `/opt/auth/mini-auth` |
| Compose 根目录 | `/opt/auth` |

安全组入站需放行：**22 / 80 / 443**（勿对公网开放 5432）。

## 架构

```text
DNS auth.liuyidi.me ──A──► 150.158.146.191
                              │
                   Caddy :443 (Let's Encrypt)
                              │
                   api :8000  (FastAPI / mini-auth)
                              │
                   Postgres 16 (仅 Docker 内网)
```

客户端登录 → `https://auth.liuyidi.me`；拿到 access JWT 后再请求阿里云 `https://bot.liuyidi.me` bootstrap。

## 境内加速约定（对齐阿里云 Demo）

与 [aliyun-ecs-demo-deploy](../../mini-langfuse/.claude/skills/aliyun-ecs-demo-deploy/SKILL.md) / `mini-langfuse/deploy/demo` 相同策略：

| 用途 | 镜像 / 源 |
|------|-----------|
| Docker Hub 拉取 | `https://docker.m.daocloud.io`（`/etc/docker/daemon.json` registry-mirrors） |
| 基础镜像 | `docker.m.daocloud.io/library/python:3.12-slim`、`…/postgres:16`、`…/caddy:2` |
| Debian apt | `mirrors.aliyun.com` |
| PyPI | `https://mirrors.aliyun.com/pypi/simple/` |
| GitHub clone/pull | `https://ghfast.top/https://github.com/liuyidi/mini-auth.git`（直连慢时） |

仓库内脚本：

- [`deploy/setup-docker-mirror.sh`](../deploy/setup-docker-mirror.sh)
- [`deploy/Dockerfile.ecs`](../deploy/Dockerfile.ecs)（CN 友好构建）
- [`deploy/docker-compose.yml`](../deploy/docker-compose.yml)
- [`deploy/Caddyfile`](../deploy/Caddyfile)

## 0. DNS（若未配）

万网 / DNS 控制台：

| 类型 | 主机记录 | 值 |
|------|----------|-----|
| A | `auth` | `150.158.146.191` |

```bash
dig +short auth.liuyidi.me
# 期望: 150.158.146.191
```

## 1. 安装 Docker + 镜像加速（第一步）

在腾讯云上执行：

```bash
ssh -i ~/Downloads/tencent_cloud.pem ubuntu@150.158.146.191

# 官方安装脚本（腾讯云一般可用）；若慢可改用阿里云 docker-ce 源
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
# 重新 SSH 登录一次使 docker 组生效

# 配置 DaoCloud 镜像加速（与阿里云 Demo 一致）
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
sudo systemctl enable docker

docker pull hello-world
docker run --rm hello-world
```

或把仓库里的 `deploy/setup-docker-mirror.sh` 拷上去执行。

## 2. 放置代码与 Compose

```bash
sudo mkdir -p /opt/auth
sudo chown ubuntu:ubuntu /opt/auth
cd /opt/auth

# 优先 ghfast（境内）
git clone https://ghfast.top/https://github.com/liuyidi/mini-auth.git mini-auth \
  || git clone https://github.com/liuyidi/mini-auth.git mini-auth

# 若 GitHub 仓库尚未改名，临时仍用：
# git clone …/deepseek-chat-api.git mini-auth

cd /opt/auth
cp mini-auth/deploy/docker-compose.yml .
cp mini-auth/deploy/Caddyfile .
cp mini-auth/deploy/.env.example .env
# 编辑 .env：强随机 JWT_SECRET、Postgres 密码、CORS
nano .env

# 构建上下文指向源码（compose 内 build.context=./mini-auth）
docker compose build
docker compose up -d
```

`.env` 最小项：

```bash
POSTGRES_USER=auth
POSTGRES_PASSWORD=<强密码>
POSTGRES_DB=mini_auth
DATABASE_URL=postgresql://auth:<强密码>@db:5432/mini_auth
JWT_SECRET=<长随机串>
JWT_ACCESS_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=30
CORS_ORIGINS=https://bot.liuyidi.me,https://auth.liuyidi.me
```

## 3. 验收

```bash
docker compose -f /opt/auth/docker-compose.yml ps
curl -fsS http://127.0.0.1:8000/health          # 若直接 expose；默认仅经 Caddy
curl -fsS https://auth.liuyidi.me/health
curl -fsS -o /dev/null -w "docs %{http_code}\n" https://auth.liuyidi.me/docs
```

证书由 Caddy 自动申请；失败时检查：DNS、安全组 80/443、Cloudflare 勿开橙云挡 ACME。

## 4. 日常更新

```bash
ssh -i ~/Downloads/tencent_cloud.pem ubuntu@150.158.146.191
cd /opt/auth/mini-auth
git fetch origin main && git reset --hard origin/main
cd /opt/auth
docker compose build api
docker compose up -d api
curl -fsS https://auth.liuyidi.me/health
```

## 5. 与阿里云业务对接（后续）

| 端 | 动作 |
|----|------|
| RN / WebUI | 登录 base URL → `https://auth.liuyidi.me` |
| minibot | bootstrap 验 `Bearer` access JWT（`iss=https://auth.liuyidi.me`） |
| JWT | 第一版可共享 `JWT_SECRET`（HS256）；上线 JWKS 后改拉公钥 |

设计见 [`auth-platform-design.md`](./auth-platform-design.md)。

## 6. 仓库改名说明

本地与 GitHub 目标名：**mini-auth**（原 `deepseek-chat-api`）。

- 本机路径：`/Users/liuyidi/github/mini-auth`
- GitHub：`github.com/liuyidi/mini-auth`（`gh repo rename mini-auth` 或网页 Settings → Rename）
- 服务器目录名固定用 `mini-auth`，即使曾从旧仓 clone

## 常见坑

| 现象 | 处理 |
|------|------|
| pull python/postgres 超时 | 确认 `daemon.json` DaoCloud；compose/Dockerfile 写死 `docker.m.daocloud.io/...` |
| pip 慢 | 用 `Dockerfile.ecs`（阿里云 PyPI） |
| OOM | 确认 swap；勿在同机再堆无关大服务 |
| 证书失败 | `dig auth.liuyidi.me`、安全组、Caddy 日志 `docker compose logs caddy` |
| GitHub 慢 | `ghfast.top` 前缀 clone/fetch |
