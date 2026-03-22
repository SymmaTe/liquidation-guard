# Liquidation Guard

Aave V3 仓位监控与 AI 分析工具，帮助你实时掌握借贷健康度，在被清算前及时预警并给出操作建议。

> 当前仅支持以太坊主网（Ethereum Mainnet）。

**网址**：[liquidation-guard.vercel.app](https://liquidation-guard.vercel.app)

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 仓位总览 | 查看任意地址的 Aave V3 抵押、借款、健康度 |
| 压力测试 | 模拟 ETH/BTC 价格下跌，预览健康度变化 |
| 自动监控告警 | 健康度低于阈值时自动发 Telegram 通知 + AI 建议 |
| AI 对话分析 | 与 AI 实时对话，分析仓位风险并给出补仓/还款方案 |

---

## 快速上手

### 第一步：连接钱包

点击左下角「Connect Wallet」，使用 MetaMask 或其他浏览器钱包连接。连接后即可查看自己的 Aave V3 仓位。

### 第二步：查看仓位

进入**仓位页**，自动加载当前钱包的 Aave V3 仓位数据，包括：

- 总抵押（USD）、总借款（USD）、净资产
- 健康度（HF）：绿色 ≥ 1.4 安全 / 黄色 ≥ 1.1 注意 / 红色 < 1.1 危险
- 每种质押代币的数量、价值、LTV、清算阈值
- 每种借款代币的数量、价值

也可以手动输入任意以太坊地址查询他人仓位。

**压力测试**：拖动页面下方滑块，模拟 ETH/BTC 价格下跌后的健康度变化。

---

## 设置页配置

进入**设置页**完成以下配置，开启监控和 AI 功能。

### RPC URL（可选，推荐填写）

用于后端监控节点连接。不填使用公共节点（检查间隔最快 5 分钟）；填写后最快可 30 秒检查一次。

**推荐使用 Alchemy（免费）**：
1. 访问 [alchemy.com](https://alchemy.com) 注册账号
2. 创建新 App，选择 Ethereum Mainnet
3. 进入 App 详情 → API Key，复制 HTTPS 格式 URL
4. 粘贴到设置页 RPC URL 输入框，点击「测试连接」验证

### 监控地址

添加需要监控的以太坊地址（最多 2 个，可以不是自己的钱包）。连接钱包后会自动填入当前地址。

### 检查间隔

- 无 RPC URL：最快 5 分钟
- 有 RPC URL：最快 30 秒

### 告警阈值

- **默认**：根据你的质押组合动态加权计算（更精准）
- **自定义**：手动设置注意线（最高 1.5）和紧急线，注意紧急线必须低于注意线
- 告警冷却：注意级别默认 30 分钟内不重复发，紧急级别默认 5 分钟内不重复发
- 级别从注意升级到紧急时立即触发，不受冷却限制

### Telegram 告警

1. 在 Telegram 搜索 **@userinfobot**，点击 Start，获取你的 Chat ID（数字）
2. 将 Chat ID 填入设置页
3. 点击「发送测试消息」验证是否能收到

告警消息包含：健康度、告警级别、抵押/借款金额、AI 分析建议。

### AI 配置

支持 5 个 AI 提供商，需要填写对应平台的 API Key 和模型 ID。Key 加密存储于服务器，不会泄露。

**强烈推荐 DeepSeek**：价格极低（约为 GPT-4o 的 1/20），分析质量完全够用，国内用户充值方便。注册后充值 5 元可用相当长时间。

| 提供商 | 获取 Key | 常用模型 ID |
|--------|----------|-------------|
| ⭐ DeepSeek（推荐） | [platform.deepseek.com](https://platform.deepseek.com) → API Keys | `deepseek-chat` |
| Anthropic Claude | [console.anthropic.com](https://console.anthropic.com) → API Keys | `claude-sonnet-4-6` |
| OpenAI | [platform.openai.com](https://platform.openai.com) → API Keys | `gpt-4o` / `gpt-4o-mini` |
| Google Gemini | [aistudio.google.com](https://aistudio.google.com) → Get API Key | `gemini-2.0-flash` |
| 豆包 | [console.volcengine.com](https://console.volcengine.com) → 模型推理 | `doubao-pro-32k-241215` |

> 豆包模型 ID 需要日期后缀，请在火山引擎控制台「模型推理 → 模型广场」查看当前可用的完整 ID。

填写后点击「测试 AI 连接」验证（5 秒超时）。

---

## 自动监控工作原理

1. 后端每 10 秒扫描所有开启监控的用户
2. 根据每个用户设置的检查间隔决定是否查询链上数据
3. 健康度数据每 5 分钟写入数据库一次（用于历史图表）
4. 健康度低于阈值时：
   - 调用 AI 分析仓位风险和操作方案
   - 通过 Telegram 发送告警 + AI 建议
5. 若 AI Key 余额不足：告警照常发送，AI 分析暂停，并发一次充值提醒

---

## AI 对话

进入**对话页**，直接用自然语言询问仓位情况：

- "我的仓位现在安全吗？"
- "我距离清算还有多远？"
- "我应该补充多少 ETH？"
- "帮我分析一下还款和补仓哪个更划算"

AI 会实时查询链上数据并给出具体的数量和金额建议。需要先在设置页配置 AI Key。

---

## 常见问题

**Q：没收到 Telegram 告警？**
A：检查 ① 监控开关是否打开 ② Chat ID 是否正确 ③ 点测试按钮是否能收到 ④ 健康度是否真的低于阈值

**Q：健康度显示 ∞？**
A：该地址在 Aave 没有借款，健康度无限大，这是正常的。

**Q：RPC URL 测试失败？**
A：确认 URL 是 HTTPS 格式，选的是 Ethereum 主网（Mainnet），Key 未过期。

**Q：AI 对话响应很慢？**
A：AI 需要调用工具查询链上数据，通常需要 10-30 秒，正常现象。

**Q：AI Key 安全吗？**
A：Key 经加密后存储于服务器，前端无法读取明文，日志中不会出现。

**Q：支持哪些代币？**
A：支持 Aave V3 主网所有代币，包括 ETH、WBTC、USDC、USDT、DAI、LINK、AAVE、wstETH 等。

**Q：推荐填写自己的 RPC URL 吗？**
A：强烈推荐。不填时使用公共节点，高频监控下可能遇到限速，AI 分析也会更慢。Alchemy 免费额度对个人用户完全够用。

---

## 反馈与联系

遇到问题或有功能建议，欢迎通过以下方式反馈：

- Twitter / X：[@MingYangFa40352](https://x.com/MingYangFa40352)
- GitHub：[SymmaTe](https://github.com/SymmaTe)
- Telegram：[@SymmaTe2026](https://t.me/SymmaTe2026)
- 邮箱：fmy1908809325@gmail.com
