**Anna（anna.partners）是一款定位为 “AI Operating System / AI Partner” 的本地优先 AI Agent 平台。** 它不是单纯的聊天机器人，而是一个可以在用户设备上运行、具备持久记忆、能主动规划和执行任务，并把第三方 Agent / 脚本 / 工具包装成可分发 App 的系统。

Kate 给你的邮件正是针对他们的 **Founding Builder Program**（创始构建者计划），邀请你把 WeFinance（以及你之前的 MeetSpot、VibeDoc 等项目）重建成 Anna App，并通过真实用户牵引（MAU）获得持续月度资助。

### 1. 核心定位与架构
- **定位**：Personal AI Companion / AI OS。官方强调 “Anna is not AI. She's your companion.”——她会记住你的偏好、历史和上下文，适应你的沟通风格，主动规划任务，并调用子 Agent 完成复杂工作流。
- **架构（Hybrid）**：
  - **Anna Agent**：本地运行（macOS / Windows / Linux / 移动端），文件和工具调用留在用户设备上，数据不出本机。
  - **Anna Cloud Platform**：负责跨设备同步、持久记忆编排、用户账号体系。
- **安全**：数据本地优先 + 端到端加密同步；Sandbox 模式限制文件访问；Zen Mode 可关闭长期记忆；官方声明不出售/分享数据。
- **平台覆盖**：桌面（三大系统）、iOS/Android、Telegram / WeChat / WhatsApp、Web 浏览器。
- **能力亮点**：
  - 永久记忆（跨会话、跨设备）。
  - 主动规划 + 子 Agent 并行执行。
  - 可扩展 Skillbook（代码、研究、内容生成、数据分析、PPT、邮件等）。
  - 用户可选择自己的模型（BYOK 支持）。
  - 免费层覆盖日常需求。

用户可以直接在对话中调用已发布的 Anna App（类似 App Store 体验），App 能利用 Anna 提供的 runtime、记忆、UI 组件和工具调用。

### 2. 对开发者 / Builder 意味着什么
Anna 把 “平台层” 全部接管了：UI、沙箱执行、托管、用户账号、记忆、LLM 编排、权限。开发者主要负责**逻辑本身**。

可转化的资产包括：
- 现有 Python / Node.js 脚本
- AI Agents
- MCP Servers
- 工作流 / 工具链
- 甚至部分 SaaS 逻辑

技术栈概览（来自 Developer Hub）：
- **Tools (Executa)**：基于 JSON-RPC 2.0 over stdio 的独立插件，支持 Python / Node.js / Go / Rust SDK。
- **Skills (SKILL.md)**：声明式 Markdown 能力卡。
- **Apps**：把 Tools + Skills + 行为打包成可分发的体验（可带 HTML/JS/CSS 前端，也可纯逻辑）。

Docs 对 AI 编码工具友好（支持 `.md`、`llms.txt` 等），官方提供 GitHub 示例仓库和快速上手 demo。App 审核通常 3–5 个工作日。

### 3. Founding Builder Program 详细规则（当前核心机会）
这不是传统“选少数赢家”的比赛，而是**按真实牵引发月度 grant**。

**资金池与档位**（最高档单 App 可达 $5,000/月，9 月有 Launch Boost）：

| Tier | 要求 MAU | 9 月 Launch Boost | 后续每月 Grant |
|------|----------|-------------------|---------------|
| S (Galactic Sovereign) | 20,000+ | $6,000 | $5,000 |
| A (Growth Titans) | 10,000+ | $4,000 | $2,500 |
| B (Starship Commanders) | 4,000+ | $1,600 | $1,000 |
| C (Orbit Pioneers) | 1,000+ | $400 | $200 |
| D (Stratosphere Builders) | 500+ | $200 | $100 |
| E (Genesis Spark) | 200+ | $80 | $50 |

- **总池**：$80,000 / 月。
- **MAU 定义**：已登录的唯一 Anna 用户，完成一次 **Qualified App Run**（真正执行 App 主要功能并返回有意义结果）。Free Credits / 付费 Credits / BYOK 都 100% 计入。
- **不算**：仅打开/安装、失败运行、机器人、自测账号、虚假流量。
- **时间线**（当前 2026 年 8 月）：
  - 7 月 29 日 – 8 月 31 日：Build & Beta 阶段（8 月用量不计奖）。
  - 9 月 1 日：正式 MAU 统计开始。
  - 资格窗口：到 11 月 30 日。一旦达标（≥200 MAU），Founding Builder 身份永久（MAU 跌破 200 只暂停发放，恢复后继续）。
- **其他关键规则**：
  - 必须审核通过并上架 Marketplace。
  - 每月至少一次有意义更新。
  - 严格反作弊（克隆拆分、买量刷跑等会被聚合或取消资格）。
  - 发放：月末统计后 30 天内支付（银行/PayPal/Stripe 等）。
  - 有 Grandfathering 保护，预算接近上限时会暂停新准入，但已达标 App 不受影响。
  - 获批 Builder 可拿临时 Pro 权益。

**加入步骤**（邮件里也写了）：
1. 注册 https://anna.partners
2. 提交 Developer Access 表单
3. 加入 Discord + Luma 活动（https://luma.com/kmc1ddf9）
4. 按 Builder Overview 开始构建 / 迁移
5. 提交审核 → 上架 → 拉真实用户

官方规则完整版在论坛：https://forum.anna.partners/t/turn-your-ai-agents-apps-into-recurring-monthly-grants-join-the-anna-ai-os-founding-builder-program-up-to-80k-month-pool/205

### 4. 与你现有项目的契合度
Kate 特别提到 WeFinance 的 “receipt / statement → insights” 工作流，认为非常适合做成 Anna App（持久状态 + 工具 + 更丰富交互 UI）。你已有的 MeetSpot、VibeDoc 等也已证明能从原型走到真实用户，这正是他们看重的。

对你这种做 multi-agent、GTM、工具链的开发者来说，Anna 的价值在于：
- 降低分发和用户获取门槛（直接进他们的 App 生态）。
- 用现有 Agent/脚本快速包装上架。
- 可能拿到稳定的月度现金支持（如果能做出有真实 MAU 的产品）。

### 5. 目前生态状态与注意事项
- 产品仍较早期（YouTube 订阅量不大，官方账号粉丝也有限），但开发者工具和文档在快速完善。
- 有专门的 Hackathon 和 Workshop 系列视频（如何把工作流转成 Skill、如何快速发布 App 等）。
- 社区主要在 Discord 和官方论坛。
- 风险点：平台用户基数目前不大，MAU 增长需要自己做获客；规则对“真实使用”要求严格，刷量无效。

