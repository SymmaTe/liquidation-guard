# 项目开发进度

记录每个步骤的目标、完成状态、涉及文件和核心知识点。

---

## ✅ Step 1 — 项目结构搭建

**目标**：建立整个项目的骨架，配置好开发环境。

**完成内容**：
- 创建 `agent/`、`contracts/`、`frontend/` 三个子目录
- 初始化 Python 虚拟环境（venv），安装依赖
- 初始化 Foundry 合约项目
- 初始化 Git 仓库
- 配置 `.env` 和 `.gitignore`

**涉及文件**：
```
liquidation-guard/
├── agent/
│   ├── venv/               ← Python 虚拟环境
│   └── requirements.txt    ← 依赖列表
├── contracts/              ← Foundry 项目
├── frontend/               ← 待开发
├── .env                    ← 真实配置（不提交 git）
├── .env.example            ← 配置模板
├── .gitignore
└── README.md
```

**用到的工具**：
- `python3 -m venv` — 虚拟环境
- `forge init` — Foundry 初始化
- `git init` — Git 初始化

---

## ✅ Step 2 — 读取 Aave V3 链上仓位数据

**目标**：用 Python 连接以太坊主网，调用 Aave V3 合约读取真实仓位数据。

**完成内容**：
- 用 `web3.py` 连接 Alchemy RPC（以太坊主网）
- 调用 Aave V3 Pool 合约的 `getUserAccountData()` 函数
- 解析返回的 6 个原始链上数字（除以 1e18 / 1e8 换算为可读格式）
- 实现模拟仓位功能（`mock_position`），不依赖真实钱包也能测试
- 实现混合质押模拟（`mock_collateral_breakdown`），可指定多种代币组合
- 根据健康度显示风险等级（🟢 安全 ≥1.4 / 🟡 注意 ≥1.1 / 🔴 紧急 <1.1，稳定币为主时阈值更低）
- `print_position(pos, breakdown)` 将仓位总览与逐代币明细表合并到同一个终端框内，单一质押也显示明细行
- `__main__` 展示四种模式：单一质押 mock / Chainlink 实时价格 / 混合质押 mock / 真实链上地址

**涉及文件**：
- `agent/read_position.py`

**核心概念**：

| 概念 | 说明 |
|------|------|
| ABI | 合约使用说明书，告诉 Python 函数名、参数、返回值 |
| `getUserAccountData()` | Aave V3 核心函数，返回总抵押、总借款、健康度等 |
| `getUserReserveData()` | AaveProtocolDataProvider，查询单个代币的质押/借款状态 |
| `getReserveConfigurationData()` | AaveProtocolDataProvider，读取代币 LTV 和清算阈值（basis points） |
| Health Factor | 健康度 = 总抵押 × 加权清算阈值 / 总借款，< 1 会被清算 |
| LTV vs 清算阈值 | LTV 是可借比例（入场），清算阈值是清算触发点（守护），两者不同 |
| 加权清算阈值 | = Σ(各代币价值 × 各代币清算阈值) / 总抵押，混合质押时各不相同 |
| `1e18` | 链上数字没有小数点，除以 1e18 得到真实数字 |
| Checksum 地址 | 以太坊地址的大小写规范（EIP-55），web3.py 强制要求 |

**Aave V3 Pool 合约地址（主网固定）**：
```
0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2
```

---

## ✅ Step 3 — AI 风险分析报告（多模型支持）

**目标**：把链上数据传给 AI，让 AI 用中文生成风险报告和操作建议。

**完成内容**：
- 用 `LiteLLM` 统一接口支持多种 AI 模型
- 实现 Provider 与 API Key 的自动匹配（避免把 Claude key 发给 DeepSeek）
- `analyze_position(pos, breakdown=None)` 支持传入混合质押明细
  - 有 breakdown 时，Prompt 列出每种代币的数量/价值/LTV，AI 给出分代币补仓建议
  - 无 breakdown 时，退化为单一质押分析（向下兼容）
- 计算"价格再跌多少触发清算"并告知 AI
- `__main__` 演示两个场景：单一质押三档风险 + 混合质押（ETH+WBTC+USDC）

**涉及文件**：
- `agent/ai_analyzer.py`

**支持的模型（只需改 `.env`）**：

| Provider | .env 配置 | 费用 |
|----------|-----------|------|
| Ollama (本地) | `AI_MODEL=ollama/llama3.2` | 免费 |
| DeepSeek | `AI_MODEL=deepseek/deepseek-chat` | 极便宜（~$0.14/百万tokens）|
| Anthropic | `AI_MODEL=claude-haiku-4-5-20251001` | 便宜 |
| OpenAI | `AI_MODEL=gpt-4o-mini` | 中等 |

