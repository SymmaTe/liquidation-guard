# 命令参考手册

记录项目开发过程中所有用过的 Bash 命令，附带解释。

---

## 1. 项目初始化

### 创建项目目录结构
```bash
mkdir -p /home/incent/liquidation-guard
cd /home/incent/liquidation-guard
mkdir -p agent contracts frontend
```
- `mkdir -p` → 创建目录，`-p` 表示如果父目录不存在就一并创建
- 我们创建了三个子目录：`agent`（AI代码）、`contracts`（合约）、`frontend`（前端）

---

## 2. Python 虚拟环境（venv）

### 什么是 venv
venv 是 Python 的虚拟环境，让每个项目有独立的 Python 依赖，互不冲突。

### 创建 venv
```bash
python3 -m venv agent/venv
```
- `python3 -m venv` → 用 Python 内置模块创建虚拟环境
- `agent/venv` → 虚拟环境存放的路径（在 agent 文件夹下）

### 激活 venv
```bash
source agent/venv/bin/activate
```
- `source` → 在当前 shell 中执行脚本（不是新开一个 shell）
- 激活后命令行前面会显示 `(venv)`，说明已进入虚拟环境
- **每次新开终端都要重新激活**

### 退出 venv
```bash
deactivate
```

---

## 3. Python 依赖安装

### 安装项目所需的库
```bash
cd agent
source venv/bin/activate
pip install anthropic web3 python-dotenv requests
```

| 库 | 用途 |
|----|------|
| `anthropic` | 调用 Claude AI API |
| `web3` | 连接以太坊，读写链上数据 |
| `python-dotenv` | 读取 `.env` 文件里的配置（API Key 等） |
| `requests` | 发送 HTTP 请求 |

### 把依赖写入 requirements.txt（方便别人复现环境）
```bash
pip freeze > requirements.txt   # 把当前环境所有库版本写入文件
pip install -r requirements.txt # 别人用这个命令一键安装所有依赖
```

---

## 4. Foundry 合约初始化

### 在 contracts 目录初始化 Foundry 项目
```bash
cd contracts
forge init . --no-git
```
- `forge init .` → 在当前目录初始化 Foundry 项目（会创建 src、test、script 目录）
- `--no-git` → 不单独初始化 git（因为我们在外层已经有 git 了）
- 执行后会自动安装 `forge-std`（Foundry 标准库）

### 编译合约
```bash
forge build
```

### 运行合约测试
```bash
forge test
```

---

## 5. Git 初始化

### 在项目根目录初始化 git
```bash
cd /home/incent/liquidation-guard
git init
```
- `git init` → 创建 `.git` 目录，开始追踪文件变化

### 查看当前状态
```bash
git status
```

### 提交代码
```bash
git add .
git commit -m "描述这次改了什么"
```

---

## 6. 环境变量配置

### 复制模板，创建真实配置文件
```bash
cp .env.example .env
```
- `.env.example` → 模板文件，记录需要哪些变量（提交到 git）
- `.env` → 真实配置，填入真实 Key（**不能提交到 git，已加入 .gitignore**）

---

## 7. Python 脚本运行

### 运行各脚本
```bash
cd /home/incent/liquidation-guard/agent
source venv/bin/activate

python3 read_position.py   # Step 2：读取链上仓位数据
python3 ai_analyzer.py     # Step 3：AI 生成风险报告（本地测试用，功能已被 agent.py 覆盖）
python3 agent.py           # Step 4：完整 AI Agent 对话模式（Tool Use）
python3 monitor.py         # Step 7：异步多用户监控（从 Supabase 读配置，Ctrl+C 退出）
```

**每次新开终端的完整流程：**
```bash
cd /home/incent/liquidation-guard/agent
source venv/bin/activate
python3 <脚本名>.py
```

---

## 8. 常用检查命令

### 确认 RPC 连接是否正常
```bash
python3 -c "
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('YOUR_RPC_URL'))
print('Connected:', w3.is_connected())
print('Block:', w3.eth.block_number)
"
```
- `-c` → 直接在命令行执行一段 Python 代码，不需要创建文件

### 确认 Python 和工具版本
```bash
python3 --version
node --version
/home/incent/.foundry/bin/forge --version
```