**建议行动顺序**：
1. 先注册账号 + 提交 Dev Access 表单（拿 Pro 权益和文档权限）。
2. 看官方 Builder Overview + GitHub 示例，把 WeFinance 核心流程快速迁一个 MVP。
3. 进 Discord 和论坛，看其他 Builder 在做什么、规则最新解读。
4. 8 月重点做产品打磨和早期用户测试，9 月开始正式冲 MAU。

如果你需要，我可以继续帮你：
- 拆解具体某个项目（比如 WeFinance）怎么映射到 Anna App 结构
- 整理 Dev Docs 关键链接和快速上手 checklist
- 对比它和 OpenClaw / Hermes / 其他本地 Agent 框架的差异

直接告诉我下一步想深入哪块就行。

---

## 执行计划（按 Build&Beta / Sept Boost 两个窗口排的具体日期）

### Phase 0：本周内（8/8 – 8/15），打地基
- [ ] 提交 Dev Access 表单 `forms.gle/4x7NhVyUeE7z7bqJ8`（拿 Dev Access + temporary Pro）
- [ ] 读 `staging.anna.partners/llms.txt` + GitHub 示例仓库，搞清楚 Executa（JSON-RPC over stdio）的最小可用接口长什么样
- [ ] 进 Discord `discord.gg/7ftTdsdMMz`，翻一下已上线的 App 案例和 App Review 常见拒绝原因（这块目前还是信息盲区）
- [ ] 定架构映射：`vision_ocr_service` / `chat_manager` / `recommendation_service` 三个服务包成几个 Executa tool；UI 优先用 Anna 原生组件，不自己重写前端（除非账单可视化这类强交互需求原生组件接不住）

### Phase 1：8/15 – 8/31，Build & Beta（零 MAU 压力，随便测）
- [ ] 写 stdio JSON-RPC adapter，把三个服务包出去（不用碰 auth/持久化，Anna 平台包）
- [ ] 小圈子内测：MeetSpot/VibeDoc 用户群 + 朋友，纯粹抓 bug，这阶段跑量不计 MAU
- [ ] **8/28 前提交 App Review**（留 3-5 工作日缓冲，确保赶在 9/1 之前正式上架，不然错过 Launch Boost 整个窗口）

### Phase 2：9/1 – 9/30，Launch Boost 窗口（真正决定档位的一个月）
- [ ] App 必须已上架，9/1 起计 MAU
- [ ] 拉新渠道（这是唯一的真实瓶颈，不是技术瓶颈）：
  - MeetSpot（500+ star、真实付费用户）里做一次 cross-promotion
  - VibeDoc（374 star）用户群同理
  - Discord/论坛里其他 builder 互相导流
  - 个人 X 发布
- [ ] 目标：保底摸到 Tier E（200+ MAU，$80 一次性），转化率理想的话冲 Tier D（500+，$200）

### Phase 3：10 – 11 月，维持资格
- [ ] 每月至少一次"有意义的产品改进"（硬性维持条件，别漏）
- [ ] 观察 MAU 稳定在哪一档，决定常规月度 grant 预期

### 唯一真正的决策变量
**200 MAU 现实不现实，取决于 MeetSpot/VibeDoc 现有用户池的转化率**——这个数字我不知道，你比我清楚这两个产品的活跃用户规模和用户愿不愿意跳去试一个新工具。技术迁移成本低（架构映射清楚），值不值得投入主要看这条转化路径通不通。

## Setup 实际进度（2026-08-08）

- ✅ Anna 账号建好，用户名改成 `calderbuild`
- ✅ Dashboard 登录可用（`anna.partners/dashboard`），默认模型 Qwen3.7 Plus
- ✅ Dev Access 表单已提交（Anna username: calderbuild，邮箱 johnrobertdestiny@gmail.com）
- ✅ 已加入官方 Discord，用户名 `calderbuild`

## Discord 逛了一圈，补充几条 Builder Overview 没写清楚的信息

来源：`#announcements` + `#general` 频道，2026-08-08 实测。社区确实活跃，官方人员（dora / kate）会直接答疑，不是死群。

### 平台最新能力（Anna 1.1.0 beta.97→beta.122 changelog，直接影响架构设计）
- **Async Jobs**：Tool 执行时间上限从 90 秒放宽到 **24 小时**，SDK 提供 `anna.tools.invokeAsyncAwait()`，带进度追踪和 AbortSignal 取消。WeFinance 的 vision OCR 调用（2-5s/张）远用不到这个上限，但账单批量处理如果做多图并发可以用异步任务模式
- **原生文档解析**：`doc_read` / `sheet_read` 平台工具原生支持 xlsx/xls/docx/pptx/pdf 解析，**不用自己维护解析栈**——如果以后想让用户直接传 Excel 账单明细而不只是账单截图，这块可以省掉
- **持久存储**：`$ANNA_WORKSPACE_DIR`，90 天保留期，idle agent 也不会被快速回收
- **开发者控制台自带 Analytics**：DAU 时间序列、滚动 WAU/MAU、token & cost 聚合，还有 `GET /developer/apps/{app_id}/stats` API——**MAU 不用自己埋点统计，Anna 后台直接看**

### 意外发现：Revenue Share（跟 Founding Builder Grant 是两件事，可以叠加）
- **70% 的"eligible usage profit"分给开发者**，T+1 自动日结，append-only ledger，**payout 门槛 $50**
- BYOK（用户带自己的 API key）调用 **零 Anna Energy 成本**——用户用自己的 key 不产生你的运营成本，但依然计入 MAU（只要是真实调用）

### App 发现机制（对应第 2 阶段的拉新计划）
- 每个发布的 App 自动生成 **SEO 友好的公开落地页**：`/store/@handle/slug`，带 OG 卡片 + JSON-LD + sitemap
- 分享按钮自带 **`?ref=` 渠道归因**（可以精确知道 MeetSpot/VibeDoc 导流过来多少人）+ `?action=install` 免登录墙直接安装流程

### App Review
- 现在有专门的 reviewer 通过 **PENDING_REVIEW 审核队列**跑 App，处理效率比之前快（具体审核标准细则 Discord 里没搜到，`co-creation` 论坛频道目前是空的，没有其他 builder 分享案例可参考——这块还是信息盲区，等自己提审时才能知道实际尺度）
- **2026-08-12 补充：状态机 + 通知机制已在 `anna.partners/developers/apps/app-publish`（"Publishing an App"）里白纸黑字，之前的信息盲区可以关掉了：**
  - 状态机：`DRAFT --submit--> PENDING_REVIEW --admin approve--> APPROVED --publish version--> PUBLISHED`，另有 `REJECTED`（打回可改后重提，不扣分）、`ARCHIVED`（下架，已装用户不受影响）两个分支
  - admin 走 `POST /super-admin/apps/{id}/approve`，body 带 `publish: bool`：`publish:true` 直接连审带发，一步到 `PUBLISHED`；`publish:false` 只到 `APPROVED`——**这种情况下不会自动上架**，还要自己回 Versions tab 点一次 "Publish" 才真正进 App Store
  - **关键坑：没有邮件通知**（原文 "There is no email notification today"），也**没有 SLA 承诺**（"no enforced SLA today; check My Apps in the Console for the current status"）——意味着只能自己定期回控制台查，或调 `GET /developer/apps/{id}` 看 `status` 字段，不会有任何主动推送告诉你审完了
  - Reviewer 至少会核两件事：manifest 对着 schema + 当前 Executa 目录重新校验一遍；listing 文案/截图和实际表现是否相符

