# WeFinance Copilot - Sprint 3 Development Tasks with i18n Support

## Project Context

**Project Name**: WeFinance Copilot - AI-Powered Smart Financial Assistant
**Competition**: 2025 Shenzhen International Fintech Competition (AI Track)
**Deadline**: November 16, 2025, 24:00
**Current Date**: November 6, 2025
**Time Remaining**: 10 days

## Critical Priority: Internationalization (i18n)

**Epic 0: Implement Chinese-English Language Switching**

### Task 0.1: i18n Architecture Setup
**Files**: Create `utils/i18n.py`, `locales/zh_CN.json`, `locales/en_US.json`

**Requirements**:
1. Create internationalization utility module (`utils/i18n.py`)
   ```python
   """Internationalization support for WeFinance Copilot."""
   import json
   from pathlib import Path
   from typing import Dict, Any

   class I18n:
       """Simple i18n manager for bilingual support."""

       def __init__(self, locale: str = "zh_CN"):
           self.locale = locale
           self.translations = self._load_translations(locale)

       def _load_translations(self, locale: str) -> Dict[str, Any]:
           """Load translation file for given locale."""
           locale_file = Path(__file__).parent.parent / "locales" / f"{locale}.json"
           if locale_file.exists():
               with open(locale_file, "r", encoding="utf-8") as f:
                   return json.load(f)
           return {}

       def t(self, key: str, **kwargs) -> str:
           """Translate key with optional formatting."""
           text = self.translations.get(key, key)
           if kwargs:
               return text.format(**kwargs)
           return text

       def switch_locale(self, locale: str) -> None:
           """Switch to different locale."""
           self.locale = locale
           self.translations = self._load_translations(locale)
   ```

2. Create translation files structure:
   ```
   locales/
   ├── zh_CN.json  # Chinese (Simplified)
   └── en_US.json  # English
   ```

3. Initialize in `utils/session.py`:
   ```python
   from utils.i18n import I18n

   def init_session_state() -> None:
       """Initialize session state variables."""
       if "locale" not in st.session_state:
           st.session_state.locale = "zh_CN"  # Default to Chinese

       if "i18n" not in st.session_state:
           st.session_state.i18n = I18n(st.session_state.locale)

       # ... existing code ...
   ```

**Acceptance Criteria**:
- i18n module functional with locale switching
- Translation files structure created
- Session state properly initialized

### Task 0.2: Create Translation Dictionaries
**Files**: `locales/zh_CN.json`, `locales/en_US.json`

**Requirements**:
1. Extract all user-facing text from codebase
2. Create comprehensive translation dictionaries
3. Organize by feature/page for maintainability

**Example Structure**:
```json
{
  "app": {
    "title": "WeFinance Copilot",
    "subtitle": "AI-Driven Smart Financial Assistant",
    "reset_session": "Reset Session",
    "reset_success": "Session data cleared",
    "version": "Version: {version}",
    "competition": "Competition: 2025 Shenzhen International Fintech Competition",
    "goal": "Goal: Complete MVP in 10 days"
  },
  "navigation": {
    "home": "Home · Project Overview",
    "bill_upload": "Bill Upload & OCR",
    "spending_insights": "Spending Analysis Dashboard",
    "advisor_chat": "Conversational Financial Advisor",
    "investment_recs": "Investment Recommendations & Explanations"
  },
  "home": {
    "welcome": "Welcome to WeFinance Copilot Demo. Experience the following features via left navigation:",
    "feature_bill": "**Bill Upload & OCR**: Experience high-precision recognition from hybrid OCR architecture",
    "feature_analysis": "**Spending Analysis Dashboard**: Understand your spending patterns and trends",
    "feature_chat": "**Conversational Financial Advisor**: Get personalized advice through AI chat",
    "feature_recs": "**Investment Recommendations**: View recommended products and decision logic",
    "info_version": "Current version focuses on core framework, features will be enhanced in future iterations"
  },
  "errors": {
    "page_not_found": "Selected page does not exist, please choose again from sidebar",
    "render_failed": "Page rendering error occurred, please refresh or contact support",
    "network_error": "Network connection failed, please check network settings",
    "api_rate_limit": "Service busy, please try again later",
    "ocr_failed": "Image recognition failed, manual input recommended"
  }
}
```

