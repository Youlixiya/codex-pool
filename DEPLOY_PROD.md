# 生产环境一键部署（2G/2核 VPS）

宿主机 **80 端口**映射到应用（容器内 8790），同一入口提供：

- 管理后台（Vue）
- `/api/v1` 管理 API
- `/v1` Codex 代理

配置好域名 **A 记录**指向服务器后，可直接访问 `http://你的域名`，无需带端口号。

## 前置条件

- Docker + Docker Compose v2
- 防火墙 / 安全组放行：**80**（Web + API + 代理）
- ChatGPT 网页授权上游时另放行 **1455**（OAuth 回调）
- 宿主机 **80 端口未被占用**（如已有 Nginx，需先停掉或改 `APP_HTTP_PORT`）

## 一键部署

```bash
cd /path/to/codex-pool
cp .env.prod.example .env.prod
# 编辑 .env.prod：PUBLIC_URL=http://你的域名、密码、JWT_SECRET 等
chmod +x scripts/deploy-prod.sh
./scripts/deploy-prod.sh
```

浏览器打开 `PUBLIC_URL`（例如 `http://pool.example.com`）。

## 域名与 HTTPS

1. 域名控制台添加 **A 记录** → 服务器公网 IP  
2. `.env.prod` 中设置：
   - `PUBLIC_URL=http://pool.example.com`
   - `CORS_ORIGINS=http://pool.example.com`（HTTPS 上线后改为 `https://...`）  
3. 需要 HTTPS 时，可在前加 Caddy / Nginx 反代并申请证书；或后续把 `APP_HTTP_PORT` 改为其它端口，由反代监听 443→80。

## 常用命令

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f app
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build app
docker compose -f docker-compose.prod.yml --env-file .env.prod down
```

## Codex CLI

```toml
[model_providers.codex-pool]
name = "OpenAI"
base_url = "http://你的域名/v1"
wire_api = "responses"
env_key = "CODEX_POOL_API_KEY"
```

```bash
export CODEX_POOL_API_KEY="sk-cp-控制台创建的密钥"
codex
```

## 资源与容量

| 服务 | 内存上限（compose） |
|------|---------------------|
| MySQL | 512M |
| Redis | 96M |
| app | 768M |

2GB 机器建议加 **1GB swap**。

## ChatGPT OAuth

- `CHATGPT_OAUTH_REDIRECT_URI=http://你的域名:1455/auth/callback`
- 防火墙放行 **1455**

## 与开发 compose 的区别

| | 开发 `docker-compose.yml` | 生产 `docker-compose.prod.yml` |
|--|---------------------------|--------------------------------|
| 对外端口 | 8790 | **80** |
| 前端构建 | 本机或独立 web 容器 | 镜像内多阶段构建 |

本地开发仍用 8790：`uv run codex-pool-admin --reload`，见 [DOCKER.md](./DOCKER.md)。