### 更新一下 Phase 2 的行动项
- [ ] 发布时用 `?ref=` 参数分别标记 MeetSpot 导流 / VibeDoc 导流 / 个人 X 导流，跑完就知道哪个渠道转化率最高，不用瞎猜
- [ ] 关注 Revenue Share 是否也要单独开启/配置 payout profile（跟 Founding Builder Grant 走的是两条钱路，别搞混）

## SDK 架构映射（读完 `staging.anna.partners/llms.txt` + 关键文档，2026-08-08）

### Anna 的三层模型
- **Executa（Tool 或 Skill）**：最小单元。Tool = 任意语言写的常驻进程，走 **JSON-RPC 2.0 over stdio**（`describe` 返回 manifest，`invoke` 执行，日志走 stderr 别走 stdout）。Skill = 纯 Markdown 声明的"配方"，agent 按需读，没有自己的代码执行
- **Anna App**：打包一个或多个 Executa + `system_prompt_addendum`，发布到 App Store，用户 `#提及` 才激活。`schema:1` = 纯 chat 增强（无自定义 UI），`schema:2` = 带沙箱 iframe 自定义 UI

官方给的决策捷径：**先做 Skill 验证流程 → 需要真 I/O/凭据/流式再拆成 Tool → 要发布给最终用户再包成 App**。不要一上来就冲最复杂的 schema:2。

### WeFinance 三个服务 → 三个 Executa Tool 的映射
| WeFinance 现有服务 | 映射成 | 备注 |
|---|---|---|
| `services/vision_ocr_service.py`（账单图片→交易） | Tool: `wefinance-ocr` | ✅ 已用 Agent Sessions 的 `attachments` 写完并本地验证通过（见下），不用自己的 key |
| `modules/chat_manager.py`（对话理财建议） | Tool: `wefinance-chat` | 纯文本，✅ 已用 Anna Sampling 写完（见上方 Setup 进度） |
| `services/recommendation_service.py`（可解释投资建议） | Tool: `wefinance-recommend` | 纯文本 + 结构化输出，Sampling 的 `responseFormat: json_schema` 正好对上现有的"结构化推荐+推理链"需求 |

### ~~关键发现：Sampling 不支持图片输入~~ → 已解决：用 Agent Sessions 的 attachments（2026-08-09）

最初判断 Sampling（`sampling/createMessage`）的 `messages[].content` 只支持文本，`executa-image.md` 那套是图片生成/编辑不是理解，所以以为 OCR 只能自带 key。**这个判断被 Kate 的回信推翻了**：她指出 Sampling 确实只支持文本，但 **"Session"（Agent Sessions）支持图片输入**。翻了 `developers/tools/executa-agent.md`（Agent Sessions 协议文档）没找到图片参数，又翻了她给的 Builder Overview 关联文档 `developers/apps/llm-and-agent.md`，在 "3.0a Native image inputs (attachments)" 一节找到了具体机制：

```python
session.run(content=prompt, attachments=[
    {"type": "image/jpeg", "data": "<base64>", "filename": "receipt.jpg"}
])
```

文档原话确认 **"The same field works on the plugin path: `session.run(content, attachments=[...])` in the Python `executa_sdk`"**——Tool（不只是 iframe App）一样能用。规则：
- 图片格式 jpeg/png/gif/webp/bmp/svg+xml，单次最多 6 张，单张 ≤20MB
- `data`（base64，本地文件走这个）或 `url`（公网 HTTPS，有 SSRF 防护）二选一
- 模型必须 vision-capable，不支持直接报 `APP_MODEL_NOT_VISION_CAPABLE`（无静默降级），要用 `modelPreferences` 指定 vision 模型（如 `{hints:[{name:"gemini"}]}`）
- 图片只在当次 run 可见，不进历史记录

**结论更新**：`wefinance-ocr` 不用自带 `OPENAI_API_KEY` 了，改用 Agent Session（`host_capabilities: ["llm.sample", "llm.agent.auto"]`）+ `attachments` 传账单图片。三个 Tool 现在全部可以用 Anna 的 host LLM，零自己的 API 成本，也不用担心 App Review 因为"自带 key"卡关。**教训**：厂商自己的人给的答案（"Session 支持图片"）当场没法验证具体机制就先记成待查项，而不是直接采信或直接推翻自己的旧结论——后来翻到协议文档白纸黑字才算真正验证过。

chat 和 recommendation 两个纯文本服务切到 Sampling 的好处：不占用自己的 API 额度/成本，且 `responseFormat: json_schema` 是 provider 强制约束解码，比现在 `temperature=0.0` + 手动 prompt 约束 JSON 格式更可靠。

### 已查清楚：Agent Session 协议细节（2026-08-09，直接读 staging.anna.partners 的 executa-agent.md + llm-and-agent.md 验证，非猜测）

写 `wefinance-ocr` 时先按"跟 `sampling/createMessage` 同款命名风格类推"写了一版（`agent/session.close`、`kind="fixed"`、`session_id`、单文本响应），写完之后逛 Developer Forum 看到一篇 `agent.session` 相关的已解决帖子，顺手去翻了权威协议文档，发现好几处类推错了：

- Reverse-RPC 方法名是 `agent/session.create` / `agent/session.run` / `agent/session.cancel` / `agent/session.delete`（**不是** `.close`）
- `session.create` 用 `kind="agent"` + `agent_submode="auto"`，**不是** `kind="fixed"`——`fixed` 是"绑定到某一个已注册的其他 Executa Tool（靠 `fixed_client_id`）单次调用"，不适用于"就是想让模型看一眼图片回答"这种场景；`kind="agent"` + `submode="auto"` 才是文档里给纯图片理解场景的示例写法
  - 更正（2026-09-29）：现行的 `reference-executa-agent-sessions.json` 里 `session_create` 的签名只有 `agent_submode` / `fixed_client_id` / `label` / `quota_caps` / `ttl_seconds`，已经没有 `kind` 参数；Bill Scanner 不传 `kind`，在 0.2.15 上实测扫描正常