**Acceptance Criteria**:
- All UI text extracted and translated
- Both language versions complete and accurate
- JSON files valid and properly formatted

### Task 0.3: Integrate i18n in UI Components
**Files**: All files in `pages/` directory, `app.py`

**Requirements**:
1. Replace all hardcoded strings with i18n calls:
   ```python
   # Before:
   st.title("WeFinance Copilot")
   st.subheader("AI驱动的智能财务助理原型")

   # After:
   i18n = st.session_state.i18n
   st.title(i18n.t("app.title"))
   st.subheader(i18n.t("app.subtitle"))
   ```

2. Add language switcher in sidebar:
   ```python
   with st.sidebar:
       # Language switcher at top
       locale_options = {
           "zh_CN": "中文",
           "en_US": "English"
       }
       selected_locale = st.selectbox(
           "Language / 语言",
           options=list(locale_options.keys()),
           format_func=lambda x: locale_options[x],
           index=0 if st.session_state.locale == "zh_CN" else 1
       )

       if selected_locale != st.session_state.locale:
           st.session_state.locale = selected_locale
           st.session_state.i18n.switch_locale(selected_locale)
           st.rerun()
   ```

3. Update all pages systematically:
   - `app.py`: Main navigation and layout
   - `pages/bill_upload.py`: Upload form and messages
   - `pages/spending_insights.py`: Charts and analysis text
   - `pages/advisor_chat.py`: Chat interface
   - `pages/investment_recs.py`: Questionnaire and recommendations

**Acceptance Criteria**:
- All UI text uses i18n system
- Language switcher functional
- Page content switches without breaking layout
- No hardcoded strings remain

### Task 0.4: Bilingual Code Documentation
**Files**: All Python files

**Requirements**:
1. Docstrings: Keep in English (industry standard)
2. Complex algorithm comments: Bilingual
   ```python
   # Complex business logic - provide both languages for team clarity
   # 复杂业务逻辑 - 提供双语注释以便团队理解

   # Risk score calculation using weighted factors
   # 使用加权因子计算风险评分
   risk_score = (
       age_factor * 0.3 +      # Age influence on risk tolerance / 年龄对风险承受能力的影响
       income_factor * 0.4 +    # Income stability weight / 收入稳定性权重
       investment_exp * 0.3     # Experience consideration / 投资经验考虑
   )
   ```

3. User-facing error messages: Use i18n system
   ```python
   # Before:
   raise ValueError("无效的交易金额")

   # After:
   raise ValueError(i18n.t("errors.invalid_amount"))
   ```

**Acceptance Criteria**:
- Docstrings in English
- Critical logic has bilingual comments
- Error messages use i18n
- Code remains PEP8 compliant

## Completed Work

### Sprint 1 ✅ (Day 1-3)
- ✅ Project structure and conda environment setup
- ✅ PaddleOCR + GPT-4o hybrid OCR architecture implementation
- ✅ Bill upload page (`pages/bill_upload.py`)
- ✅ Data analysis module (`modules/analysis.py`)
  - Category statistics, spending trends, anomaly detection (Z-score)
  - Insight text generation
- ✅ Spending insights page (`pages/spending_insights.py`)
  - Plotly charts
  - Anomaly detection table
- ✅ Unit tests (`tests/test_ocr_service.py`, `tests/test_structuring_service.py`)

### Sprint 2 ✅ (Day 4-7)
- ✅ Chat manager (`modules/chat_manager.py`)
  - Budget queries, spending analysis, term explanations, financial advice
  - GPT-4o integration
- ✅ Financial advisor chat page (`pages/advisor_chat.py`)
  - Budget control sidebar
  - Example questions
- ✅ LangChain Agent (`services/langchain_agent.py` - optional)
  - Tool definitions (query_budget, query_spending, query_category)
  - ConversationBufferMemory
- ✅ Recommendation service (`services/recommendation_service.py`)
  - Risk assessment questionnaire (3 questions)
  - Asset allocation rules
  - **XAI explanation generation** (competition highlight)