**Token 消耗估算**：
- 每次分析一个仓位：约 250 tokens
- DeepSeek 新账号免费额度（500万tokens）：可用约 2万次
- 每天监控一个用户（每小时分析一次）：能用约 2 年

**核心概念**：

| 概念 | 说明 |
|------|------|
| LiteLLM | 统一接口库，一套代码调用 100+ AI 模型 |
| Prompt Engineering | 告诉 AI 角色、数据、输出格式，引导输出质量 |
| `max_tokens` | 限制 AI 输出长度，控制费用 |
| f-string | Python 字符串模板，`{变量}` 自动替换 |

---

## ✅ Step 4 — Tool Use（AI Agent 核心）

**目标**：让 AI 自己决定要调用哪些工具，真正实现"Agent"而不是简单的问答。

**完成内容**：
- 定义六个工具供 AI 调用：
  - `get_aave_position(wallet_address)` — 查询链上真实仓位（总抵押/借款/健康度）
  - `get_token_price(symbol)` — Chainlink 链上预言机实时价格
  - `get_token_ltv(symbol)` — 实时从 Aave V3 链上读取 LTV 和清算阈值（非硬编码）
  - `get_collateral_breakdown(wallet_address)` — 质押明细 + 借款明细（数量/价值/LTV）
  - `calculate_repayment_needed(...)` — 计算还款所需代币数量（通常比补仓更高效）
  - `calculate_collateral_needed(...)` — 计算补仓所需代币数量
- AI 自动判断何时调用工具、传什么参数（`tool_choice="auto"`）
- 多工具联动：AI 在一次对话中可连续调用多个工具
- 实现多轮对话，AI 能记住上下文追问
- **查询仓位标准流程**：系统提示要求 AI 必须依次调用两个工具
  1. `get_aave_position` → 总览（健康度、总抵押、总借款）
  2. `get_collateral_breakdown` → 明细（各代币数量、价值、独立 LTV）
- **混合质押补仓建议**：AI 分代币给出补仓优先级
  - 稳定币（USDC/USDT/DAI）价格不跌，适合保守用户
  - ETH/WBTC 清算阈值高，补仓效率更高
  - LINK/AAVE 清算阈值低，不优先推荐

**涉及文件**：
- `agent/agent.py`
- `agent/read_position.py`（所有链上/ABI 逻辑）

**实际运行效果**：
```
你："我抵押了$10000 ETH，借了$6500，要补多少ETH回到健康度1.5？"
  ↓
AI 调用 get_token_price(ETH)       → Chainlink 实时价 $2311
AI 调用 get_token_ltv(ETH)         → 清算阈值 82.5%
AI 调用 calculate_collateral_needed → 需补 0.7867 ETH（$1818）
  ↓
AI 生成完整中文补仓建议

告警场景（混合质押）：
  ↓
AI 调用 get_collateral_breakdown(wallet)
→ { ETH: 0.5个 $1157 LTV=80.5%, USDT: 500个 $500 LTV=75% }
AI 调用 calculate_collateral_needed(...)
→ 需补充 X 个代币
```

**Chainlink 支持的价格 Feed（= 可查询质押明细的代币）**：

| 代币   | Chainlink Feed 地址 | 说明 |
|--------|---------------------|------|
| ETH    | 0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419 | ETH/USD |
| WBTC   | 0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c | BTC/USD |
| USDC   | 0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6 | USDC/USD |
| USDT   | 0x3E7d1eAB13ad0104d2750B8863b489D65364e32D | USDT/USD |
| DAI    | 0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9 | DAI/USD |
| LINK   | 0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c | LINK/USD |
| AAVE   | 0x547a514d5e3769680Ce22B2361c10Ea13619e8a9 | AAVE/USD |
| WSTETH | 0xCfE54B5cD566aB89272946F602D76Ea879CAb4a8 | 用 stETH/USD feed 间接计算 |

> **wstETH 价格计算**：wstETH 是 stETH 的非再基础封装，价格不等于 stETH。
> 正确算法：`wstETH 合约.getStETHByWstETH(1e18) / 1e18 × stETH/USD`
> 约比直接用 stETH/USD 高 20%+（因为 wstETH 累积了质押收益）。
>
> 只监控这 8 种代币：Aave V3 主流质押资产 + 均有 Chainlink 链上报价。
> `get_user_collateral_breakdown` 只遍历这 8 个地址（避免遍历全部 30+ 资产超时）。