---

## 9. Agent 工具说明

agent.py 里定义了五个 AI 可调用的工具：

| 工具 | 数据来源 | 用途 |
|------|---------|------|
| `get_aave_position(wallet)` | Aave V3 Pool 合约 | 查询仓位健康度、总抵押、总借款 |
| `get_token_price(symbol)` | Chainlink 链上预言机 | 获取 ETH/WBTC 等实时 USD 价格 |
| `get_token_ltv(symbol)` | Aave DataProvider 合约（链上实时读取）| 查询代币 LTV 和清算阈值 |
| `get_collateral_breakdown(wallet)` | Aave DataProvider + Chainlink | 质押明细 + 借款明细（数量/价值/LTV）|
| `calculate_repayment_needed(...)` | 本地公式计算 | 计算还款需要多少代币（优先推荐）|
| `calculate_collateral_needed(...)` | 本地公式计算 | 计算补仓需要多少代币 |

> 所有链上 ABI 和 Web3 逻辑集中在 `read_position.py`，agent.py 只做工具调度。

**AI 查询仓位的标准流程（系统提示已内置，agent.py 和 monitor.py 一致）**：
```
1. get_aave_position        → 总览（健康度/总抵押/总借款）
2. get_collateral_breakdown → 明细（各代币数量/价值/独立LTV/清算阈值）
3. get_token_price          → 各代币实时价格（Chainlink）
4. calculate_collateral_needed → 各代币补仓数量，按优先级建议：
   - 稳定币（USDC/USDT/DAI）价格不跌，适合保守用户
   - ETH/WBTC 清算阈值高，补仓效率更高
   - LINK/AAVE 清算阈值低，不优先推荐
```

**支持的代币及 Chainlink Feed 地址**：

| 代币   | Feed 地址 | 备注 |
|--------|-----------|------|
| ETH    | 0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419 | |
| WBTC   | 0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c | |
| USDC   | 0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6 | |
| USDT   | 0x3E7d1eAB13ad0104d2750B8863b489D65364e32D | |
| DAI    | 0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9 | |
| LINK   | 0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c | |
| AAVE   | 0x547a514d5e3769680Ce22B2361c10Ea13619e8a9 | |
| WSTETH | 0xCfE54B5cD566aB89272946F602D76Ea879CAb4a8 | stETH/USD × getStETHByWstETH |

> **WSTETH 价格**：`wsteth.getStETHByWstETH(1e18) / 1e18 × stETH/USD`
> wstETH 是 stETH 的非再基础封装，价格比 stETH 约高 20%+（累积质押收益）。

**快速测试 get_collateral_breakdown**：
```bash
cd /home/incent/liquidation-guard/agent
source venv/bin/activate
python3 -c "
from read_position import get_user_collateral_breakdown
import json
result = get_user_collateral_breakdown('0x176F3DAb24a159341c0509bB36B833E7fdd0a132')
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

**测试混合质押模拟（mock_collateral_breakdown）**：
```bash
python3 -c "
from read_position import mock_collateral_breakdown
import json
result = mock_collateral_breakdown('0xTest', [
    {'symbol': 'ETH',  'amount': 2.0,  'price_usd': 2000.0},
    {'symbol': 'WBTC', 'amount': 0.05, 'price_usd': 60000.0},
    {'symbol': 'USDC', 'amount': 3000, 'price_usd': 1.0},
])
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

### 切换模型（只改 .env，代码不用动）
```bash
# 使用 DeepSeek（推荐，便宜）
AI_PROVIDER=deepseek
AI_MODEL=deepseek/deepseek-chat
DEEPSEEK_API_KEY=sk-xxx

# 使用 Ollama（免费本地）
AI_PROVIDER=ollama
AI_MODEL=ollama/llama3.2

# 使用 Claude
AI_PROVIDER=anthropic
AI_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=sk-ant-xxx
```

---

## 10. AI 模型安装（LiteLLM + Ollama）

### LiteLLM（统一多模型接口）
```bash
cd agent
source venv/bin/activate
pip install litellm
```
- `litellm` → 一个库支持 100+ AI 模型（OpenAI / Anthropic / Gemini / Ollama 等）
- 用户只需在 `.env` 里改 `AI_PROVIDER` 和 `AI_MODEL`，代码不用改