- 创建响应里会话标识字段叫 `app_session_uuid`，不是 `session_id`
- `session.run` 是 v2 的"缓冲式流"：响应结构是 `{run_id, stream_id, frames: [...], final}`，答案文本在 `event=="final"` 的那个 frame 里，不是单个文本字段
- `modelPreferences`（用来强制 vision-capable 模型，避免 `APP_MODEL_NOT_VISION_CAPABLE`）是 `session.run` 的**逐次**参数，不是建会话时传一次

已按这份权威文档改完 `plugin.py` + `test_local.py`，本地模拟测试全部通过。**还剩一个没法在本地验证的假设**：`agent_submode="auto"` 会不会让模型尝试调用工具而不是直接回答——这个 Tool 没有申请任何跨 Tool 的 `agent.tools` 授权，理论上模型没有可调用的工具，但这一点要等 Dev Access 批下来、真实连上 host 才能证实。

用户上传的账单图片怎么从 Anna 聊天界面传到 Tool 手上（`attachments.data` 要 base64，但这段 base64 从哪个字段进到 `invoke.arguments` 里，还是走 `schema:1` 聊天界面自带的文件上传）——这个还没查，同样要等真实连上 host 才能确认。

## 差异化 & PMF 调研（2026-08-08，外部市场调研 + Anna 生态实测）

### 外部市场：现有理财 App 的真实痛点（有来源，非猜测）

**竞品格局**：Copilot Money（$13/月）、Monarch Money（$99.99/年）、Cleo AI、Rocket Money、Expensify（个人版 $4.99/月）——**几乎所有主流玩家的记账方式都是强制银行卡关联（Plaid）**，账单/小票 OCR 顶多是辅助功能，不是核心工作流。

**三个有真实用户抱怨支撑的缺口**（来源见文末，均为 2026 年数据）：
1. **OCR 摩擦**：现有小票扫描"角度不对、光线不好就要手动改"，没人做到"可靠到能替代手输"——这正是 WeFinance 的核心技术（GPT-4o Vision 一步到位）理论上能打的点，但 Expensify/Finny 已经占了"个人小票 OCR"这个位置，纯拼 OCR 精度不够
2. **强制银行卡关联的隐私/覆盖率问题**：Plaid 覆盖率不是 100%，现金收入、非美国银行账户、不想授权第三方读取银行数据的用户，现有 App 基本用不了
3. **有仪表盘没有真建议**：市面上"分类记账"和"给建议"是两件事，能自动分类的（Copilot）不给投资建议，给投资建议的（Richify 等）用的是标准 Markowitz 优化，不是"针对你的真实交易数据可解释"——WeFinance 现有的"可解释推荐 + 推理链"理论上填这个缝，但没做过真实用户验证

**2026 年 AI Agent 理财赛道的真实资金流向**：Mine（$14M）、Jelou（$10M）、Alpaca（$135M）、Taktile（$110M，高盛领投）——**资金都在"执行具体金融操作的 agent"**（催退款、砍账单、再平衡、放贷决策），不是"AI 聊天理财顾问"这个品类。WeFinance 现在的定位（顾问层，不是执行层）不在这波融资热点里，这是个诚实的劣势，不是加分项。

### 最有证据支撑的差异化角度：双语 / 国际学生场景

三个角度里证据强度最高、但执行风险也最高的一个：
- **真实缺口**：WeChat Pay/支付宝 2026 年外国人交易量同比涨 80%，但**没有任何主流个人理财 App 能同时处理中英双语 + 多币种（CNY/USD/EUR）+ 支付截图**——留学生/华人群体这个场景是空的
- **WeFinance 现有优势**：i18n 系统本来就是 zh_CN/en_US 双语架构，不是要新建，是已经具备的基础设施
- **真实风险**：微信支付/支付宝官方 API 接入涉及国内企业主体注册，监管门槛高；这个细分群体价格敏感、获客难；如果微信支付/支付宝自己做个人理财层，这个缺口随时可能被巨头填掉

**诚实的结论（调研 agent 原话）**："Receipt-first + 隐私替代方案 + 可解释建议"这个组合和 WeFinance 现有技术能力匹配度最高，**但市场拉力没有验证过**——需要真去问 50 个潜在用户，愿不愿意拍照传账单而不是直接授权银行卡，调研查不出这个答案，只能真做用户访谈。双语/国际学生角度证据最强，但技术+监管执行难度也最高，适合当**验证完核心产品后的第二阶段定位**，不是现在就all-in的方向。

### 来源
Finny Blog（2026 年多篇：AI 记账 App 评测、多币种记账、隐私对比）、Monarch Money 隐私评测、Financial Panther、Crunchbase 2026 H1 fintech 融资报告、FinTech Futures 2026-07 融资月报、realchinatrip 微信支付宝外国人指南（2026）、bill.com/Expensify 小票扫描 App 评测

### 最小可行迁移路径（对应 Phase 0-1）
1. ✅ **`wefinance-chat` 已写完并本地验证通过**——`ask_advisor` 工具，走 Anna Sampling（`host_capabilities: ["llm.sample"]`），不用自己的 OPENAI_API_KEY
2. ✅ **`wefinance-recommend` 已写完并本地验证通过**——`generate_recommendations` 工具，移植了 `services/recommendation_service.py` 的 `analyze_transactions`（纯 Python 重写不依赖 pandas）+ prompt 结构，用 Sampling 的 `responseFormat: json_schema` 替代手写 JSON 约束
3. ✅ **`wefinance-ocr` 已写完并本地验证通过**——`extract_transactions` 工具，移植了 `services/vision_ocr_service.py` 的"先数后提取"prompt + 健壮 JSON 解析 + 字段容错，改用 Agent Sessions（`kind="agent"` + `agent_submode="auto"`）+ `attachments` 传图
4. ✅ **三个 Tool 都跑通，已包成 `schema:1` App manifest**
5. 有余力再考虑 `schema:2` 自定义 UI（图表、账单可视化这些强交互需求原生 chat 界面接不住的部分）

**2026-08-09 补充一轮：对着官方文档 + 真实 GitHub 示例代码逐项核对，发现并修完了一批之前凭类比猜错的协议/打包细节**（见下方"Ship 前核对"整节），当前状态和上面 1-4 条写的时间点相比有实质性变化，以那节为准。

### Setup 进度更新（2026-08-09）
- ✅ 回复了 Kate 的邮件：同步了注册/Discord/Luma/Dev Access 表单进度，追问了"Sampling 不支持图片输入，OCR 步骤自带 API key 会不会被 App Review 卡"这个问题
- ⬜ `/developer` 目前仍 403（Dev Access 还没批下来，官方说 24 小时内生效，继续等）
- 当前 Anna 账号是 Free plan，1,000/月配额，剩 977.936——表单承诺的"temporary Pro benefits"要等批下来才会到账，现在还没有