**核心概念**：

| 概念 | 说明 |
|------|------|
| Tool Use / Function Calling | AI 主动调用外部函数获取数据，而不是靠训练数据回答 |
| `tools` 参数 | 告诉 AI 有哪些工具可用（名称、描述、参数格式）|
| `tool_choice="auto"` | AI 自己决定要不要调用工具，以及调用哪个 |
| `tool_calls` | AI 返回的工具调用请求，包含函数名和参数 |
| `role: "tool"` | 把工具执行结果返回给 AI 的消息格式 |
| 对话历史 `messages` | 每轮对话都追加到列表，AI 能记住上下文 |
| 跨轮次追踪结果 | `pos_result` / `bd_result` 在 while 循环外声明，避免多轮工具调用时丢失数据 |

**工具调用流程**：
```
1. 用户发消息
2. AI 返回 tool_calls（想调用哪个工具）
3. 我们执行工具，拿到结果
4. 把结果以 role="tool" 加入对话历史
5. AI 再次被调用，基于结果生成最终回答
```

---

## ✅ Step 5 — 自动监控循环（已在 Step 7 重构为多用户版）

**目标**：定时轮询监控地址健康度，低于阈值时自动触发 AI 告警。

**完成内容（原始单用户版）**：
- 动态告警阈值：按质押/借款代币波动性加权计算
- 告警冷却：注意 30 分钟，紧急 5 分钟，级别升级立即触发
- Telegram 推送 + AI 分析建议（Tool Use）
- Ctrl+C 优雅退出

> Step 7 已将 monitor.py 重构为异步多用户版，见 Step 7。

**核心概念**：

| 概念 | 说明 |
|------|------|
| 动态阈值 | 按质押/借款代币波动性加权，稳定币可接受更低健康度 |
| 借款侧风险 | 借了 ETH/WBTC 等波动资产，涨价会增加债务 USD 价值，同样压低 HF |
| 告警冷却 | 避免健康度持续低位时每轮都触发 AI 分析，节省 token |
| Telegram Bot | `sendMessage` API，只推送到配置的 chat_id |

---

## ✅ Step 6 — 前端 Dashboard

**目标**：Web 界面让用户连接钱包即可查看仓位、压力测试、监控设置、AI 对话。

**技术栈**：
- Next.js 16 + wagmi v3 + viem（Vercel 部署，免费）
- 直接调用 Aave V3 + Chainlink 链上合约，无需自定义合约
- Tailwind CSS 深色 UI，ClientOnly 解决 wagmi hydration 问题

**完成功能**：

1. **仓位总览页 `/`**
   - 地址输入框（支持查询任意地址，优先已连接钱包）
   - 地址跨页面持久化（localStorage）
   - 健康因子卡片：总抵押 / 总借款 / HF / 加权清算阈值
   - 颜色标签：加权动态阈值（稳定币 1.2/1.05，波动币 1.4/1.1）或用户自定义阈值
   - 质押明细表 + 借款明细表（数量 + USD 价值）
   - 清算价格估算：每个波动代币独立计算，考虑加权清算阈值

2. **压力测试页 `/stress`**
   - 质押代币价格下跌滑块（稳定币锁定）
   - 借款代币价格上涨滑块（稳定币锁定）
   - 实时重算加权清算阈值 + 健康因子
   - HF 进度条：白线=当前值，彩色填充=模拟值，双色直观对比

3. **监控设置页 `/settings`**
   - 监控开关 + 监控地址列表（连钱包后自动填入，支持多地址）
   - 自定义 RPC URL（填写后解锁最快 30 秒检查频率，不填默认 LlamaRPC 公共节点）
   - RPC URL 测试连接按钮（eth_blockNumber 验证，5 秒超时）
   - 自定义检查间隔：无 RPC 最快 5 分钟（2×2 布局），有 RPC 最快 30 秒（3×2 布局）
   - 切换 RPC 时自动重置超出范围的间隔选择
   - 自定义告警阈值（注意线 / 紧急线 HF，关闭时使用加权动态阈值）
   - Telegram Chat ID + 自定义通知间隔 + **测试发送按钮**（Step 7 已接入后端）
   - AI 提供商选择（Anthropic / OpenAI / Google / DeepSeek / 豆包）+ API Key + 模型 ID
   - AI 测试连接按钮（Step 7 已接入后端，5 秒超时）
   - 所有设置同步 Supabase（Step 7 已完成，ai_key 加密存服务器，前端不可读取）

