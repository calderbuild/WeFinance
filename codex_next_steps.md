# WeFinance Copilot - Sprint 3 Next Steps

## Current Status

✅ **Epic 0 (i18n Framework) - COMPLETED**
- i18n module with caching
- 121 translation keys in zh_CN/en_US
- All 5 pages internationalized (110+ i18n calls)
- Language switcher in sidebar
- 15 tests passing

## Phase 2: Testing, Documentation & Code Quality (P0 Tasks)

### Priority Order
**P0 (Critical - Must Complete Today)**:
1. Task 3: End-to-End Integration Testing
2. Task 5: Error Handling Enhancement
3. Task 8: README Documentation (Bilingual)
4. Task 9: Code Quality Review

**P1 (Important - Complete Tomorrow)**:
1. Task 4: Performance Optimization
2. Task 6: UI Beautification
3. Task 7: Demo Data Preparation

### Task 3: End-to-End Integration Testing (P0)

**Objective**: Validate all user flows work correctly in both languages

**Files to Update**: `tests/test_integration.py`

**Requirements**:
1. Add 5 comprehensive E2E test scenarios (mock all API calls):
   ```python
   # Scenario 1: Full workflow
   def test_full_workflow_zh():
       """Upload bill → View analysis → Chat query → View recommendations (Chinese)"""
       # Test steps...

   def test_full_workflow_en():
       """Same workflow in English"""
       # Test steps...

   # Scenario 2: Anomaly feedback loop
   def test_anomaly_detection_feedback():
       """Upload bills with anomaly → User confirms/marks fraud → Verify state"""
       # Test steps...

   # Scenario 3: Language switching
   def test_language_switching():
       """Switch language mid-session → Verify all UI updates → No data loss"""
       # Test steps...

   # Scenario 4: Multi-turn chat
   def test_multi_turn_chat_memory():
       """Multi-turn conversation → Clear history → Verify memory reset"""
       # Test steps...

   # Scenario 5: Error handling
   def test_error_handling_graceful():
       """Trigger OCR error → Verify fallback → User continues workflow"""
       # Test steps...
   ```

2. Use pytest fixtures for mock data:
   ```python
   @pytest.fixture
   def mock_transactions():
       """Sample transaction data for testing"""
       return [...]

   @pytest.fixture
   def mock_llm_response(monkeypatch):
       """Mock OpenAI API responses"""
       def mock_call(*args, **kwargs):
           return MockResponse(...)
       monkeypatch.setattr("openai.ChatCompletion.create", mock_call)
   ```

3. Test coverage targets:
   - All pages render without errors (zh_CN + en_US)
   - Session state persists correctly across language switches
   - API failures handled gracefully with user-friendly messages
   - Anomaly feedback loop complete (confirm/fraud actions work)

**Acceptance Criteria**:
- [ ] All 5 scenarios pass in both languages (10 tests total)
- [ ] Test coverage ≥80% for core modules
- [ ] No P0/P1 bugs discovered (or all fixed)
- [ ] Test report generated: `pytest --cov=modules --cov=services --cov-report=html`

**Output**: Test report showing pass/fail status and coverage metrics

---

### Task 5: Error Handling Enhancement (P0)

**Objective**: Ensure no Python stack traces exposed, all errors user-friendly

**Files to Update**:
- `services/ocr_service.py`
- `services/structuring_service.py`
- `modules/chat_manager.py`
- `services/recommendation_service.py`
- All page files

**Requirements**:

1. **Global exception handler** (already exists in app.py, verify it uses i18n):
   ```python
   # app.py:186-191 - Verify this:
   try:
       render()
   except Exception as exc:
       logger.exception("Page render failed: %s", exc)
       st.error(i18n.t("errors.render_failed"))  # ✅ Good
       st.stop()
   ```