### 安装 Ollama（本地免费运行 AI 模型）

**第一步：安装系统依赖**
```bash
sudo apt-get install zstd
```
- `zstd` → Ollama 安装包需要的解压工具，缺少会报错

**第二步：安装 Ollama**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```
- 从官网下载并运行安装脚本
- 安装路径：`/usr/local/bin/ollama`

**第三步：启动 Ollama 服务**
```bash
ollama serve
```
- 启动本地 AI 服务，默认监听 `http://localhost:11434`
- **需要保持这个终端开着**，或者在后台运行

**第四步：下载模型**
```bash
ollama pull llama3.2
```
- 下载 Meta 的 Llama 3.2 模型（约 2GB）
- 下载一次后本地缓存，之后不需要联网

**验证 Ollama 是否正常**
```bash
ollama list          # 查看已下载的模型
ollama run llama3.2  # 直接对话测试（输入 /bye 退出）
```

### .env 模型配置说明
```bash
AI_PROVIDER=ollama              # 默认用本地 Ollama（免费）
AI_MODEL=ollama/llama3.2        # 模型名

# 切换到 Claude（付费）：
# AI_PROVIDER=anthropic
# AI_MODEL=claude-haiku-4-5-20251001

# 切换到 OpenAI（付费）：
# AI_PROVIDER=openai
# AI_MODEL=gpt-4o-mini
```

---

## 11. 每次开发时的启动流程

每次打开电脑重新开发，按顺序执行：

**终端 1：启动后端 API 服务（Step 7 开始需要）**
```bash
cd /home/incent/liquidation-guard/backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**终端 2：启动前端**
```bash
cd /home/incent/liquidation-guard/frontend
npm run dev
# 浏览器访问 http://localhost:3000
```

**终端 3：运行 Agent 脚本（可选，本地测试用）**
```bash
cd /home/incent/liquidation-guard/agent
source venv/bin/activate        # 激活 Python 虚拟环境
python3 monitor.py              # 自动监控（长期运行）
# 或
python3 agent.py                # AI Agent 对话（手动查询）
python3 ai_analyzer.py          # 单次 AI 风险分析
python3 read_position.py        # 只读链上数据
```

---

## 12. Telegram 告警配置

### 创建 Bot
1. Telegram 搜索 `@BotFather`，发送 `/newbot`
2. 填写 display name 和 username（username 必须以 `bot` 结尾）
3. 拿到 Token，格式：`数字:字母数字混合`

### 获取 Chat ID
```bash
# 先给 bot 发任意一条消息，再访问：
https://api.telegram.org/bot{TOKEN}/getUpdates
# 找 "chat":{"id": 后面的数字即为 TELEGRAM_CHAT_ID
```

### 填入 .env
```bash
TELEGRAM_BOT_TOKEN=你的token
TELEGRAM_CHAT_ID=你的chat_id
```

### 测试发送
```bash
cd /home/incent/liquidation-guard/agent
source venv/bin/activate
python3 -c "
from dotenv import load_dotenv
load_dotenv('../.env')
import os, requests
token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')
r = requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
    json={'chat_id': chat_id, 'text': '✅ Liquidation Guard 连接成功'})
print(r.json())
"
```

### 告警冷却规则
| 级别 | 冷却时间 | 说明 |
|------|---------|------|
| 🟡 注意 | 30 分钟 | 有缓冲，不需要频繁打扰 |
| 🔴 紧急 | 5 分钟  | 需要快速响应 |
| 级别升级 | 立即触发 | 注意 → 紧急 不等冷却 |

---

## 13. 前端开发（Next.js + wagmi）

### 初始化项目
```bash
cd /home/incent/liquidation-guard/frontend
yes "" | npx create-next-app@latest . --typescript --tailwind --app --no-eslint --src-dir --import-alias "@/*" --use-npm
```
- `create-next-app` → 官方脚手架，自动配置 TypeScript + Tailwind CSS + App Router
- `--src-dir` → 源码放在 `src/` 目录下，结构更清晰
- `--import-alias "@/*"` → 允许用 `@/components/Foo` 代替相对路径 `../../components/Foo`

### 安装 Web3 依赖
```bash
npm install wagmi viem @tanstack/react-query @rainbow-me/rainbowkit
```

| 库 | 用途 |
|----|------|
| `wagmi` | React hooks，读链上数据、发交易 |
| `viem` | 底层以太坊库（wagmi 依赖）|
| `@tanstack/react-query` | 数据缓存，避免重复 RPC 请求 |
| `@rainbow-me/rainbowkit` | 钱包连接 UI（备用）|

### 开发与构建
```bash
cd /home/incent/liquidation-guard/frontend