### Ship 前核对：跑了一轮 7 路并行文档调研 + 亲自查证，修完了一批协议/打包细节（2026-08-09）

**背景**：`wefinance-ocr` 写完之后，让一个 workflow 并行读了 tool 构建、打包分发、Sampling 协议、App manifest schema、App bundling/发布、官方 local-dev/测试工具链、参考文档 + 真实 GitHub 示例代码这 7 类文档（staging.anna.partners），产出 122 条 finding + 一份综合报告。**综合报告本身有一条"blocking"级别的结论是错的**，靠亲自回查权威文档才发现——记录下来，因为这正是"转述子 agent 结论前要抽验"的活例子。

**目录结构 + 打包文件（综合报告判断正确，已照办）**：
- `anna-app dev` / `executa` 自动发现只扫 `<manifest目录>/executas/<name>/`，原来的扁平结构（`anna_app/wefinance-chat/` 直接和 manifest 平级）会被静默跳过。已重构成：
  ```
  anna_app/
    manifest.json          # 改名自 app_manifest.json + 改对 schema
    app.json                # 新增，Listing 元数据（name/slug/category/tagline/pricing_model）
    executas/
      wefinance-chat/{wefinance_chat.py, test_local.py, executa.json, pyproject.toml}
      wefinance-recommend/{...}
      wefinance-ocr/{...}
  ```
- `manifest.json` 原来塞了 `name/display_name/version/description/author` 五个字段——**这份 manifest 是 Pydantic `extra="forbid"` 解析的，这五个字段根本不在允许列表里，整份文件会直接校验失败**（亲自读 `app-manifest.md` 核实，非转述）。已删掉，`name/display_name/description` 挪去新建的 `app.json`（对应 Listing 表单），`version` 不属于 manifest 字段、要在建版本时单独传 SemVer 参数。`required_executas` 也从裸字符串数组改成 `{tool_id: string}` 对象数组，值先填 `tool-dev-<slug>` 占位（真实值要等每个 Executa 在 `/executa` 铸造后拿到手，和各自 `executa.json` 的 `tool_id` 保持一致）
- 每个 Tool 新增 `executa.json`（打包身份文件，字段对着真实示例仓库 `whtcjdtc2007/anna-executa-examples` 的 `executa-agent-demo/executa.json` 抄的：`slug/name/version/executa_type/description/tool_id/type`）+ `pyproject.toml`（`uv run` 自动发现要用；不用 requirements.txt，那不是真实约定）。三个 Tool 都是纯 stdlib 零依赖，`pyproject.toml` 写了 `[project.scripts]` 入口指到各自模块的 `main()`
- `plugin.py` 改名成模块名（`wefinance_chat.py` / `wefinance_recommend.py` / `wefinance_ocr.py`），匹配 `pyproject.toml` 的 `[project.scripts]` 入口约定

**协议层修复（同样照办，来自亲自读 `executa-lifecycle.md`/`executa-sampling.md`/`executa-intro.md` + 真实示例代码交叉验证）**：
- 三个 Tool 的 `_reader()` 后台线程原来假设每行都是 dict，一行非对象的合法 JSON（如裸数组）会在线程里抛 `AttributeError` 悄悄杀死线程，主线程卡死在空队列上，症状和 pitfall #1（进程提前退出）一样但根因不同——已加 `isinstance(msg, dict)` 判断 + `try/except` 兜底
- JSON 解析失败原来只打日志，没按文档回一个 `-32700` 错误帧——已补上
- 加了 `shutdown` method handler（返回 `{"ok": true}`）——文档 + 真实示例都有，原来漏了
- `health` 响应原来只有 `{"status":"ready"}`，`executa-lifecycle.md` 的示例是 `{"status":"ready","message":"","details":{}}`——已补全（`message`/`details` 空值即可，文档没说必填但补上更贴合官方 shape）
- Sampling/Agent 内部等待超时原来是 90s，`executa-lifecycle.md` + `executa-intro.md` 都写 `invoke` 默认预算 60s（per-tool overridable）——chat/recommend 的纯文本 sampling 降到 50s；`wefinance-ocr` 的 `session.run` 保留 90s 没动，因为真实参考插件自己内部等了 180s，两份"权威"文档在这点上互相矛盾，没法在没有真实 host 的情况下彻底定论，先记下这个冲突
- 加了 `initialize()` 里读取 host 提议的 `protocolVersion`，没协商上 v2 就不再尝试 sampling/agent（原来无条件假设总是 v2，真遇到 v1 host 会一直卡到超时才报错）
- Sampling/Agent 报错原来是把整个 error dict 原样 `str()` 甩给用户，现在按 `executa-sampling.md`/`executa-agent.md` 的错误码表映射成人话（如 `SAMPLING_NOT_GRANTED` → "你还没在 Anna Admin 里给这个 Tool 开 sampling 权限"）
- `wefinance-recommend`：`onUnsupported: "json_object"` 意味着模型不支持严格 schema 时会静默降级，原来没检查 `_meta.responseFormat.downgraded`，降级后如果模型没吐出 `recommendations` 字段会被 `.get("recommendations", [])` 悄悄吞成空列表、对外显示"success"——现在检测到降级且缺字段会显式报错
- `wefinance-ocr`：`session.run` 的 frame 扫描原来只认 `event=="final"`，真实参考插件的文档明确还有一种"哨兵型" `event=="complete"`（没有 text 字段，答案要从累积的 `delta`/`token`/`message` 帧里拼）——原实现遇到这种收尾方式会静默返回空结果，现在两种都处理了

**推翻综合报告的一条"blocking"结论**：报告说三个 Tool 的 `initialize()` 响应把协商能力放错了 key（应该是 `client_capabilities` 不是 `capabilities`），证据是真实示例插件 `executa_agent_demo.py` 确实这么写。但亲自去读 `executa-lifecycle.md`（v2 handshake 的**权威页**，`executa-sampling.md` 和 `executa-agent.md` 都指向它作为协议细节的最终来源）发现它的官方 worked example 用的是 `capabilities: {sampling: {}}`——和我们原来的代码一致。再去读 `executa-sampling.md` 自己那段可运行的"Minimal Python example"，也是 `capabilities`，不是 `client_capabilities`。**两个独立、互相印证、且被其他文档明确指向的权威来源 vs 一个孤立的示例脚本**，判定示例脚本是异常值（可能是那个 demo 为配合更新的 Agent Sessions 功能而引入的实验性/未同步写法），**没有改这一处**，保持原来的 `capabilities` key 不动。这是"reviewer/workflow 的发现，采纳和驳回都要独立验证"的实例——如果照单全收会把三个 Tool 的协议改错，且不会有任何本地测试能发现，因为 `test_local.py` 是我们自己既当 Tool 又当 host 模拟的，两边会自洽地错在一起