4. **AI 对话页 `/chat`**
   - ChatGPT 式布局：左侧对话历史列表 + 右侧全高聊天区
   - 对话历史按日期分组，显示最后一条消息预览，支持删除
   - 对话持久化到 **Supabase 后端**（Step 7 已完成迁移，不再用 localStorage）
   - 改走后端 `POST /agent/chat`，AI 通过 Tool Use 主动查链上数据
   - 支持 5 个 AI 提供商（用户 API Key 传后端，后端用 LiteLLM 统一调用）
   - 右上角 HF 实时徽章
   - 加载时显示"正在查询链上数据并分析…"

**默认 RPC 策略**：
- 前端仓位查询：用户自定义 RPC → LlamaRPC 公共节点（eth.llamarpc.com）
- 用户 key 零泄露，服务器零 RPC 成本

**alert 术语统一**：
- 🟢 安全（HF ≥ 加权警告线）
- 🟡 注意（加权危险线 ≤ HF < 加权警告线）
- 🔴 紧急（HF < 加权危险线）
- 前端 PositionCard 和后端 monitor.py 使用同一套加权阈值逻辑

**涉及文件**：
```
frontend/src/
├── app/
│   ├── page.tsx              ← 仓位总览
│   ├── stress/page.tsx       ← 压力测试
│   ├── settings/page.tsx     ← 监控设置
│   └── chat/page.tsx         ← AI 对话
├── components/
│   ├── Sidebar.tsx           ← 导航 + 钱包连接
│   ├── ClientOnly.tsx        ← hydration 修复
│   ├── PositionCard.tsx      ← 健康因子卡片（加权动态阈值）
│   ├── BreakdownTable.tsx    ← 明细表
│   └── LiquidationPrices.tsx ← 清算价格估算
├── hooks/usePosition.ts      ← 链上数据 hooks
└── lib/
    ├── aave.ts               ← 合约地址 + ABI + 代币配置
    ├── wagmi.ts              ← wagmi 配置（优先用户 RPC → LlamaRPC）
    └── settings.ts           ← 用户设置类型 + localStorage + computeWeightedThresholds
```

**核心概念**：

| 概念 | 说明 |
|------|------|
| `useReadContract` | wagmi hook，读单个合约函数 |
| `useReadContracts` | 批量读多个合约，减少 RPC 请求 |
| ClientOnly | 包裹 wagmi 相关组件，服务端渲染时返回 null 避免 hydration 错误 |
| 加权清算阈值 | 模拟时随各代币权重变化重新计算，不用链上固定值 |
| 清算价格公式 | `liqPrice_i = (debt - otherWeightedLiq) / (amount_i × liqThreshold_i)` |
| computeWeightedThresholds | 前端实现与 monitor.py 相同的加权阈值逻辑，保证前后端一致 |

**待完成（移至后续步骤）**：
- 一键补仓/还款按钮 — Step 8 合约
- 历史健康因子走势图 — Step 7 续（接口 + 前端图表）

---

## ✅ Step 7 — 后端 API（FastAPI 多用户）+ 健康历史图表

**目标**：将现有 Python 逻辑包装为 API，支持多用户并发访问。

**技术栈**：
- FastAPI 异步后端（Railway 部署）
- Supabase PostgreSQL（免费 500MB）

**✅ 已完成**：

1. **FastAPI 骨架** — CORS、路由注册、`/health` 接口
2. **测试连接接口**
   - `POST /test/rpc` — eth_blockNumber 验证，5 秒超时
   - `POST /test/ai` — 支持 5 个 provider，5 秒超时
   - `POST /test/telegram` — 用服务端 Bot Token 发测试消息
3. **用户设置接口**
   - `GET /settings/{wallet}` — 从 Supabase 读取
   - `POST /settings/{wallet}` — upsert，ai_key Fernet 加密后存 Supabase；GET 只返回 has_ai_key bool
4. **对话历史接口（5 个）**
   - GET / POST / DELETE 对话，GET / POST 消息
   - 第一条用户消息写入时自动更新对话标题
5. **Supabase 数据库**
   - `user_settings`、`chat_conversations`、`chat_messages`、`health_history` 四张表
   - health_history 索引：`(wallet_address, recorded_at desc)`