2. **Service-level error handling** (add to all service files):
   ```python
   # services/ocr_service.py
   def recognize_bill(image: Image) -> List[OCRResult]:
       """Recognize text from bill image with graceful error handling."""
       try:
           # PaddleOCR call
           result = ocr.ocr(...)
           return result
       except Exception as e:
           logger.error(f"OCR failed: {e}")
           # Return empty result instead of raising
           # UI will show fallback message via i18n
           return []

   # services/structuring_service.py
   def structure_transactions(ocr_text: str) -> List[Transaction]:
       """Structure OCR text into transactions with retry logic."""
       try:
           response = openai.ChatCompletion.create(...)
           return parse_response(response)
       except openai.error.RateLimitError:
           # Specific error handling
           raise ValueError(i18n.t("errors.api_rate_limit"))
       except openai.error.APIError:
           raise ValueError(i18n.t("errors.api_error"))
       except Exception as e:
           logger.error(f"Structuring failed: {e}")
           raise ValueError(i18n.t("errors.structuring_failed"))
   ```

3. **Page-level fallback UI** (add to pages where API calls happen):
   ```python
   # pages/bill_upload.py
   try:
       ocr_results = ocr_service.recognize_bill(image)
       if not ocr_results:
           # Fallback: manual input form
           st.warning(i18n.t("errors.ocr_failed"))
           st.markdown(i18n.t("bill_upload.manual_input_prompt"))
           # Show manual input form...
   except Exception as e:
       st.error(i18n.t("errors.ocr_error", error=str(e)))
   ```

4. **Timeout handling** (add to LLM calls):
   ```python
   # modules/chat_manager.py
   def get_response(user_query: str) -> str:
       try:
           response = openai.ChatCompletion.create(
               timeout=10,  # 10 second timeout
               ...
           )
           return response.choices[0].message.content
       except openai.error.Timeout:
           # Fallback to rule-based response
           return self._fallback_response(user_query)
   ```

**Acceptance Criteria**:
- [ ] No Python stack traces visible to users (test by triggering errors)
- [ ] All error messages use i18n keys (check both languages)
- [ ] Fallback mechanisms work (manual input for OCR, rule-based for LLM)
- [ ] Logs capture full error details (for debugging)

---

### Task 8: README Documentation - Bilingual (P0)

**Objective**: Create professional bilingual READMEs for competition submission

**Files to Create/Update**:
- Update `README.md` (Chinese)
- Create `README_EN.md` (English)

**Requirements**:

1. **README.md Structure** (Chinese - 更新现有文件):
   ```markdown
   # WeFinance Copilot

   [English](./README_EN.md) | 中文

   AI驱动的智能财务助理 - 2025深圳国际金融科技大赛参赛项目

   ## 项目亮点

   - 🌐 **双语支持**：中英文实时切换，面向国际市场
   - 💰 **成本优化97%**：混合OCR架构（PaddleOCR + GPT-4o）
   - 🔍 **可解释AI**：透明展示决策逻辑（XAI）
   - ⚠️ **主动异常检测**：自动发现异常支出并提醒
   - 🔒 **隐私保护**：图片本地处理，零上传

   ## 快速开始

   ### 环境要求
   - Python 3.10+
   - Conda (推荐) 或 pip

   ### 安装步骤

   1. 克隆仓库
   ```bash
   git clone https://github.com/JasonRobertDestiny/WeFinance-Copilot.git
   cd WeFinance-Copilot
   ```

   2. 创建环境
   ```bash
   conda env create -f environment.yml
   conda activate wefinance
   ```

   3. 配置API密钥
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入你的 OpenAI API Key
   ```

   4. 运行应用
   ```bash
   streamlit run app.py
   ```

   应用将在 http://localhost:8501 打开

   ## 核心功能

   ### F1: 智能账单分析器
   - 上传账单图片（PNG/JPG/JPEG）
   - PaddleOCR自动识别中文文字（准确率≥90%）
   - GPT-4o结构化为JSON交易记录
   - 自动分类：餐饮、交通、购物等

   ### F2: 对话式财务顾问
   - 自然语言问答：\"我这个月还能花多少？\"
   - 结合账单数据提供个性化回答
   - 支持预算查询、消费分析、术语解释

   ### F3: 可解释的理财建议（XAI）
   - 3道问题评估风险偏好
   - 基于目标生成资产配置建议
   - **\"为什么？\"按钮**展示决策逻辑

   ### F4: 主动式异常检测
   - 自动检测异常支出（金额、时间、频率）
   - 主动推送警告卡片
   - 用户反馈闭环优化

   ## 技术架构

   ### 核心技术栈
   | 组件 | 技术选型 | 版本 |
   |------|---------|------|
   | 前端框架 | Streamlit | 1.28.0 |
   | OCR引擎 | PaddleOCR | 2.7.0 |
   | LLM服务 | GPT-4o | - |
   | 对话管理 | LangChain | 0.1.0 |
   | 数据处理 | Pandas | 2.0+ |
   | 可视化 | Plotly | 5.18+ |
   | 国际化 | 自研i18n模块 | - |

   ### 混合OCR架构优势

   **成本对比**：
   - 纯GPT-4o Vision: ¥30/100张图片
   - PaddleOCR + GPT-4o: ¥1/100张图片
   - **成本降低97%**

   **流程**：
   1. PaddleOCR本地识别文字（免费）
   2. GPT-4o结构化识别结果（仅文本API，成本低）
   3. 保持高准确率（≥90%）

   ## 开发进度

   - ✅ Sprint 1 (Day 1-3): 基础架构 + OCR
   - ✅ Sprint 2 (Day 4-7): 对话 + 推荐 + XAI
   - 🔄 Sprint 3 (Day 8-10): 国际化 + 优化 + 测试

   ## 测试

   ```bash
   # 运行所有测试
   pytest tests/

   # 查看覆盖率
   pytest tests/ --cov=modules --cov=services --cov-report=html
   ```

   ## 常见问题

   ### 1. OCR识别不准确？
   - 确保图片清晰，光线充足
   - 支持的格式：PNG, JPG, JPEG
   - 如果失败，可使用手动输入功能

   ### 2. API调用失败？
   - 检查 `.env` 文件中的 API Key 是否正确
   - 确认网络连接正常
   - 查看 `streamlit.log` 日志文件

   ### 3. 如何切换语言？
   - 点击左侧边栏顶部的语言选择器
   - 支持中文/English实时切换

   ## 竞赛信息

   - **赛事**：2025深圳国际金融科技大赛（AI赛道）
   - **截止日期**：2025年11月16日 24:00
   - **预期得分**：93/100
     - 产品完整性：40/40
     - 创新性：28/30（XAI + 双语支持）
     - 商业价值：25/30（成本优化 + 国际化）

   ## 许可证

   本项目仅用于2025深圳国际金融科技大赛参赛。

   ## 联系方式

   - GitHub: https://github.com/JasonRobertDestiny/WeFinance-Copilot
   - Email: johnrobertdestiny@gmail.com
   ```

2. **README_EN.md Structure** (English - 新建文件):
   ```markdown
   # WeFinance Copilot

   English | [中文](./README.md)

   AI-Powered Smart Financial Assistant - 2025 Shenzhen International Fintech Competition

   ## Key Highlights

   - 🌐 **Bilingual Support**: Real-time Chinese/English switching for international markets
   - 💰 **97% Cost Reduction**: Hybrid OCR architecture (PaddleOCR + GPT-4o)
   - 🔍 **Explainable AI**: Transparent decision logic (XAI)
   - ⚠️ **Proactive Anomaly Detection**: Automatic spending anomaly alerts
   - 🔒 **Privacy Protection**: Local image processing, zero uploads

   ## Quick Start

   (Same structure as Chinese version, translated to English)
   ```

**Acceptance Criteria**:
- [ ] Both README versions complete and accurate
- [ ] Installation steps verified (test on clean environment)
- [ ] Screenshots added (5-8 images showing bilingual UI)
- [ ] FAQ covers common issues
- [ ] Links to GitHub repo working

---

### Task 9: Code Quality Review (P0)

**Objective**: Ensure code meets PEP8 standards and is production-ready

**Files to Check**: All Python files

**Requirements**:

1. **Run formatters and linters**:
   ```bash
   # Format all code
   black .

   # Check linting
   ruff check .

   # Fix auto-fixable issues
   ruff check --fix .
   ```

2. **Review output and fix remaining issues**:
   - Line length violations (max 88 chars for black, 100 for ruff)
   - Unused imports
   - Missing docstrings
   - Type annotation issues

3. **Add missing docstrings** (English only):
   ```python
   def compute_anomaly_report(
       transactions: List[Dict],
       whitelist_merchants: Set[str]
   ) -> Dict[str, Any]:
       """
       Compute anomaly detection report with whitelist filtering.

       Args:
           transactions: List of transaction dictionaries
           whitelist_merchants: Set of trusted merchant names

       Returns:
           Dictionary containing:
               - active_anomalies: List of detected anomalies
               - all_anomalies: Complete history
               - message: Status message
       """
       # Implementation...
   ```

4. **Fix identified issues from monitoring report**:
   - ✅ app.py:110 - Mixed language docstring → Pure English
   - ✅ app.py:116 - Hardcoded Chinese message → Use i18n
   - ✅ app.py:69,80,151 - `st.experimental_rerun()` → `st.rerun()`

5. **Verify bilingual comments** (complex logic only):
   ```python
   # Risk score calculation using weighted factors
   # 使用加权因子计算风险评分
   risk_score = (
       age_factor * 0.3 +      # Age influence on risk tolerance / 年龄影响
       income_factor * 0.4 +    # Income stability weight / 收入稳定性权重
       investment_exp * 0.3     # Experience consideration / 经验考虑
   )
   ```

**Acceptance Criteria**:
- [ ] `black .` runs without changes (all files formatted)
- [ ] `ruff check .` shows zero errors
- [ ] All public functions have English docstrings
- [ ] Complex logic has bilingual inline comments
- [ ] No deprecated APIs used (e.g., `st.experimental_*`)

**Output**: Clean codebase ready for competition submission

---

## Testing Checklist

After completing all P0 tasks, manually test:

1. **Language Switching**:
   - [ ] Switch from Chinese to English in sidebar
   - [ ] All UI text updates correctly
   - [ ] No data loss after switching
   - [ ] Chart labels/tooltips update

2. **Full User Flow** (in both languages):
   - [ ] Upload bill → OCR succeeds
   - [ ] View spending analysis → Charts render
   - [ ] Chat with advisor → Get response
   - [ ] View investment recs → XAI explanation shows
   - [ ] Anomaly detected → Confirm/mark fraud works

3. **Error Scenarios**:
   - [ ] Upload invalid image → Fallback to manual input
   - [ ] Network error → User-friendly message (no stack trace)
   - [ ] Switch language during API call → No crash

4. **Performance**:
   - [ ] Page load time <2 seconds
   - [ ] Language switch <500ms
   - [ ] Charts render smoothly

---

## Success Metrics

**P0 Tasks Completion**:
- [ ] Task 3: Integration tests passing (≥80%)
- [ ] Task 5: Error handling complete (zero stack traces exposed)
- [ ] Task 8: Bilingual READMEs complete
- [ ] Task 9: Code quality review passed (black + ruff clean)

**Ready for Submission**:
- [ ] All features working in both languages
- [ ] No P0/P1 bugs
- [ ] Documentation complete
- [ ] GitHub repo up-to-date

---

## Next Phase (P1 Tasks - If Time Permits)

After P0 completion, proceed to:
1. Task 4: Performance optimization (caching, lazy loading)
2. Task 6: UI beautification (theme, animations)
3. Task 7: Demo data preparation (sample bills, products)

---

**开始执行 P0 任务！优先顺序：Task 3 → Task 5 → Task 8 → Task 9**