- ✅ Investment recommendations page (`pages/investment_recs.py`)
  - 4-step workflow: Risk assessment → Goals → Allocation → XAI explanation

## Sprint 3 Development Tasks (Day 8-10)

### Epic 3.1: Proactive Anomaly Detection Optimization (F4 Bonus)

#### Task 1: Anomaly Detection UI Enhancement
**Files**: `pages/spending_insights.py`, `app.py`

**Requirements**:
1. Add anomaly warning cards at homepage top (`app.py`)
   - Use `st.error()` or `st.warning()` for highlighting
   - Display latest 3 anomalies (time, merchant, amount, reason)
   - Add "Confirm My Transaction" and "Mark as Fraud" buttons
   - Text via i18n: `i18n.t("anomaly.confirm")`, `i18n.t("anomaly.mark_fraud")`

2. Add anomaly history view in `spending_insights.py`
   - Sidebar displays all anomaly records
   - Mark confirmed/rejected anomalies
   - All labels via i18n

3. User feedback loop
   - After confirmation, remove from warning list
   - After fraud marking, highlight transaction (red)
   - Record feedback in `st.session_state`
   - Success messages via i18n

**Acceptance Criteria**:
- Anomaly cards display correctly with smooth interaction
- User operations receive real-time feedback
- All text supports bilingual switching
- Anomaly history feature complete

#### Task 2: Anomaly Detection Algorithm Optimization
**Files**: `modules/analysis.py`

**Requirements**:
1. Whitelist mechanism
   - Add "Trusted Merchants Management" in sidebar (i18n)
   - Support adding/removing whitelist merchants
   - Whitelist merchants bypass anomaly detection

2. Threshold tuning
   - Test different Z-score thresholds (1.5/2.0/2.5)
   - Auto-adjust based on data distribution

3. New user graceful degradation
   - When data volume <10 transactions, reduce sensitivity
   - Show message via i18n: `i18n.t("anomaly.data_accumulating")`

**Acceptance Criteria**:
- Anomaly detection accuracy ≥85%
- False positive rate <10%
- Whitelist feature functional
- Messages support bilingual

### Epic 3.2: Integration Testing & Performance Optimization

#### Task 3: End-to-End Integration Testing
**Files**: Create `tests/test_integration.py`

**Requirements**:
1. Design 5 complete user flow test cases
   - Scenario 1: Upload bill → View analysis → Chat query → View recs
   - Scenario 2: Batch upload → Anomaly detection → User confirmation
   - Scenario 3: Multi-turn chat → Clear history → Restart Q&A
   - Scenario 4: Risk questionnaire → Generate recs → View XAI
   - Scenario 5: Anomaly trigger → User feedback → View history

2. Test both languages (zh_CN and en_US)
3. Use mock data (avoid real API calls)
4. Record test results and bugs

**Acceptance Criteria**:
- 5 test cases pass rate ≥80%
- All P0/P1 bugs fixed
- Both languages tested
- Test report complete

#### Task 4: Performance Optimization
**Files**: All page files

**Requirements**:
1. Add caching optimization
   - `@st.cache_data` in `spending_insights.py` for data processing
   - Cache common query responses in `advisor_chat.py`
   - Cache recommendation results in `investment_recs.py`
   - Cache translation lookups in i18n module

2. Chart lazy loading
   - Charts collapsed by default
   - Render on "Expand" button click
   - Button text via i18n

3. Optimize data processing
   - Use Pandas vectorized operations
   - Reduce unnecessary data transformations

**Acceptance Criteria**:
- Page load time ≤2 seconds
- Repeated operation response time reduced ≥50%
- Cache hit rate ≥40%
- Language switching smooth (<500ms)

#### Task 5: Error Handling Enhancement
**Files**: All service files

**Requirements**:
1. Global exception capture
   - Add global exception handling in `app.py`
   - Add try-except to all API calls

2. User-friendly error messages (via i18n)
   - Network error → `i18n.t("errors.network_error")`
   - API rate limit → `i18n.t("errors.api_rate_limit")`
   - OCR failure → `i18n.t("errors.ocr_failed")`

3. Fallback mechanisms
   - OCR failure → Manual input form
   - LLM timeout → Rule-based simple response

