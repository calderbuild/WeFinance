# WeFinance Copilot - Next Phase Development Prompt

## Current Status (2025-11-06 18:32)

### ✅ Completed Tasks

**P0 Critical Tasks - 88.75% Complete**:
- ✅ Task 9: Code Quality Review (100%) - All issues fixed, black/ruff passing
- ✅ Task 3: Fix Failing Test (100%) - test_error_handling_messages now supports bilingual
- ✅ Task 3: Integration Testing (90%) - 16/16 tests passing, 58% coverage
- ✅ Task 8: Bilingual README (90%) - README_EN.md complete, missing screenshots
- ✅ Task 5: Error Handling (75%) - User-friendly messages, missing fallbacks

**Application Status**:
- ✅ Running on http://localhost:8503
- ✅ All core features functional
- ✅ Bilingual support working (Chinese/English)
- ✅ No runtime errors

### 📊 Test Results

```bash
======================== 16 passed, 1 warning in 1.09s =========================

Coverage Report:
- utils/i18n.py: 94% ✅
- services/ocr_service.py: 80% ✅
- services/structuring_service.py: 80% ✅
- services/recommendation_service.py: 87% ✅
- modules/analysis.py: 73% ⚠️
- modules/chat_manager.py: 48% ⚠️ (需要提升)
- utils/session.py: 36% ⚠️ (需要提升)
```

---

## Phase 2: Remaining P1 Tasks

### Priority Order

**P1 (Important - Complete Today)**:
1. ✨ Task 8: Add UI Screenshots (30 min)
2. 🛡️ Task 5: Implement Fallback Mechanisms (1.5 hours)
3. 📈 Task 3: Improve Test Coverage (2 hours)

---

## Task 8: Add UI Screenshots to README (P1)

### Objective
Complete README_EN.md with 5-8 high-quality screenshots showing bilingual UI.

### Requirements

**Screenshots Needed** (save to `docs/screenshots/`):
1. `01-homepage-zh.png` - 首页（中文）显示项目介绍和异常警告
2. `02-homepage-en.png` - Homepage (English) with project intro
3. `03-language-switch.png` - 侧边栏语言切换器特写
4. `04-bill-upload-zh.png` - 账单上传页面（中文）
5. `05-spending-analysis-en.png` - Spending dashboard (English)
6. `06-chat-advisor-zh.png` - 对话式顾问界面（中文）
7. `07-investment-recs-en.png` - Investment recommendations with XAI (English)
8. `08-anomaly-detection.png` - 异常检测警告卡片

### Implementation Steps

1. **Create screenshot directory**:
   ```bash
   mkdir -p docs/screenshots
   ```

2. **Capture screenshots**:
   - Open browser to http://localhost:8503
   - Take full-page screenshots (1920x1080 recommended)
   - Alternate between Chinese and English for each feature
   - Ensure UI elements are clearly visible

3. **Update README_EN.md**:
   Insert screenshots after "## Key Highlights" section:
   ```markdown
   ## Screenshots

   ### Homepage & Language Switching
   <table>
   <tr>
   <td><img src="docs/screenshots/01-homepage-zh.png" alt="Homepage (Chinese)" /></td>
   <td><img src="docs/screenshots/02-homepage-en.png" alt="Homepage (English)" /></td>
   </tr>
   </table>

   *Seamless language switching via sidebar selector*

   ### Bill Upload & OCR
   ![Bill Upload](docs/screenshots/04-bill-upload-zh.png)
   *PaddleOCR automatically extracts transaction data from bill images*

   ### Spending Analysis Dashboard
   ![Spending Analysis](docs/screenshots/05-spending-analysis-en.png)
   *Category breakdown, trends, and anomaly alerts*

   ### Conversational Financial Advisor
   ![Chat Advisor](docs/screenshots/06-chat-advisor-zh.png)
   *Natural language queries about budget and spending*

   ### Investment Recommendations with XAI
   ![Investment Recommendations](docs/screenshots/07-investment-recs-en.png)
   *Transparent decision logic with "Why?" explanations*

   ### Proactive Anomaly Detection
   ![Anomaly Detection](docs/screenshots/08-anomaly-detection.png)
   *Real-time alerts for suspicious transactions*
   ```

4. **Update Chinese README.md** with same screenshots

### Acceptance Criteria
- [ ] 8 screenshots captured at 1920x1080 resolution
- [ ] Images saved to `docs/screenshots/` directory
- [ ] Both README.md and README_EN.md updated with image references
- [ ] Screenshots show both Chinese and English interfaces
- [ ] All images load correctly when viewing README on GitHub

---

## Task 5: Implement Fallback Mechanisms (P1)

### Objective
Add graceful degradation when OCR or LLM services fail.

### 5.1: OCR Failure → Manual Input Form

**File**: `pages/bill_upload.py`

**Current Behavior**:
```python
# When OCR fails, just shows error message
try:
    ocr_results = ocr_service.recognize_bill(image)
except Exception as e:
    st.error(i18n.t("errors.ocr_error", error=str(e)))
    # User has no way to proceed! ❌
```