npm run dev    # 启动开发服务器（热更新），访问 http://localhost:3000
npm run build  # 生产构建（检查 TypeScript 类型错误）
npm run start  # 运行生产构建（需先 build）
```

### 环境变量（前端专用）
前端使用 `.env.local`（不提交 git），变量名必须以 `NEXT_PUBLIC_` 开头才能在浏览器访问：
```bash
# frontend/.env.local
NEXT_PUBLIC_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/你的key  # 可选，不填默认用 LlamaRPC
```
> 生产环境可以不填，前端默认使用 `eth.llamarpc.com` 公共节点，零成本。

### 文件结构
```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          ← 全局外壳（Providers + Sidebar）
│   │   ├── page.tsx            ← 首页 /（地址输入 + 仓位展示）
│   │   ├── providers.tsx       ← wagmi + React Query 注入
│   │   ├── stress/page.tsx     ← 压力测试模拟器
│   │   ├── settings/page.tsx   ← 监控设置页
│   │   ├── chat/page.tsx       ← AI 对话页（ChatGPT 式，历史持久化）
│   │   └── globals.css         ← 全局样式
│   ├── components/
│   │   ├── Sidebar.tsx         ← 左侧导航栏 + 钱包连接
│   │   ├── ClientOnly.tsx      ← 解决 wagmi hydration 问题
│   │   ├── PositionCard.tsx    ← 健康因子 / 总抵押 / 总借款（加权动态阈值）
│   │   ├── BreakdownTable.tsx  ← 质押明细 + 借款明细表
│   │   └── LiquidationPrices.tsx ← 单代币清算价格估算
│   ├── hooks/
│   │   └── usePosition.ts      ← usePosition / useFullBreakdown / useTokenPrices
│   └── lib/
│       ├── wagmi.ts            ← wagmi 配置（链、RPC、钱包连接器）
│       ├── aave.ts             ← Aave 合约地址 + ABI + 代币配置 + Chainlink feeds
│       └── settings.ts         ← 用户设置类型定义 + localStorage 读写
└── .env.local                  ← 前端环境变量（不提交 git）
```

### 每次前端开发启动
```bash
cd /home/incent/liquidation-guard/frontend
npm run dev
# 浏览器访问 http://localhost:3000
```

---

## 14. 后端开发（FastAPI）

### 初始化虚拟环境并安装依赖
```bash
cd /home/incent/liquidation-guard/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 启动开发服务器
```bash
cd /home/incent/liquidation-guard/backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
# 访问 http://localhost:8000/docs 查看自动生成的 API 文档
```
- `--reload` → 代码改动后自动重启，无需手动重启
- `/docs` → Swagger UI，可直接在浏览器测试所有接口

### 启动多用户监控
```bash
cd /home/incent/liquidation-guard/agent
source venv/bin/activate
pip install supabase   # 首次需要安装
python3 monitor.py
```
监控从 Supabase `user_settings` 表读取 `monitor_enabled=True` 的用户，自动并发检查。

### 环境变量（根目录 `.env`，后端和 monitor 共用）
```bash
TELEGRAM_BOT_TOKEN=     # Telegram 告警推送
SUPABASE_URL=           # Supabase 项目 URL
SUPABASE_ANON_KEY=      # Supabase anon key
MONITOR_POLL_INTERVAL=10  # 主循环间隔（秒），默认 10
```