**Acceptance Criteria**:
- No Python stack traces exposed
- All exceptions have friendly bilingual messages
- Fallback mechanisms effective

### Epic 3.3: Demo Presentation Optimization

#### Task 6: UI Beautification & Experience Optimization
**Files**: All page files, `.streamlit/config.toml` (create new)

**Requirements**:
1. Unified UI style
   - Create `.streamlit/config.toml` for theme
   - Unified color scheme (blue/green financial style)
   - Unified button styles, card spacing

2. Interaction experience optimization
   - Custom loading animations (bilingual text)
   - Optimize success/failure messages with icons
   - First-time user guide via i18n

3. Responsive layout
   - Use `st.columns()` for optimized layout
   - Display key metrics using metric cards

**Acceptance Criteria**:
- UI style unified and professional
- Interactions smooth without lag
- New users quickly get started in either language

#### Task 7: Demo Data Preparation
**Files**: `assets/sample_bills/`, `assets/mock_products.json`

**Requirements**:
1. Prepare 10 high-quality sample bills
   - Cover 7 categories (dining, transport, shopping, medical, entertainment, education, other)
   - Include 2 anomalous transactions
   - Ensure OCR accuracy ≥95%

2. Prepare conversation example scripts (bilingual)
   - 10 example questions (4 intent types)
   - Verify response accuracy in both languages

3. Optimize mock product library (bilingual)
   - Expand to 20 financial products
   - Cover all risk levels
   - Product names and descriptions in both languages

**Acceptance Criteria**:
- Sample bills recognized accurately
- Conversation examples have reasonable bilingual responses
- Product library data complete in both languages

### Epic 3.4: Documentation & Competition Materials

#### Task 8: README Documentation Enhancement
**Files**: `README.md`, create `README_EN.md`

**Requirements**:
1. Create bilingual READMEs
   - `README.md`: Chinese version
   - `README_EN.md`: English version
   - Cross-reference between versions

2. Update quick start guide
   - Verify installation steps
   - Add FAQ for common issues

3. Add demo descriptions
   - Feature screenshots (5-8 images) with bilingual UI
   - Placeholder for demo video link

4. Update tech stack description
   - Actual version numbers
   - Explain hybrid OCR architecture advantages
   - Mention i18n support

**Acceptance Criteria**:
- Both README versions complete
- Installation steps verified
- FAQ covers common issues
- Non-technical people understand core features

#### Task 9: Code Quality Review
**Files**: All Python files

**Requirements**:
1. Code standards check
   - Run `black .` to format all code
   - Run `ruff check .` to check standards
   - Add missing docstrings (English)

2. Comment review
   - Docstrings in English (standard practice)
   - Complex logic has bilingual inline comments
   - User-facing strings use i18n

3. Code refactoring
   - Extract repeated code into utilities
   - Simplify >3 nesting levels
   - Optimize data structures

**Acceptance Criteria**:
- Code passes black and ruff checks
- Docstrings in English
- Critical logic has bilingual comments
- Function complexity ≤3 nesting levels

## Technical Constraints

### Environment Configuration
```bash
conda activate wefinance
python --version  # Python 3.10.x
```

### API Configuration (.env file)
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-debs5nl5QYdw7AwnXMxHSzxVu1e15KzJsgwHK9Khp25STqMe
OPENAI_BASE_URL=https://newapi.deepwisdom.ai/v1
OPENAI_MODEL=gpt-4o