**Required Behavior**:
```python
# When OCR fails, show manual input form as fallback
try:
    ocr_results = ocr_service.recognize_bill(image)
    if not ocr_results:  # OCR returned empty
        st.warning(i18n.t("bill_upload.ocr_empty_fallback"))
        _show_manual_input_form(i18n)
except Exception as e:
    st.error(i18n.t("errors.ocr_error", error=str(e)))
    st.info(i18n.t("bill_upload.manual_input_prompt"))
    _show_manual_input_form(i18n)

def _show_manual_input_form(i18n):
    """Display manual transaction input form when OCR fails."""
    st.markdown(f"### {i18n.t('bill_upload.manual_input_title')}")

    with st.form("manual_transaction_form"):
        date = st.date_input(i18n.t("bill_upload.field_date"))
        merchant = st.text_input(i18n.t("bill_upload.field_merchant"))
        category = st.selectbox(
            i18n.t("bill_upload.field_category"),
            options=["餐饮", "交通", "购物", "日常", "其他"]
        )
        amount = st.number_input(
            i18n.t("bill_upload.field_amount"),
            min_value=0.0,
            step=0.01
        )

        submitted = st.form_submit_button(i18n.t("common.btn_submit"))

        if submitted:
            # Create transaction object
            transaction = Transaction(
                id=f"manual-{int(time.time())}",
                date=date,
                merchant=merchant,
                category=category,
                amount=float(amount)
            )
            # Add to session state
            session_utils.add_transaction(transaction)
            st.success(i18n.t("bill_upload.manual_input_success"))
            st.rerun()
```

**Translation Keys to Add** (`locales/zh_CN.json` and `locales/en_US.json`):
```json
{
  "bill_upload": {
    "ocr_empty_fallback": "OCR未识别到内容，请使用手动输入。",
    "manual_input_prompt": "您可以手动输入交易信息：",
    "manual_input_title": "手动输入交易",
    "manual_input_success": "交易已添加成功！",
    "field_date": "日期",
    "field_merchant": "商户名称",
    "field_category": "类别",
    "field_amount": "金额（元）"
  }
}
```

### 5.2: LLM Timeout → Rule-Based Fallback

**File**: `modules/chat_manager.py`

**Current Behavior**:
```python
def generate_response(self, user_query: str) -> str:
    try:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            temperature=0.7,
            # No timeout! ❌
        )
        return response.choices[0].message.content
    except OpenAIError as e:
        logger.error(f"LLM call failed: {e}")
        raise  # Exposes error to user ❌
```

**Required Behavior**:
```python
def generate_response(self, user_query: str) -> str:
    """Generate response with timeout and rule-based fallback."""
    try:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            temperature=0.7,
            timeout=10.0,  # 10 second timeout ✅
        )
        return response.choices[0].message.content

    except Timeout:
        logger.warning("LLM timeout, using rule-based fallback")
        return self._fallback_response(user_query)

    except OpenAIError as e:
        logger.error(f"LLM call failed: {e}")
        return self._fallback_response(user_query)

def _fallback_response(self, query: str) -> str:
    """Rule-based response when LLM unavailable."""
    query_lower = query.lower()

    # Budget queries
    if any(kw in query_lower for kw in ["预算", "budget", "还能花", "can spend"]):
        spent = sum(t.amount for t in self.transactions)
        remaining = self.monthly_budget - spent
        return self._i18n.t(
            "chat.fallback_budget",
            spent=spent,
            remaining=remaining,
            budget=self.monthly_budget
        )

    # Category queries
    if any(kw in query_lower for kw in ["哪方面", "category", "花钱最多", "spending most"]):
        category_totals = calculate_category_totals(self.transactions)
        top_category = max(category_totals.items(), key=lambda x: x[1])
        return self._i18n.t(
            "chat.fallback_category",
            category=top_category[0],
            amount=top_category[1]
        )

    # Default fallback
    return self._i18n.t("chat.fallback_generic")
```

**Translation Keys to Add**:
```json
{
  "chat": {
    "fallback_budget": "您本月预算¥{budget}，已花费¥{spent}，剩余¥{remaining}。（离线模式）",
    "fallback_category": "您在{category}类别的花费最多：¥{amount}。（离线模式）",
    "fallback_generic": "抱歉，AI服务暂时不可用。请稍后重试或咨询人工客服。"
  }
}
```

### Acceptance Criteria
- [ ] OCR failure shows manual input form in both languages
- [ ] Manual input form validates data correctly
- [ ] LLM timeout set to 10 seconds
- [ ] Rule-based fallback handles 3+ common query types
- [ ] Fallback responses clearly indicate "offline mode"
- [ ] All error paths tested manually

---

## Task 3: Improve Test Coverage (P1)

### Objective
Raise overall test coverage from 58% to 70%+ by adding tests for under-tested modules.

### Target Modules

**1. modules/chat_manager.py (48% → 70%)**

