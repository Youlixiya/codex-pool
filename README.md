# codex-pool

本地 HTTP 代理 + Web 管理后台（**单端口**）：在网页配置上游账号并签发 API Key，Codex CLI 用同一地址的 `/v1` 自动路由 / 故障转移。

## 快速开始

```bash
uv sync
docker compose up -d mysql redis
cp .env.example .env

# 构建前端（首次）
cd web && npm install && npm run build && cd ..

# 一条命令：管理后台 + API + Codex 代理
uv run codex-pool-admin --reload --port 8790
```

浏览器打开 **http://127.0.0.1:8790**（需已 `npm run build` 生成 `web/dist`）。

### 前端开发（5173，可选）

```bash
# 终端 1：后端 + 已构建的静态资源（或仅 API）
uv run codex-pool-admin --reload --port 8790

# 终端 2：Vite 热更新
cd web && npm run dev
```

浏览器打开 **http://127.0.0.1:5173**（`npm run dev` 会同时打印 **Network** 内网地址，如 `http://192.168.x.x:5173`）。不要混用 8790 的缓存页面；若 `/assets/*.js` 404，先 `npm run build` 或强制刷新。

内网其他设备访问 5173 时，本机仍需运行 `codex-pool-admin`（8790），代理才会通。

| 地址 | 用途 |
|------|------|
| **8790** | 生产式单端口（`web/dist` + API + 代理） |
| **5173** | 仅前端热更新，`/api`、`/v1` 代理到 8790 |

## Codex CLI 配置

`~/.codex/config.toml`：

```toml
model = "gpt-5.3-codex"
model_provider = "codex-pool"

[model_providers.codex-pool]
name = "OpenAI"
base_url = "http://127.0.0.1:8790/v1"
wire_api = "responses"
env_key = "CODEX_POOL_API_KEY"
```

```bash
export CODEX_POOL_API_KEY="sk-cp-你在控制台创建的key"
codex
```

## 路由（同一端口）

| 路径 | 用途 |
|------|------|
| `/` | 管理后台（静态页，需 `web/dist`） |
| `/api/v1/*` | 管理 API |
| `/v1/*` | Codex CLI 代理 |
| `/healthz` | 健康检查 |

## 环境变量

| 字段 | 说明 |
|------|------|
| `DATABASE_URL` | MySQL（必填） |
| `REDIS_URL` | 配置热重载 |
| `JWT_SECRET` / `ADMIN_*` | 管理后台登录 |
| `WEB_DIST` | 前端构建目录（默认 `web/dist`） |

## 验证

```bash
curl http://127.0.0.1:8790/healthz
curl -H "Authorization: Bearer sk-cp-你的key" http://127.0.0.1:8790/v1/models
```

Docker 全栈见 [DOCKER.md](./DOCKER.md)。**生产环境（2G VPS 一键部署）**见 [DEPLOY_PROD.md](./DEPLOY_PROD.md)。

## ChatGPT 网页授权（上游）

管理后台 → **上游账号** → 类型选 **chatgpt (OAuth)** → 填写名称 → **打开网页授权**。

流程与 Codex CLI 相同（PKCE + `localhost:1455` 回调），凭证写入 `~/.codex-pool/auth/<名称>.json`，保存后即可用于代理。

注意：本机 **1455 端口** 需空闲（若正在运行 `codex login` 会冲突）。也可在 `.env` 中调整 `CHATGPT_OAUTH_CALLBACK_PORT` 与 `CHATGPT_OAUTH_REDIRECT_URI`（须与 OpenAI 注册一致）。

授权成功后，上游列表与编辑对话框会展示 **5 小时** 与 **一周** 额度（来自 ChatGPT `wham/usage` 接口，与 Codex CLI `/status` 同源）。