6. **read_position.py 重构**
   - 移除模块级 `w3` / `pool` / `data_provider` / `wsteth_contract`
   - 所有查询函数新增 `rpc_url=None` 参数，`@lru_cache` 按 URL 缓存 Web3 实例
   - 不填 RPC → 优先 `MAINNET_RPC_URL` → fallback LlamaRPC
7. **monitor.py 重构（异步多用户版）**
   - 从 Supabase 实时拉取 `monitor_enabled=True` 用户列表
   - `asyncio.gather` 并发检查所有用户，Web3/AI 调用放入 `run_in_executor`
   - 每用户独立 RPC URL、告警阈值、Telegram chat_id、冷却时间
   - 健康历史写入限速：最快每 300s 写一条，控制数据量
   - 每天自动清理 7 天前的历史记录
   - 主循环间隔 10s（`MONITOR_POLL_INTERVAL`），检查间隔选项：无 RPC 最快 5 分钟，有 RPC 最快 30 秒～3 小时
8. **monitor AI 分析优化（`agent.py`）**
   - `while True` → `range(6)`，加 30s timeout，max_tokens 512
   - Telegram 告警：纯文本三段式（分析结果 / 方案对比 / 操作建议），禁止 Markdown 符号
   - AI 余额不足：首次发一条 Telegram 提示，后续静默降级，充值后自动恢复
9. **AI Agent 接口（`routes/agent.py`）**
   - `POST /agent/chat` — SSE 流式响应，接收消息历史、用户 API Key、模型/Provider、RPC URL、钱包地址
   - LiteLLM `acompletion` 异步 Tool Use 循环（最多 6 轮，timeout 60s，max_tokens 2000）
   - 工具调用轮次静默收集，最终文字轮次实时 SSE emit；多工具并行用 `asyncio.gather`
   - 6 个工具：get_aave_position、get_token_price、get_token_ltv、get_collateral_breakdown、calculate_repayment_needed、calculate_collateral_needed
   - Provider 前缀映射：deepseek→`deepseek/`、google→`gemini/`、doubao→`volcengine/`
   - API Key 余额不足返回友好提示
   - 系统提示产品知识库：RPC 注册教程、Telegram 配置、各提供商模型 ID、FAQ
10. **前端 chat 页迁移与优化**
    - 对话历史从 localStorage 迁移至 Supabase 后端持久化
    - 流式读取 SSE，立即插入空气泡边流边填充；收到首 chunk 后隐藏转圈动画
    - 消息历史截取最近 10 条传后端；取消按钮 AbortController；前端超时 120s
    - Markdown 渲染（react-markdown + @tailwindcss/typography）

11. **健康历史接口**
    - `GET /history/{address}?days=7` — 查询指定地址最近 N 天的健康度历史
    - desc 排序 + limit 5000 + reverse，确保超大数据集时优先返回最新数据
12. **健康历史走势图（前端）**
    - `HealthHistoryChart.tsx`：recharts LineChart，24 桶时间聚合
    - 时间范围切换：2h / 24h / 3d / 7d，选择结果持久化 localStorage
    - 用户自定义警戒线（从 `/settings/{wallet}` 读取）
    - 5 分钟自动刷新；监控中断显示为断线（`connectNulls={false}`）
    - 颜色点：绿（HF≥1.4）/ 黄（≥1.1）/ 红（<1.1）
    - 图表地址跟随前端 queryAddress，查谁显示谁的历史

**系统架构**：
```
用户浏览器（Vercel）
    ↓  wagmi 钱包连接
FastAPI 后端（Railway）
    ↓              ↓
Supabase DB    Telegram Bot（告警推送，用用户 chat_id）

前端仓位查询：用户自定义 RPC → LlamaRPC（服务器零成本）
监控端查询：同上，每用户独立 RPC
```

**数据量估算（7 天保留）**：

| 场景 | health_history | chat_messages | 合计 |
|---|---|---|---|
| 100 用户 300s 轮询 | ~40MB | ~12MB | ~55MB ✅ |
| 100 用户 60s 轮询 | ~40MB | ~12MB | ~55MB ✅ |

---

## ✅ Step 7.5 — 生产部署

**完成内容**：

1. **后端（Railway）**
   - `railway.toml`：Start Command = `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - `.python-version`：固定 Python 3.12.3（避免 3.13 兼容性问题）
   - `requirements.txt` 复制到项目根目录供 Railpack 识别
   - CORS 配置精确域名：`https://liquidation-guard.vercel.app`
   - 环境变量：`SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY`
   - 数据库 RLS 启用，后端用 service_role key 绕过（无需策略）