**已解决：三个 Tool 全部在 `/executa` 铸造成功（2026-08-09，Chrome 实操，Free plan 账号）**：

Free plan 不卡 Tool 创建（`verified-developer.md` 说得对，只卡 `/developer/apps/*`）。三个 Tool 逐个走"Mint tool_id → 填 Description/Category/Icon → 勾 Supports Executa Protocol → JSON Editor 里注入插件里那份 `MANIFEST` dict → 每步用 `javascript_tool` 读 textarea/`input.value` 回读核对 `JSON.parse` 完全相等 → Create → 不信 toast，点 Refresh 看 My Tools 卡片真的持久化了 → 再截图确认" 的流程,真实铸造到的 `tool_id`：

| Tool (slug) | 真实 tool_id |
|---|---|
| wefinance-ocr | `tool-calderbuild-wefinance-bill-scanner-swymwa2w` |
| wefinance-chat | `tool-calderbuild-wefinance-advisor-chat-zm45qs9z` |
| wefinance-recommend | `tool-calderbuild-wefinance-investment-recommendations-r2q5jdey` |

`anna_app/manifest.json` 的 `required_executas` 和三份 `executa.json` 的 `tool_id` 已同步改成这三个真实值（`grep -rn "tool-dev-" anna_app/` 确认零残留占位符），三个 `test_local.py` 协议测试全部重跑通过（未受影响，改的只是打包元数据不是协议代码）。Visibility 目前是 `private — only you`（推荐的 dev-loop 起点，后续要在 Anna App 里挂载或上 Explore Hub 再切 `app_bundled`/`public`）。

中途踩了两个小坑（均已现场修正、有截图证据）：Icon 字段第一次点击没落地（emoji 输入法/焦点时序问题，`cmd+a` 选中了空内容），二次点击后甚至叠加成 `💬💬`（重复输入），最终改用"点击 → cmd+a → Delete → 输入一次" 并用 `javascript_tool` 读回 `input.value` 精确核对单字符后才继续。Manifest JSON Editor 直接打字第一次把 wefinance-chat 的 `display_name` 打成了 "WeFinance Advisor Chat"（和插件代码里真实的 `MANIFEST["display_name"] = "WeFinance Advisor"` 不一致），后两个 Tool 改用原生 setter + `dispatchEvent('input')` 直接注入 `JSON.stringify(manifest, null, 2)` 字符串,一次到位且用 `JSON.stringify(JSON.parse(ta.value)) === JSON.stringify(manifest)` 做了程序化相等断言,不再靠肉眼比对。

**关键发现：铸造成功 ≠ 能真实执行（2026-08-09，Chrome 实机测试，非推测）**

三个 Tool 铸造后，在真实 Anna 主聊天界面（`anna.partners/dashboard`，新开 Zen Mode 干净会话，排除了 Main Soul 里一段无关的旧历史干扰——那段历史是 Anna 自己的通用 agent 很早之前尝试用她自己的 fs_*/exec_run 工具从零写 plugin.py 卡住超时的残留，和我们这次的手写代码无关，纯属误导）里 `@` 出 `WeFinance Advisor Chat` 并 pin 上，发送真实问题（"I spent 240 CNY on dining and 30 CNY on transit last month. Where did my money go?"），Anna 的真实回复：

> I can see you've @mentioned the WeFinance Advisor Chat skill, and I have its documentation loaded. However, the actual execution tool (`ask_advisor`) isn't available in my current execution environment. This appears to be a configuration issue - the skill is documented but not properly connected to the execution layer.

**根因**：三个 Tool 创建时 `Distribution Type` 都留了 `None`——manifest/`describe()` 元数据被平台解析并用于文档/发现（所以 `@` 提及能找到、图标描述都对），但**没有任何字段告诉 Agent 去哪里取二进制/怎么起进程**，所以调用时无法真正 spawn 我们的 `wefinance_chat.py`。这和"铸造成功 + 卡片持久化"是两件事——已验证的只是"注册成功"，不是"可执行"。

亲自读 `executa-binary.md`（`staging.anna.partners/developers/tools/executa-binary.md`）确认了三条真实可选路径，都不是"改个字段"那么轻：
1. **`uv` 分发**——发布到 PyPI（公开包注册表），Agent 从那装。最贴合我们已有的零依赖 `pyproject.toml` + `[project.scripts]` 结构,但要占用一个公开包名、需要 PyPI 账号/token,且发布后基本不可撤回。
2. **`binary` 分发（PyInstaller）**——按 `darwin-arm64`/`linux-x86_64`/`windows-x86_64` 等平台各打一份二进制,压成 `.tar.gz`/`.zip`,挂到 GitHub Releases(仓库已有,天然合适),`binary_urls` 填对应 URL。工作量最大(要交叉编译或至少覆盖常见平台),但可逆(删 Release 即可撤)、不占公开包名。
3. **`local` 分发**——`Local Archive Path` 指向"Agent host"上的绝对路径,免注册表/免上传,但要求 Calder 本机装了 Anna 的本地 Agent 执行器(登录页 3 步 onboarding 的"Install Agent"),而目前没有证据证明这一步已完成(Settings 弹窗只有 Appearance/Language,没查到 Agent 连接状态入口)——真要走这条路,第一步是先确认 Agent 有没有装、装在哪台机器。

三条路径都有实质代价(公开发布 / 跨平台构建 / 依赖未确认的本地环境),不是"顺手就做"的收尾动作,**已就此向用户呈现选项等待决策,没有unilaterally 选一条动手**——尤其 PyPI 发布这类不可逆的对外发布动作,按规矩要明确许可才能做。

**结果：选了 GitHub Releases + PyInstaller 二进制分发路径（用户拍板"按你的推荐"，已执行到 CI 绿、release 未剪）**

