# WeFinance Copilot - Sprint 3 开发任务

## 项目上下文

**项目名称**: WeFinance Copilot - AI驱动的智能财务助理
**竞赛**: 2025深圳国际金融科技大赛（AI赛道）
**截止日期**: 2025年11月16日 24:00
**当前日期**: 2025年11月6日
**剩余时间**: 10天

## 已完成工作

### Sprint 1 ✅ (Day 1-3)
- ✅ 项目结构和conda环境配置
- ✅ PaddleOCR + GPT-4o混合OCR架构实现
- ✅ 账单上传页面 (`pages/bill_upload.py`)
- ✅ 数据分析模块 (`modules/analysis.py`)
  - 分类统计、支出趋势、异常检测(Z-score算法)
  - 生成洞察文本
- ✅ 消费分析页面 (`pages/spending_insights.py`)
  - Plotly图表展示
  - 异常检测表格
- ✅ 单元测试 (`tests/test_ocr_service.py`, `tests/test_structuring_service.py`)

### Sprint 2 ✅ (Day 4-7)
- ✅ 对话管理器 (`modules/chat_manager.py`)
  - 预算查询、消费分析、术语解释、理财建议
  - GPT-4o集成
- ✅ 财务顾问聊天页面 (`pages/advisor_chat.py`)
  - 预算控制侧边栏
  - 示例问题按钮
- ✅ LangChain Agent (`services/langchain_agent.py` - 可选)
  - 工具定义 (query_budget, query_spending, query_category)
  - ConversationBufferMemory
- ✅ 推荐服务 (`services/recommendation_service.py`)
  - 风险评估问卷(3道问题)
  - 资产配置规则
  - **XAI解释生成** (竞赛核心亮点)
- ✅ 投资推荐页面 (`pages/investment_recs.py`)
  - 4步流程：风险评估 → 投资目标 → 配置展示 → XAI解释

## Sprint 3 开发任务 (Day 8-10)

### Epic 3.1: 主动式异常检测优化 (F4加分项)

#### 任务1: 异常检测UI增强
**文件**: `pages/spending_insights.py`, `app.py`
**需求**:
1. 在首页(`app.py`)顶部添加异常警告卡片
   - 使用 `st.error()` 或 `st.warning()` 高亮显示
   - 展示最新3条异常（时间、商户、金额、原因）
   - 添加"确认本人消费"和"标记欺诈"按钮
2. 在`spending_insights.py`中添加异常历史查看
   - 侧边栏显示所有异常记录
   - 标记已确认/已拒绝的异常
3. 用户反馈闭环
   - 用户确认后，将异常移出警告列表
   - 标记欺诈后，高亮该交易（红色）
   - 在`st.session_state`中记录用户反馈

**验收标准**:
- 异常卡片正确展示且交互流畅
- 用户操作实时反馈
- 异常历史功能完整

#### 任务2: 异常检测算法优化
**文件**: `modules/analysis.py`
**需求**:
1. 白名单机制
   - 在侧边栏添加"信任商户管理"
   - 支持用户添加/删除白名单商户
   - 白名单商户不触发异常检测
2. 阈值调优
   - 测试不同Z-score阈值(1.5/2.0/2.5)
   - 根据数据分布自动调整阈值
3. 新用户降级处理
   - 数据量<10笔时，降低异常检测灵敏度
   - 提示"数据积累中，检测准确度提升需要时间"

**验收标准**:
- 异常检测准确率≥85%
- 误报率<10%
- 白名单功能正常

### Epic 3.2: 集成测试与性能优化

#### 任务3: 端到端集成测试
**文件**: 新建 `tests/test_integration.py`
**需求**:
1. 设计5个完整用户流程测试用例
   - 场景1: 上传账单 → 查看分析 → 对话查询 → 查看建议
   - 场景2: 批量上传 → 异常检测 → 用户确认
   - 场景3: 多轮对话 → 清空历史 → 重新问答
   - 场景4: 风险问卷 → 推荐生成 → XAI解释查看
   - 场景5: 异常触发 → 用户反馈 → 历史查看
