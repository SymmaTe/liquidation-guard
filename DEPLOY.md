# Liquidation Guard 部署文档

## 架构概览

- **前端**：Vercel (`liquidation-guard.vercel.app`)
- **后端 API**：Railway service 1 (`liquidation-guard-production.up.railway.app`)
- **监控进程**：Railway service 2（同一个 project，Root Directory: `agent`）
- **数据库**：Supabase（RLS 已启用，后端用 service_role key 绕过）

---

## 前端部署（Vercel）

1. 登录 [vercel.com](https://vercel.com)，导入 GitHub repo `SymmaTe/liquidation-guard`
2. **Root Directory** 设置为 `frontend`
3. 环境变量：
   - `NEXT_PUBLIC_BACKEND_URL` = `https://liquidation-guard-production.up.railway.app`
4. 部署后域名：`liquidation-guard.vercel.app`

> `frontend/.npmrc` 已配置 `legacy-peer-deps=true`，解决 wagmi/rainbowkit 版本冲突
> `frontend/vercel.json` 已配置 `installCommand: npm install --legacy-peer-deps`

---

## 后端部署（Railway）

### 项目：`liquidation-guard` → service 1

1. 登录 [railway.app](https://railway.app)，创建 project，New Service → GitHub Repo → `liquidation-guard`
2. **Root Directory**：留空（项目根目录）
3. Start Command 由 `railway.toml` 自动配置：`cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
4. `.python-version` 已固定 Python 3.12.3
5. 环境变量：
   - `SUPABASE_URL` = Supabase 项目 URL
   - `SUPABASE_SERVICE_ROLE_KEY` = Supabase service_role 密钥

验证：访问 `https://liquidation-guard-production.up.railway.app/health` 返回 `{"status":"ok"}`

---

## 监控进程部署（Railway）

### 同一个项目：`liquidation-guard` → service 2

1. 在 `liquidation-guard` project 画布空白处右键 → New Service → GitHub Repo → `liquidation-guard`
2. **Root Directory** 设置为 `agent`
3. Start Command 由 `agent/railway.toml` 自动配置：`python3 monitor.py`
4. 环境变量：
   - `SUPABASE_URL` = 同上
   - `SUPABASE_SERVICE_ROLE_KEY` = 同上
   - `TELEGRAM_BOT_TOKEN` = Telegram Bot Token

验证：Railway 日志中出现 `Liquidation Guard 多用户监控启动`

---

## 注意事项

- 监控 AI 分析：当前未配置，告警只发基础数据（健康度、抵押、借款）
- 数据保留：health_history 表每 7 天自动清理一次旧记录
- CORS：后端已配置允许 `liquidation-guard.vercel.app`
- AI key：用户在设置页填写，仅存浏览器 localStorage，不上传服务器

---

## 环境变量汇总

| 位置 | 变量名 | 说明 |
|------|--------|------|
| Vercel | `NEXT_PUBLIC_BACKEND_URL` | 后端 Railway URL |
| Railway 后端 | `SUPABASE_URL` | Supabase 项目 URL |
| Railway 后端 | `SUPABASE_SERVICE_ROLE_KEY` | Supabase service_role 密钥 |
| Railway 监控 | `SUPABASE_URL` | 同上 |
| Railway 监控 | `SUPABASE_SERVICE_ROLE_KEY` | 同上 |
| Railway 监控 | `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