### 文件结构
```
backend/
├── main.py              ← FastAPI 入口，注册路由、CORS 配置
├── db.py                ← Supabase 客户端初始化
├── routes/
│   ├── test.py          ← 测试连接（/test/rpc、/test/ai、/test/telegram）
│   ├── settings.py      ← 用户设置（GET/POST /settings/{wallet}）
│   ├── chat.py          ← 对话历史（5 个接口，首条消息自动生成标题）
│   └── agent.py         ← AI Agent 对话（SSE 流式，Tool Use，并行工具调用）
├── requirements.txt     ← Python 依赖
└── venv/                ← Python 虚拟环境（不提交 git）

agent/
├── db.py                ← Supabase 客户端（monitor 用，路径同 backend/db.py）
├── monitor.py           ← 异步多用户监控（从 Supabase 读配置）
└── read_position.py     ← 支持 rpc_url 参数，每用户独立 Web3 实例
```

### 所有后端接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 服务健康检查 |
| `/test/rpc` | POST | 验证 RPC URL（eth_blockNumber，5 秒超时）|
| `/test/ai` | POST | 验证 AI API Key + 模型 ID（5 秒超时）|
| `/test/telegram` | POST | 发送测试消息到用户 Chat ID |
| `/settings/{wallet}` | GET | 读取用户设置（从 Supabase）|
| `/settings/{wallet}` | POST | 保存用户设置（ai_key 不存后端）|
| `/chat/{wallet}` | GET | 获取对话列表 |
| `/chat/{wallet}` | POST | 新建对话 |
| `/chat/{wallet}/{id}` | DELETE | 删除对话（级联删消息）|
| `/chat/{wallet}/{id}` | GET | 获取对话消息 |
| `/chat/{wallet}/{id}` | POST | 追加消息（role 必须小写，首条用户消息自动更新对话标题）|
| `/agent/chat` | POST | AI Agent 对话（SSE 流式，LiteLLM Tool Use，支持 5 个 provider）|

### Supabase 数据库表

| 表 | 说明 |
|---|---|
| `user_settings` | 用户设置（主键：wallet_address）|
| `chat_conversations` | 对话列表（关联 wallet_address）|
| `chat_messages` | 消息记录（关联 conversation_id，级联删除）|
| `health_history` | 健康因子历史（每 300s 写一条，保留 7 天）|

### 前端对接
前端通过 `NEXT_PUBLIC_BACKEND_URL` 环境变量指向后端：
```bash
# frontend/.env.local
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000       # 本地开发
NEXT_PUBLIC_BACKEND_URL=https://xxx.railway.app     # 生产环境（Railway）
```
不填默认 `http://localhost:8000`。

---

## 15. 路径速查

| 目录/文件 | 说明 |
|-----------|------|
| `/home/incent/liquidation-guard/` | 项目根目录 |
| `agent/` | Python AI Agent 代码 |
| `agent/venv/` | Python 虚拟环境（不提交 git）|
| `agent/read_position.py` | Step 2：读取 Aave 仓位的脚本 |
| `agent/ai_analyzer.py` | Step 3：AI 风险分析脚本 |
| `agent/agent.py` | Step 4：完整 AI Agent（Tool Use + 多轮对话）|
| `agent/monitor.py` | Step 7：异步多用户监控（从 Supabase 读配置）|
| `agent/db.py` | Supabase 客户端（monitor 专用）|
| `contracts/` | Solidity 合约（Foundry 项目）|
| `backend/` | FastAPI 后端（Step 7）|
| `backend/db.py` | Supabase 客户端初始化 |
| `backend/routes/test.py` | 测试连接接口（RPC / AI / Telegram）|
| `backend/routes/settings.py` | 用户设置 CRUD |
| `backend/routes/chat.py` | 对话历史 CRUD（5 个接口）|
| `backend/routes/agent.py` | AI Agent 对话接口（SSE 流式 + Tool Use）|
| `frontend/` | Next.js 前端（Step 6）|
| `frontend/src/app/` | 页面和全局配置 |
| `frontend/src/components/` | 可复用 UI 组件 |
| `frontend/src/hooks/` | 读取链上数据的 React hooks |
| `frontend/src/lib/` | wagmi 配置 + Aave 合约定义 |
| `.env` | 真实配置（不提交 git）|
| `.env.example` | 配置模板（提交 git）|
| `COMMANDS.md` | 本文件，命令参考手册 |
| `PROGRESS.md` | 各步骤进度记录与核心概念说明 |