2. 使用Mock数据执行测试（避免真实API调用）
3. 记录测试结果和发现的Bug

**验收标准**:
- 5个测试用例通过率≥80%
- 发现的P0/P1 Bug全部修复
- 测试报告记录完整

#### 任务4: 性能优化
**文件**: 所有页面文件
**需求**:
1. 添加缓存优化
   - 在`spending_insights.py`中添加`@st.cache_data`缓存数据处理
   - 在`advisor_chat.py`中缓存常见查询回答
   - 在`investment_recs.py`中缓存推荐结果
2. 图表懒加载
   - 图表默认折叠，点击"展开"按钮才渲染
3. 优化数据处理
   - 使用Pandas矢量化操作替代循环
   - 减少不必要的数据转换

**验收标准**:
- 页面加载时间≤2秒
- 重复操作响应时间减少≥50%
- 缓存命中率≥40%

#### 任务5: 错误处理完善
**文件**: 所有服务文件
**需求**:
1. 全局异常捕获
   - 在`app.py`中添加全局异常处理
   - 所有API调用添加try-except
2. 用户友好的错误提示
   - 网络错误 → "网络连接失败，请检查网络设置"
   - API限流 → "服务繁忙，请稍后再试"
   - OCR失败 → "图片识别失败，建议手动输入"
3. 降级方案
   - OCR失败 → 提供手动输入表单
   - LLM超时 → 返回规则生成的简单回答

**验收标准**:
- 无Python堆栈报错暴露给用户
- 所有异常都有友好提示
- 降级方案有效且用户无感知

### Epic 3.3: Demo演示优化

#### 任务6: UI美化与体验优化
**文件**: 所有页面文件, `.streamlit/config.toml`(新建)
**需求**:
1. 统一UI风格
   - 创建`.streamlit/config.toml`配置主题
   - 统一颜色方案（主色调：蓝色/绿色金融风格）
   - 统一按钮样式、卡片间距
2. 交互体验优化
   - 添加自定义loading动画文案（"正在识别账单..."）
   - 优化成功/失败提示（`st.success`/`st.error`带图标）
   - 首次使用添加操作引导（`st.info`提示框）
3. 响应式布局
   - 使用`st.columns()`优化页面布局
   - 关键指标使用metric卡片展示

**验收标准**:
- UI风格统一专业
- 交互流畅无卡顿
- 新用户能快速上手

#### 任务7: Demo数据准备
**文件**: `assets/sample_bills/`, `assets/mock_products.json`
**需求**:
1. 准备10张高质量示例账单
   - 覆盖7大类别（餐饮、交通、购物、医疗、娱乐、教育、其他）
   - 包含2张异常消费（深夜大额、同商户高频）
   - 确保OCR识别准确率≥95%
2. 准备对话示例脚本
   - 10个示例问题（覆盖4类意图）
   - 验证回答准确性
3. 优化Mock产品库
   - 扩展到20个理财产品
   - 覆盖所有风险等级

**验收标准**:
- 示例账单识别准确
- 对话示例回答合理
- 产品库数据完整

### Epic 3.4: 文档与竞赛材料

#### 任务8: README文档完善
**文件**: `README.md`(已存在)
**需求**:
1. 更新快速开始指南
   - 验证安装步骤准确性
   - 添加常见问题FAQ
2. 补充演示说明
   - 添加功能截图（5-8张）
   - 添加演示视频链接位置
3. 更新技术栈说明
   - 补充实际使用的版本号
   - 说明混合OCR架构优势

**验收标准**:
- 按README能成功运行项目
- 非技术人员能看懂核心功能
- FAQ覆盖常见问题

#### 任务9: 代码质量审查
**文件**: 所有Python文件
**需求**:
1. 代码规范检查
   - 运行`black .`格式化所有代码
   - 运行`ruff check .`检查规范
   - 补充缺失的docstring
2. 中文注释审查
   - 关键业务逻辑添加中文注释
   - 复杂算法添加注释说明