1. 本地先把可逆的部分全做完再问权限：`pip install pyinstaller`,给三个工具各 `pyinstaller --onefile` 打包,写了 `/tmp/test_binary_*.py` 逐个验证冻结后的二进制和源码脚本协议行为完全一致(describe/initialize/invoke/health/shutdown 全过)。
2. 复刻官方参考仓库 `whtcjdtc2007/anna-executa-examples` 的 `build-release.yml` 模式,写了 `.github/workflows/build-executa-binaries.yml`(3 工具 × 2 平台矩阵)。**发现并修掉参考文档自己那份 CI 示例的一个真实 bug**:它的协议测试用 `echo ... | binary | assert` 这种裸 shell 管道,而我们的插件是刻意设计成"stdin EOF 后不退出"的长驻进程(和文档 pitfall #1 的要求一致),所以那种管道会在 binary 阻塞等第二行输入时**永久挂起**——本地实测复现了这个挂起(2 分钟 bash 超时才杀掉)。修法:改写成 `scripts/test_executa_binary.py`,用 `subprocess.Popen` + `finally: proc.terminate()` 显式收尾,不管协议走到哪一步都保证进程被杀。这条如果不是本地先复现就直接搬进 CI,大概率会在每次 CI 跑的时候悄悄挂起浪费执行分钟数,而不会报错——是"照抄参考实现"最容易踩的那类坑。
3. `git add -n` 核对只有 15 个真实源文件会被 commit(`dist/`、`.spec`、二进制全部命中 `.gitignore` 里已有的 `dist/`/`build/` 规则,没有泄漏),commit + push 前问了用户"推到公开仓库这一步要不要做、做到哪一步"(push-only / push+dry-run / push+剪 release 三选项),用户选**"push + workflow_dispatch 空跑验证,不剪 release"**。
4. 第一次 `workflow_dispatch`(3 平台矩阵,含 `macos-13` 跑 darwin-x86_64)跑了 31 分钟仍有 3 个 job 卡在 `queued`、`runner_name` 一直是空——查 `actions/runner-images` 官方 README 确认 **`macos-13` 已经从可用镜像列表里彻底消失**(不是"慢",是"已经没有这个池子了"),连当时用的 `macos-14` 也已被标 deprecated(还能跑,但排期内会下线)。**这是先假设"CI 只是排队慢"、后来才用官方文档验证"这个 runner 池根本不存在了"的一次负向断言纠偏**——如果没去查,可能会一直干等。修法:砍掉 darwin-x86_64(2026 年 Intel Mac 已经没有可靠的免费 hosted runner 标签),`darwin-arm64` 换成 `macos-latest`(当前指向 macOS 26 Arm64,非 deprecated)。
5. 第二次 `workflow_dispatch`(2 平台 × 3 工具 = 6 job)全绿,总耗时约 1 分钟,6 个 artifact(`<tool>-<platform>`)全部产出。**这一步只验证了"CI 能造出二进制",还没验证"Anna 平台能真正下载并跑起来"**——`binary_urls` 还没接到 Executa Hub 的 Distribution 表单里,`extract → spawn → 真实调用` 这条链路仍未打通,是下一步。

**还是没法在本地验证的**（等 Dev Access，或需要 Anna App 层面的真实调用）：
- `session.run` 60s vs 180s 超时冲突，到底哪个是真实生效值
- `agent_submode="auto"` 在零跨 Tool 授权的情况下会不会意外尝试调用工具而不是直接回答
- Executa 发布本身**不需要** Verified Developer 状态（只需要有效付费订阅），只有 App 级别打包发布才卡在 Dev Access 上——如果账号有付费订阅，理论上三个 Executa 现在就能各自独立发布拿到真实 `tool_id`，不用等 `/developer` 解封
- 采不采用官方 `executa_sdk`（有安装门槛：目前只能从示例仓库相对路径装，没发到 PyPI）——现状是继续手写零依赖协议层，换来的是不需要额外依赖，代价是几个协议细节（这次修的那些）本来 SDK 会自动处理对
- `anna-executa-test` 官方测试工具（`pip install anna-executa-test`，号称和生产分发逻辑同源）没有采用，`test_local.py` 仍是自己模拟 host 角色——这个局限性无法消除，只能靠真实 host 测试补齐

**收尾：Distribution 全接完 + 真实调用测试，暴露第二道独立的门（2026-08-09 深夜，用户拍板"全部收尾"/"弄好"）**

1. 三个工具的 Edit Tool 表单里都填完了 `Distribution Type: Binary`，两个平台（darwin-arm64 / linux-x86_64）各自的 URL、SHA-256、Size、Entrypoint 全部用原生 setter 注入 + JS 回读逐字核对（不信 `computer.type`，这条是本 session 反复验证过的教训）。三张卡片保存后刷新，`My Tools` 页面三张卡全部显示 `BINARY` 徽章，和之前两个已完成的一致。
2. 回到 Anna 真实聊天界面，新开一个 **Zen Mode 全新会话**（排除 Main Soul 里的旧历史干扰，复刻最初发现问题时用的同一套测试方法），`@` 提及 `WeFinance Advisor Chat`，发真实问题（"I spent 45 CNY at Starbucks yesterday on coffee. Any quick budgeting advice?"）。
3. **好消息**：这次 Anna 真的调用了 `tool_calderbuild_wefinance_advisor_chat_zm45qs9z__ask_advisor`（工具调用面板可见，"✅Done"），证明 Distribution 接线确实解决了最初那个"execution tool isn't available in my current execution environment"的问题——铸造 + 分发链路完整打通。
4. **坏消息**：调用本身返回了一个新的、独立的错误：
   ```json
   {"success": false, "error": "You haven't enabled sampling for WeFinance Advisor yet -- turn it on in Anna Admin.", "command_id": "024fc837-e58b-4b33-8c33-970249610772"}
   ```
   Anna 重试了一次（同样报错），随后优雅降级成自己现编的通用理财建议，而不是走我们工具里 `ask_advisor` 真正的 reverse-RPC sampling 逻辑。这条错误信息本身很明确——不是 bug，是一道单独的权限闸。
5. **查证据链**：这道"sampling grant"是 `wefinance-chat` / `wefinance-recommend` 两个工具（用 Anna Sampling、不带自己的 OpenAI key）架构设计里天然依赖的一环——manifest 里 `host_capabilities: ["llm.sample"]` 声明了这个反向 RPC 能力，但**声明能力 ≠ 用户已授权使用它**，这是两层独立的东西（前者是"平台知道你想用什么"，后者是"用户点头让你用"）。`wefinance-ocr`（走 Agent Sessions + 图片附件，不需要 sampling）不受影响。
6. **找"Anna Admin"这个开关花了大量尝试仍未找到 UI 位置**——按顺序查过：Executa Hub 的 Edit Tool 弹窗（滚到底，只有 Capabilities 文本框和 Manifest 编辑器，没有 sampling 相关开关）；`My Tools` 卡片上的 "Install" 按钮（点击后抓包发现它实际调的是 `POST /api/v1/agents/{agent_id}/plugins/reinstall`，是往 Cloud Agent 上重装二进制，和权限授予无关）；`Authorizations` 页（那是接 Google/Twitter/GitHub/OpenAI 这类外部服务账号的 OAuth 页，无关）；`Agents` 页（Cloud Agent 的基础设施管理——Suspend/Remove Default/Destroy，Fly.io 机器信息，无关）；`Installed Apps → Permissions`（找到了这个模式的**同类实现**——"Grant everything this app and its bundled tools need — in one place. Toggles only appear for capabilities that are actually declared"，证明平台确实有这套 per-capability 授权 UI 范式，但这个入口挂在 **App**（`anna_app/manifest.json` 打包发布的整体）粒度上，我们的三个 Executa 目前是独立 Tool 身份存在，没有打包成 App，所以这个入口对我们不适用）；`Advanced → LLM` 设置页（模型选择/BYOK/递归上限/各类任务的默认模型，翻到底也没有 per-Executa 的 sampling 授权区块）。
7. **查官方文档补证**：`developers/reference.md` 的能力目录确认存在专门页面 `developers/reference/executa-sampling.md`，抓取后找到权威原句：
   > "The user enables sampling for this Executa in Anna Admin (`UserExecuta.custom_config.sampling_grant.enabled = true`, with `maxCalls` and `maxTokensTotal` caps)."
   `llms-full.txt`（全量文档语料）里的另一处措辞是 "The end user enabled sampling for this Executa in their Anna Admin panel."——**两处都只描述了这个字段/行为存在，都没有给出对应的具体 UI 路径（菜单名/按钮 label/设置页 URL）**。这和 App 发布那次撞到的"Dev Access 403"是同一个模式：文档承认某个更高权限层的存在，但 UI 侧尚未（或还没对当前账号等级）暴露完整入口。
8. **结论/待办（更新，问题已解）**：三个工具的 Distribution（可执行性）已经 100% 打通并验证；`wefinance-ocr` 应该已经完全可用（不依赖 sampling）；`wefinance-chat` / `wefinance-recommend` 卡在这道新发现的 "Anna Admin sampling grant" 权限闸上，UI 入口未定位到——需要用户确认这是否是当前账号层级/Founding Builder 阶段还没开放的功能，或者是否有别的已知入口。

**"Anna Admin" 入口找到了：`Executa Hub → Learned` tab（2026-08-09 深夜，最终定位）**

翻遍 Edit Tool 弹窗、Install 按钮、Authorizations、Agents、Installed Apps→Permissions、Advanced→LLM 之后，真正的入口其实一直在眼前：**`Executa Hub` 页面顶部有四个 tab（Explore / My Tools / My Skills / **Learned**），"Learned"（当时显示 14 项）才是"已装载到当前 Agent 的能力清单 + 每项的权限授权状态"**。之前只点过 Explore 和 My Tools，没点过 Learned。

这个盲点是怎么补上的：让 `wefinance-ocr`（不依赖 sampling，只依赖 Agent Session）单独走一次真实调用测试（用 `file_upload` 工具把 `assets/sample_bills/bill_dining.png` 直接注入聊天框的隐藏 `<input type=file>`，绕开了原生文件选择器不可见的问题），Anna 的报错原句比第一次更具体：

> "Agent Sessions aren't enabled for WeFinance Bill Scanner yet -- turn it on in **Anna Admin**." ... "please go to **Anna Admin → Skills → WeFinance Bill Scanner** and toggle Agent Sessions on."

这条错误信息第一次给出了具体路径名"Skills"，对应上了 Executa Hub 里那个没点过的 "Learned" tab（同一批已装载能力,不管注册身份是 Tool 还是 Skill,统一列在这里)。点开某个工具卡片的 "Permissions: 0/N" 徽章(橙色/警示色),弹出的正是文档里描述的那个 `UserExecuta.custom_config.sampling_grant` 授权对话框:

```
Permissions — WeFinance Bill Scanner
Authorize host capabilities for this Executa

☑ LLM Sampling          [toggle]
  Allow this Executa to call the host LLM via sampling/createMessage.
  Max calls per invoke: 8 (hard cap) / Max tokens per invoke: 32000 (hard cap)

☑ Agent Session — auto submode   [toggle]
  Allow this Executa to spawn an autonomous agent session that runs in the host worker.

📊 LLM Quota (shared)
  Max tokens per call: 4096 (default) / Max calls per day: 200 (default)
```

三个工具分别开的权限数对应各自 manifest 的 `host_capabilities` 声明:`wefinance-ocr` 2 项(LLM Sampling + Agent Session,对应 `llm.sample` + `llm.agent.auto`),`wefinance-chat` / `wefinance-recommend` 各 1 项(只有 LLM Sampling)。三个都点开、勾选、Save,卡片上的徽章从橙色 "Permissions: 0/N" 变绿色 "Permissions: N/N"。

**回归测试,两条链路都实测确认修复生效:**

- `wefinance-ocr`(不依赖 sampling,新开 Zen Mode 测试)：授权前就已经通过"读图直接回答"优雅降级出了正确结果(4 笔真实交易,金额分类全对);这次单独验证的价值是确认了"Agent Sessions"这第二种 host_capability 具体错在哪、路径怎么找到。
- `wefinance-chat`(依赖 sampling,新开 Zen Mode 测试,授权后重新发送同一个问题)：这次工具调用面板返回 `{"success": true, "data": {"success": true, "data": {"advice": ""}, "duration_ms": 8764}, "command_id": "..."}` —— **不再报 "You haven't enabled sampling" 错误**,`duration_ms: 8764` 证明真的走完了一次 sampling 往返(不是又一次静默失败)。**权限问题已彻底解决**。

**副作用发现:一个独立的、更小的代码 bug**——`advice` 字段返回的是空字符串 `""`,不是真实的建议文本。查了 `wefinance_chat.py::sample()`(第 162-192 行):函数按 `resp["result"]["content"]["text"]` 取值,逻辑本身看起来没问题(不是嵌套结构假设错误那类),空值大概率是这次 sampling 调用本身模型返回了空补全(具体原因需要更多样本复测才能确诊,可能是 `maxTokens=400` 加某个 system prompt 组合导致模型直接吐空,也可能是 host 侧个别请求的偶发行为)。**这个 bug 不影响本次收尾的范围**(Distribution + 权限授权都已验证打通),是否深入排查留给用户决定——聊天界面里 Anna 自己的外层模型用读到的空 advice 兜底生成了一段通用建议,所以用户体感上"看起来正常",但我们自己 `ask_advisor` 里精心设计的、基于真实交易上下文的建议链路目前没有真正把内容传出来。

**最终状态**:三个工具 Distribution(可执行)+ Permissions(可调用 sampling/agent session)全部打通,`wefinance-ocr` 端到端验证通过(真实图片→真实结构化交易),`wefinance-chat` 权限链路验证通过(不再报权限错,但 `advice` 字段本身有个独立的空值 bug 待查)。`wefinance-recommend` 权限已同样开启但未单独实测调用(和 `wefinance-chat` 走同一条 sampling 代码路径,大概率同样的现象)。