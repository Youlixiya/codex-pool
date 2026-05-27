<div align="center">

# codex-pool

**自托管 Codex CLI 账号池：Web 管理台 + 单端口 `/v1` 代理。**

[English](./README.md) · [反馈问题](https://github.com/Youlixiya/codex-pool/issues)

[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

</div>

---

## 简介

[Codex CLI](https://github.com/openai/codex) 通过 `base_url` 访问模型。**codex-pool** 作为中间层：在浏览器里配置上游账号、签发 API Key，开发者只需把 Codex 指向本机一个地址。代理负责**路由、故障转移、用量统计与费用估算**，适合个人与小团队轻量部署。

## 特性

- **单进程单端口** — 管理后台、REST API、`/v1` 代理一体
- **多租户** — 注册、独立上游池与 API Key
- **上游池与 failover** — 多账号按序尝试，失败自动切换
- **用量与计费** — Token 用量与预估费用统计
- **ChatGPT OAuth** — 网页授权上游（PKCE，与 Codex CLI 同源流程）
- **额度面板** — 展示 5 小时 / 一周额度（ChatGPT usage API）
- **运维简单** — 默认数据目录 `~/.codex-pool/`，2 核 2G 可跑

## 路由

| 路径 | 说明 |
|------|------|
| `/` | Vue 管理台（需 `web/dist`） |
| `/api/v1/*` | 登录、上游、Key、仪表盘 |
| `/v1/*` | Codex CLI 代理 |
| `/healthz` | 健康检查 |

## 快速开始

环境：**Python 3.12+**、[uv](https://github.com/astral-sh/uv)、**Node.js 18+**（仅构建前端时需要）。

```bash
git clone https://github.com/Youlixiya/codex-pool.git
cd codex-pool

uv sync
cp .env.example .env
# 修改 JWT_SECRET、ADMIN_PASSWORD、CORS_ORIGINS

cd web && npm install && npm run build && cd ..

uv run codex-pool-admin --reload --port 8790
```

浏览器打开 **http://127.0.0.1:8790**，使用 `.env` 中的管理员登录，或通过 **注册** 创建账号。

### 前端热更新（可选）

```bash
uv run codex-pool-admin --reload --port 8790
cd web && npm run dev   # http://127.0.0.1:5173，API 代理到 8790
```

## Codex CLI 配置

将 Codex 指向本池的 `/v1`，需同时配置 **`~/.codex/config.toml`** 与 **`~/.codex/auth.json`**（可用 `CODEX_HOME` 改目录）。凭证写在 `auth.json` 的 `OPENAI_API_KEY`，**无需环境变量**。

在管理后台 **API Keys** → **配置说明** 可复制与当前 Key 名称、访问地址完全一致的片段。以下为 Key 名 `default`、本机 `8790` 的示例：

**`~/.codex/config.toml`**

```toml
model = "gpt-5.5"
model_provider = "codex-pool-default"

[model_providers.codex-pool-default]
name = "OpenAI"
base_url = "http://127.0.0.1:8790/v1"
wire_api = "responses"
```

**`~/.codex/auth.json`**

```json
{
  "auth_mode": "apikey",
  "OPENAI_API_KEY": "sk-cp-你的完整API_Key"
}
```

保存后运行 `codex`；也可在列表使用 **CC Switch** 一键导入。

## 服务器部署（2 核 2G）

```bash
git clone https://github.com/Youlixiya/codex-pool.git && cd codex-pool
uv sync && cp .env.example .env
# 编辑 JWT_SECRET、CORS_ORIGINS=http://你的域名

cd web && npm install && npm run build && cd ..

uv run codex-pool-admin --host 0.0.0.0 --port 8790 --log-level info
```

数据目录默认 `~/.codex-pool/`。systemd 示例：[scripts/codex-pool.service.example](./scripts/codex-pool.service.example)。生产环境建议 Nginx/Caddy 做 HTTPS 反代。

## 环境变量

见 [`.env.example`](./.env.example)，勿提交 `.env`。

| 变量 | 说明 |
|------|------|
| `JWT_SECRET` / `ADMIN_*` | 登录；首次启动创建 admin |
| `CORS_ORIGINS` | 管理后台允许的浏览器来源 |
| `DATABASE_URL` | 可选；默认 `~/.codex-pool/codex_pool.db` |
| `BILLING_*` | 每百万 token 单价 |
| `CHATGPT_*` | OAuth 回调端口与凭证目录 |

## ChatGPT 网页授权

管理后台 → **上游账号** → **chatgpt (OAuth)** → **打开网页授权**。本机 **1455** 端口需空闲（可通过 `CHATGPT_OAUTH_CALLBACK_PORT` 修改）。

## 参与贡献

欢迎 Issue 与 PR，见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 许可证

[MIT](./LICENSE)