3. 代码重构
   - 提取重复代码为工具函数
   - 简化>3层嵌套的逻辑
   - 优化数据结构

**验收标准**:
- 代码通过black和ruff检查
- 关键逻辑有中文注释
- 函数复杂度≤3层嵌套

## 技术约束

### 环境配置
```bash
# 已配置的环境
conda activate wefinance
python --version  # Python 3.10.x
```

### API配置 (.env文件)
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-debs5nl5QYdw7AwnXMxHSzxVu1e15KzJsgwHK9Khp25STqMe
OPENAI_BASE_URL=https://newapi.deepwisdom.ai/v1
OPENAI_MODEL=gpt-4o

PADDLE_OCR_USE_ANGLE_CLASS=True
PADDLE_OCR_LANG=ch
```

### 核心依赖
- Streamlit 1.28.0
- PaddleOCR 2.7.0
- OpenAI 1.3.0
- LangChain 0.1.0
- Pandas 2.0+
- Plotly 5.18+

## 质量标准

### 功能验收
- [ ] 异常检测功能正常（准确率≥85%）
- [ ] 所有功能集成测试通过（≥80%）
- [ ] UI美观统一
- [ ] 文档完整准确

### 性能验收
- [ ] 页面加载时间≤2秒
- [ ] OCR响应时间≤3秒
- [ ] 对话响应时间≤3秒
- [ ] 缓存命中率≥40%

### 代码质量
- [ ] 代码符合PEP8规范
- [ ] 关键逻辑有中文注释
- [ ] 无Python堆栈报错暴露
- [ ] 单元测试覆盖率≥70%

## 项目结构参考

```
WeFinance/
├── app.py                      # 主入口（需添加异常警告卡片）
├── pages/
│   ├── bill_upload.py         # ✅ 已完成
│   ├── spending_insights.py   # 需优化：异常历史、缓存
│   ├── advisor_chat.py        # ✅ 已完成（需添加缓存）
│   └── investment_recs.py     # ✅ 已完成（需添加缓存）
├── modules/
│   ├── analysis.py           # 需优化：白名单、阈值调优
│   └── chat_manager.py       # ✅ 已完成
├── services/
│   ├── ocr_service.py        # ✅ 已完成（需添加错误处理）
│   ├── structuring_service.py # ✅ 已完成
│   ├── recommendation_service.py # ✅ 已完成
│   └── langchain_agent.py    # ✅ 已完成（可选）
├── tests/
│   ├── test_ocr_service.py   # ✅ 已完成
│   ├── test_structuring_service.py # ✅ 已完成
│   └── test_integration.py   # 待创建
├── .streamlit/
│   └── config.toml           # 待创建（主题配置）
└── assets/
    ├── sample_bills/         # 待扩充（10张高质量账单）
    └── mock_products.json    # 待优化（20个产品）
```

## 优先级

**P0 (必须完成)**:
1. 任务3: 端到端集成测试
2. 任务5: 错误处理完善
3. 任务8: README文档完善
4. 任务9: 代码质量审查

**P1 (重要)**:
1. 任务1: 异常检测UI增强
2. 任务4: 性能优化
3. 任务6: UI美化
4. 任务7: Demo数据准备

**P2 (加分项)**:
1. 任务2: 异常检测算法优化

## 开发建议

1. **按优先级开发**: 先完成P0任务，确保核心功能稳定
2. **增量测试**: 每完成一个任务立即测试验证
3. **保持简洁**: 遵循Linus哲学，拒绝过度设计
4. **用户体验优先**: 所有决策以Demo演示效果为准
5. **错误处理优先**: 确保无崩溃、无堆栈暴露

## 竞赛评分标准提醒

- **产品实现完整性 (40%)**: F1+F2+F3必须100%完成
- **创新性 (30%)**: XAI解释是核心亮点，需重点演示
- **商业价值 (30%)**: 混合OCR架构(97%成本优化)是关键卖点

**预期得分**: 88/100 → 91/100 (完成Sprint 3后)

---

**开始开发!** 🚀