PADDLE_OCR_USE_ANGLE_CLASS=True
PADDLE_OCR_LANG=ch
```

### Core Dependencies
- Streamlit 1.28.0
- PaddleOCR 2.7.0
- OpenAI >=1.6.1
- LangChain 0.1.0
- Pandas 2.0+
- Plotly 5.18+

## Quality Standards

### Functional Acceptance
- [ ] i18n system functional with smooth language switching
- [ ] All UI text supports Chinese and English
- [ ] Anomaly detection functioning (accuracy ≥85%)
- [ ] All integration tests pass (≥80%)
- [ ] UI beautiful and unified

### Performance Acceptance
- [ ] Page load time ≤2 seconds
- [ ] Language switching <500ms
- [ ] OCR response time ≤3 seconds
- [ ] Chat response time ≤3 seconds
- [ ] Cache hit rate ≥40%

### Code Quality
- [ ] Code conforms to PEP8
- [ ] Docstrings in English
- [ ] Complex logic has bilingual comments
- [ ] No Python stack traces exposed
- [ ] Unit test coverage ≥70%

## Project Structure Reference

```
WeFinance/
├── app.py                      # Main entry (add language switcher)
├── locales/                    # NEW: Translation files
│   ├── zh_CN.json             # Chinese translations
│   └── en_US.json             # English translations
├── utils/
│   ├── i18n.py                # NEW: Internationalization module
│   └── session.py             # Updated: Initialize i18n
├── pages/
│   ├── bill_upload.py         # Update: Use i18n for all text
│   ├── spending_insights.py   # Update: i18n + anomaly history
│   ├── advisor_chat.py        # Update: i18n + caching
│   └── investment_recs.py     # Update: i18n + caching
├── modules/
│   ├── analysis.py           # Update: Whitelist + threshold tuning
│   └── chat_manager.py       # Update: Bilingual responses
├── services/
│   ├── ocr_service.py        # Update: Error handling + i18n
│   ├── structuring_service.py # Update: Error handling + i18n
│   ├── recommendation_service.py # Update: Bilingual recs + i18n
│   └── langchain_agent.py    # Update: Bilingual prompts
├── tests/
│   ├── test_ocr_service.py   # Update: Test both languages
│   ├── test_structuring_service.py
│   ├── test_integration.py   # NEW: E2E tests
│   └── test_i18n.py          # NEW: i18n module tests
├── .streamlit/
│   └── config.toml           # NEW: Theme configuration
├── assets/
│   ├── sample_bills/         # Expand: 10 high-quality bills
│   └── mock_products.json    # Update: Bilingual products
├── README.md                  # Chinese version
└── README_EN.md              # NEW: English version
```

## Priority

**P0 (Must Complete - Critical)**:
0. Task 0.1-0.4: i18n system implementation
1. Task 3: End-to-end integration testing
2. Task 5: Error handling enhancement
3. Task 8: Bilingual README documentation
4. Task 9: Code quality review

**P1 (Important)**:
1. Task 1: Anomaly detection UI enhancement
2. Task 4: Performance optimization (including i18n caching)
3. Task 6: UI beautification
4. Task 7: Bilingual demo data preparation

**P2 (Bonus Points)**:
1. Task 2: Anomaly detection algorithm optimization

## Development Recommendations

1. **i18n First**: Complete i18n architecture before other tasks
2. **Incremental Testing**: Test language switching after each page update
3. **Priority-based Development**: Complete P0 tasks first
4. **Keep It Simple**: Follow Linus philosophy, reject over-engineering
5. **User Experience First**: Smooth language switching is critical
6. **Error Handling Priority**: Ensure bilingual error messages

## Implementation Strategy

### Phase 1: i18n Foundation (Day 8 morning)
- Task 0.1: Set up i18n architecture
- Task 0.2: Create translation dictionaries
- Test with one page (app.py) to verify system works

### Phase 2: UI i18n Integration (Day 8 afternoon - Day 9 morning)
- Task 0.3: Integrate i18n in all UI components
- Task 0.4: Add bilingual code comments
- Test language switching across all pages

### Phase 3: Core Optimization (Day 9 afternoon)
- Task 5: Error handling (bilingual messages)
- Task 4: Performance optimization (cache i18n lookups)
- Task 3: Integration testing (test both languages)

### Phase 4: Polish & Documentation (Day 10)
- Task 6: UI beautification
- Task 7: Bilingual demo data
- Task 8: Bilingual README
- Task 9: Code quality review
- Tasks 1-2: Anomaly detection (if time permits)

## Competition Scoring Criteria Reminder

- **Product Implementation Completeness (40%)**: F1+F2+F3 must be 100% complete
- **Innovation (30%)**: XAI explanation + bilingual support are core highlights
- **Business Value (30%)**: Hybrid OCR architecture (97% cost optimization) + international market readiness

**Expected Score**: 88/100 → 93/100 (after completing Sprint 3 with i18n)

---

**Start Development!**