Add tests in `tests/test_chat_manager.py`:
```python
def test_chat_manager_timeout_fallback(monkeypatch):
    """Test LLM timeout triggers rule-based fallback."""
    manager = ChatManager(transactions=sample_transactions(), monthly_budget=1000)

    # Mock LLM to raise Timeout
    def mock_timeout(*args, **kwargs):
        raise Timeout("Request timed out")

    monkeypatch.setattr(manager.client.chat.completions, "create", mock_timeout)

    response = manager.generate_response("我这个月还能花多少？")
    assert "剩余" in response or "offline" in response.lower()

def test_chat_manager_category_query():
    """Test category query with real transaction data."""
    transactions = [
        Transaction(id="1", date=date.today(), merchant="星巴克", category="餐饮", amount=50),
        Transaction(id="2", date=date.today(), merchant="滴滴", category="交通", amount=20),
        Transaction(id="3", date=date.today(), merchant="美团", category="餐饮", amount=80),
    ]
    manager = ChatManager(transactions=transactions, monthly_budget=1000)

    response = manager.generate_response("我哪方面花钱最多？")
    assert "餐饮" in response  # Should identify dining as top category

def test_chat_manager_clear_history():
    """Test conversation history clearing."""
    manager = ChatManager(transactions=[], monthly_budget=1000)
    manager.add_message("user", "Hello")
    manager.add_message("assistant", "Hi there")

    assert len(manager.messages) == 3  # system + 2 messages

    manager.clear_history()
    assert len(manager.messages) == 1  # Only system message remains
```

**2. utils/session.py (36% → 60%)**

Add tests in `tests/test_session.py`:
```python
def test_session_transaction_management():
    """Test adding and retrieving transactions from session."""
    # Initialize session state
    init_session_state()

    # Add transactions
    txn1 = Transaction(id="1", date=date.today(), merchant="Test", category="餐饮", amount=100)
    add_transaction(txn1)

    # Retrieve
    transactions = get_transactions()
    assert len(transactions) == 1
    assert transactions[0].merchant == "Test"

def test_session_anomaly_state_update():
    """Test anomaly state persistence."""
    init_session_state()

    anomaly = {
        "transaction_id": "txn-999",
        "date": "2025-11-06",
        "merchant": "可疑商户",
        "amount": 9999.0,
        "reason": "异常高额消费"
    }

    update_anomaly_state(active=[anomaly], message="检测到异常")

    active = get_active_anomalies()
    assert len(active) == 1
    assert active[0]["merchant"] == "可疑商户"

def test_session_whitelist_management():
    """Test trusted merchant whitelist."""
    init_session_state()

    # Add to whitelist
    add_trusted_merchant("星巴克")
    add_trusted_merchant("盒马鲜生")

    whitelist = get_trusted_merchants()
    assert "星巴克" in whitelist
    assert "盒马鲜生" in whitelist
    assert len(whitelist) == 2
```

### Coverage Targets
- [ ] chat_manager.py: 48% → 70% (+22%)
- [ ] session.py: 36% → 60% (+24%)
- [ ] Overall coverage: 58% → 70% (+12%)

### Run Coverage Report
```bash
pytest tests/ --cov=modules --cov=services --cov=utils --cov-report=term --cov-report=html
```

---

## Implementation Order

### Phase 2.1: Screenshots (30 min)
1. Capture all 8 screenshots
2. Update both READMEs
3. Verify images load on GitHub

### Phase 2.2: Fallback Mechanisms (1.5 hours)
1. Implement OCR manual input form (45 min)
2. Implement LLM timeout + rule-based fallback (45 min)
3. Manual testing of both fallbacks

### Phase 2.3: Test Coverage (2 hours)
1. Write chat_manager tests (1 hour)
2. Write session tests (45 min)
3. Run coverage report and verify 70%+ (15 min)

**Total Estimated Time**: 4 hours

---

## Success Criteria

After completing Phase 2, the project should have:
- ✅ 100% of P0 tasks complete
- ✅ 95%+ of P1 tasks complete
- ✅ 70%+ test coverage
- ✅ Professional documentation with screenshots
- ✅ Robust error handling with graceful degradation
- ✅ Ready for competition submission

---

## Competition Submission Checklist

Before final submission:
- [ ] All tests passing (16/16)
- [ ] Coverage ≥70%
- [ ] README screenshots present
- [ ] No hardcoded credentials in code
- [ ] Application runs without errors
- [ ] Both Chinese and English interfaces work
- [ ] GitHub repository up-to-date
- [ ] Demo video prepared (if required)

---

## Notes for Developer

**Key Files Modified in Phase 1**:
- ✅ app.py (lines 110, 116) - Fixed docstring and i18n
- ✅ locales/zh_CN.json - Added app.no_transaction_data
- ✅ locales/en_US.json - Added app.no_transaction_data
- ✅ tests/test_integration.py - Fixed bilingual error assertions

**Code Quality Status**:
- ✅ Black formatting: All files formatted
- ✅ Ruff linting: All checks passed
- ✅ No deprecated APIs
- ✅ All docstrings in English

**Current Application State**:
- Running on http://localhost:8503
- All core features functional
- No runtime errors
- Ready for Phase 2 development

---

**开始执行 Phase 2 任务！优先顺序：Screenshots → Fallbacks → Test Coverage**