2. **监控进程（Railway 同项目第二个 service）**
   - `agent/railway.toml`：Start Command = `python3 monitor.py`
   - Root Directory 设置为 `agent`
   - `agent/db.py` 改用 `SUPABASE_SERVICE_ROLE_KEY`（RLS 启用后 anon key 不可用）
   - `agent/requirements.txt` 补充 `supabase>=2.4.0`
   - AI 分析异常捕获从 `RuntimeError` 改为 `Exception`（防止 litellm 异常崩溃进程）
   - 环境变量：`SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY`、`TELEGRAM_BOT_TOKEN`
   - **⚠️ 待定**：监控告警 AI 分析暂未配置（当前显示"AI 分析暂不可用"），待决策方案：
     - 方案 B：平台统一 API key（环境变量）
     - 方案 C：告警附 App 链接，用户自行点开 AI 分析

3. **前端（Vercel）**
   - Root Directory = `frontend/`
   - `frontend/.npmrc`：`legacy-peer-deps=true`（解决 wagmi v3 / rainbowkit v2 依赖冲突）
   - `frontend/vercel.json`：`installCommand = npm install --legacy-peer-deps`
   - 环境变量：`NEXT_PUBLIC_BACKEND_URL` = Railway 后端 URL
   - 删除设置页开发占位提示文字（Step 7 相关小字）

4. **部署文档**：`DEPLOY.md`

**线上地址**：
- 前端：`https://liquidation-guard.vercel.app`
- 后端：`https://liquidation-guard-production.up.railway.app`

---

## ⬜ Step 8 — 闪电贷保护合约（Solidity）

**目标**：当用户没有闲置资金时，用闪电贷一笔交易完成调仓，提升健康度。

**适用场景**：
- 用户有超额抵押但手里没有多余 USDC 还款
- 通过闪电贷借 USDC → 还债 → 取出部分抵押品 → swap 还贷，净效果是降杠杆

**与直接操作的区别**：
- 用户有闲钱 → 前端直接调 Aave（Step 6，无需合约）
- 用户没闲钱但有超额抵押 → 闪电贷合约（Step 8）

**AI 新增逻辑**：
- `get_wallet_balance(address, token)` — 查用户钱包闲置资金
- `calculate_flashloan_params()` — 计算闪电贷参数和最终效果
- AI 先判断用户是否有闲置资金，再决定推荐直接操作还是闪电贷

**计划内容**：
- 闪电贷合约（继承 Aave FlashLoanReceiverBase）
- Foundry 测试 + Sepolia 测试网部署
- monitor.py AI 新增闲置资金判断工具

---

## Update 2026-03-22 — AI 分析优化 + Bug 修复

### AI 分析重构
- 输出改为自然语言，内部紧迫度/阈值不暴露给用户
- 紧迫度公式：`(hf - danger_t) / (alert_t - danger_t)`，低于50%紧急，高于50%可观望
- 目标健康度 = 用户注意线 + 0.05（最小缓冲，刚好脱离警戒区）
- DANGER/WARNING 分两套模板，语气各异
- 禁止 AI 重复调用 get_aave_position / get_collateral_breakdown（数据已预取，节省 token）
- 用户 rpc_url 正确传入 AI 工具调用链（get_token_price 等），避免公共节点 429

### Bug 修复
- run_agent loop 6→12，max_tokens 512→1024，修复多代币地址 AI 返回 None
- 每用户独立 AI 锁（_ai_locks dict），不同用户并行，同用户多地址串行
- Telegram 告警：DANGER 显示紧急阈值，WARNING 显示告警阈值
- 注意线 HF 前端上限收紧至 1.5，紧急线上限动态跟随注意线 - 0.01
- 测试按钮成功状态 3 秒后自动消失
- AI 余额不足误报：收紧关键词匹配
- f-string 内中文弯引号导致 SyntaxError 修复
- token_lines 去除旧价格，避免与 get_token_price 实时价格冲突

### 发布前审计修复（2026-03-22）
- 后端校验：dangerHF ≥ warningHF 或监控开启但无地址时拒绝保存并返回错误
- 设置保存：网络失败或后端拒绝时显示 alert，不再静默显示"已保存"
- 三个测试按钮加 10s AbortSignal 超时，不再卡死
- 新建对话失败时 alert 提示，不再静默无反应
- chat formatDate 跨月 bug 修复（用时间戳差值替代 getDate() 相减）
- chat textarea 自动撑高，最大 160px
- chat 无对话时右侧显示"开始新对话"引导提示
