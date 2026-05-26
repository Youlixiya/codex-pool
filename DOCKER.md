# Docker 部署

## 启动全部服务

```bash
./scripts/pull-base-images.sh
cd web && npm install && npm run build && cd ..
docker compose up -d --build
```

## 服务地址

| 服务 | 地址 |
|------|------|
| 管理后台 + API + Codex 代理 | http://localhost:8790 |
| MySQL | localhost:3307 |
| Redis | localhost:6379 |

`admin-api` 容器内已包含 `web/dist`，浏览器直接访问 **8790** 即可。可选保留 `web` 容器（5173）仅作纯静态镜像部署。

默认管理员：`admin` / `admin123`

## Codex CLI

```toml
base_url = "http://127.0.0.1:8790/v1"
```

```bash
export CODEX_POOL_API_KEY="sk-cp-你在控制台创建的key"
```

## 本地开发（不用 Docker 跑 Python）

```bash
docker compose up -d mysql redis
uv sync
cd web && npm run build && cd ..
uv run codex-pool-admin --reload --port 8790
```
