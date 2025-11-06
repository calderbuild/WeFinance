# Codex开发任务 - UX/UI优化与测试修复

## 背景上下文

**当前项目状态**:
- ✅ Vision OCR实现完成（100%识别率）
- ✅ Fallback机制完成（CSV上传、手动表单）
- ✅ 双语支持完整（中英文i18n）
- ❌ **5个测试失败**（test_ocr_service.py因Vision OCR重构失败）
- ⏳ 测试覆盖率未验证（需要pytest-cov）
- ⏳ UI截图待完成（无GUI环境）

**Claude Code的UX/UI分析结论**（见`UX_UI_OPTIMIZATION_PLAN.md`）:

应用Linus三问哲学，识别了3个真实痛点：
1. **功能割裂**: 用户需要在5个页面间跳转
2. **重复输入**: Budget在多个页面分别输入
3. **反馈缺失**: Vision OCR识别时无进度提示

**优化策略**: 从简单到复杂，优先修复bug，再逐步提升UX。

---

## 任务优先级

### 🔴 P0: 修复失败的测试（必须完成）

**为什么紧急**:
- 5个测试失败影响CI/CD
- 测试是代码质量保证的基础
- 阻塞后续开发

**失败原因**: Vision OCR重构后，`services/ocr_service.py`不再使用PaddleOCR，但测试还在验证旧逻辑。

**任务详情**: 见下方"任务1"

---

### 🟠 P1: UX优化 - Vision OCR进度反馈（高优先级）

**为什么重要**:
- Vision OCR耗时2-5秒，用户等待时焦虑
- 直接影响比赛demo演示效果
- 实现成本低（+10行代码）

**任务详情**: 见下方"任务2"

---

### 🟡 P2: UX优化 - 首页进度引导（建议完成）

**为什么有用**:
- 新用户不知道从哪里开始
- 引导流程，降低学习成本
- 实现成本中等（+30行代码）

**任务详情**: 见下方"任务3"

---

### 🟢 P3: UX优化 - 全局Budget设置（可选）

**为什么建议**:
- 减少重复输入
- 符合DRY原则
- 实现成本低（+5行代码）

**任务详情**: 见下方"任务4"

---

## 任务1: 修复失败的OCR测试 🔴

### 问题分析

**失败测试**:
1. `test_extract_text_success` - 测试PaddleOCR文本提取（已废弃）
2. `test_process_files_returns_structured_transactions` - 测试PaddleOCR+structuring（已废弃）
3. `test_process_files_invalid_image_raises_error` - 测试错误处理（需适配）
4. `test_structure_transactions_handles_api_failure` - 测试structuring_service（已废弃）
5. `test_error_handling_messages` - 测试错误消息（需适配）

**根本原因**: `services/ocr_service.py`现在直接使用`VisionOCRService`，不再调用PaddleOCR或`structuring_service`。

### 解决方案

**策略**: 删除过时测试，添加Vision OCR测试。

**文件**: `tests/test_ocr_service.py`

**步骤**:

#### Step 1: 删除过时测试

删除以下测试函数（它们测试的是已废弃的PaddleOCR逻辑）:
```python
# 删除这些函数
def test_extract_text_success(...)  # 测试PaddleOCR文本提取
def test_process_files_returns_structured_transactions(...)  # 测试PaddleOCR+structuring
def test_structure_transactions_handles_api_failure(...)  # 测试structuring_service
```

#### Step 2: 添加Vision OCR测试

新增测试用例，验证Vision OCR集成：

```python
"""测试Vision OCR集成到OCRService"""

from unittest.mock import patch, MagicMock
import pytest
from services.ocr_service import OCRService
from models.entities import Transaction

@patch('services.vision_ocr_service.OpenAI')
def test_process_files_with_vision_ocr_success(mock_openai):
    """测试通过Vision OCR成功处理文件"""
    # Mock Vision OCR响应
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '''[
        {"date": "2025-11-01", "merchant": "测试商户", "category": "餐饮", "amount": 45.0}
    ]'''
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    # 创建fake图片文件
    from io import BytesIO
    fake_file = BytesIO(b'fake_image_data')
    fake_file.name = "test_bill.png"

    # 测试
    service = OCRService()
    results = service.process_files([fake_file])

    # 验证
    assert len(results) == 1
    result = results[0]
    assert result.filename == "test_bill.png"
    assert len(result.transactions) == 1
    assert result.transactions[0].merchant == "测试商户"
    assert result.transactions[0].amount == 45.0


@patch('services.vision_ocr_service.OpenAI')
def test_process_files_vision_ocr_returns_empty(mock_openai):
    """测试Vision OCR无法识别时返回空列表"""
    # Mock返回空数组
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '[]'
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    from io import BytesIO
    fake_file = BytesIO(b'fake_image_data')
    fake_file.name = "empty_bill.png"

    service = OCRService()
    results = service.process_files([fake_file])

    # 验证：返回结果但transactions为空
    assert len(results) == 1
    assert len(results[0].transactions) == 0


@patch('services.vision_ocr_service.OpenAI')
def test_process_files_vision_ocr_handles_json_error(mock_openai):
    """测试Vision OCR返回无效JSON时的容错"""
    # Mock返回无效JSON
    mock_response = MagicMock()
    mock_response.choices[0].message.content = 'invalid json response'
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    from io import BytesIO
    fake_file = BytesIO(b'fake_image_data')
    fake_file.name = "bad_response.png"

    service = OCRService()
    results = service.process_files([fake_file])

    # 验证：容错，返回空transactions
    assert len(results) == 1
    assert len(results[0].transactions) == 0


@patch('services.vision_ocr_service.OpenAI')
def test_process_files_vision_ocr_api_exception(mock_openai):
    """测试Vision OCR API异常时的容错"""
    # Mock API抛出异常
    mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")

    from io import BytesIO
    fake_file = BytesIO(b'fake_image_data')
    fake_file.name = "api_error.png"

    service = OCRService()
    results = service.process_files([fake_file])

    # 验证：异常被捕获，返回失败结果
    assert len(results) == 1
    assert "识别失败" in results[0].text or "API Error" in results[0].text
```

#### Step 3: 保留并修复通用测试

保留并修复这个测试（它测试通用错误处理）:

```python
def test_process_files_empty_file():
    """测试空文件处理"""
    from io import BytesIO
    empty_file = BytesIO(b'')
    empty_file.name = "empty.png"

    service = OCRService()
    results = service.process_files([empty_file])

    # 空文件应被跳过
    assert len(results) == 0
```

### 验收标准

- [ ] 删除了3个过时测试
- [ ] 添加了4个新Vision OCR测试
- [ ] 所有测试通过: `pytest tests/test_ocr_service.py -v`
- [ ] 测试覆盖Vision OCR成功、失败、容错场景

---

## 任务2: Vision OCR进度反馈 🟠

### 目标

当用户上传账单图片时，实时显示识别进度，减少等待焦虑。

### 当前体验问题

```python
# 当前代码（pages/bill_upload.py:239）
with st.spinner(i18n.t("bill_upload.spinner")):  # 只显示"识别中..."
    results = ocr_service.process_files(uploaded_files)
```

**问题**:
- 用户看到spinner转圈，不知道发生了什么
- Vision OCR耗时2-5秒，无反馈让人焦虑
- 无法知道进度（是在识别第1张还是第5张？）

### 优化方案

**策略**: 使用Streamlit的`st.status`显示流式进度。

**文件**: `pages/bill_upload.py`

**实现**:

```python
# 替换原有的spinner（约在第239行）

# OLD:
# with st.spinner(i18n.t("bill_upload.spinner")):
#     results = ocr_service.process_files(uploaded_files)

# NEW:
with st.status(i18n.t("bill_upload.spinner"), expanded=True) as status:
    results = []
    total_files = len(uploaded_files)

    for idx, file in enumerate(uploaded_files, 1):
        # 显示当前处理的文件
        st.write(f"📄 {i18n.t('bill_upload.processing_file', current=idx, total=total_files, filename=file.name)}")

        # 处理单个文件
        try:
            file_results = ocr_service.process_files([file])
            results.extend(file_results)

            # 显示识别结果
            if file_results and file_results[0].transactions:
                txn_count = len(file_results[0].transactions)
                st.success(f"✅ {i18n.t('bill_upload.recognized', count=txn_count)}")
            else:
                st.warning(f"⚠️ {i18n.t('bill_upload.no_transactions')}")
        except Exception as e:
            st.error(f"❌ {i18n.t('bill_upload.error', error=str(e))}")

    # 完成状态
    status.update(label=i18n.t("bill_upload.completed"), state="complete", expanded=False)
```

### 需要添加的i18n字符串

**文件**: `locales/zh_CN.json`

在`bill_upload`节点下添加：
```json
{
  "bill_upload": {
    "processing_file": "正在处理第 {current}/{total} 个文件：{filename}",
    "recognized": "识别到 {count} 笔交易",
    "no_transactions": "未识别到交易记录",
    "completed": "✅ 所有文件处理完成"
  }
}
```

**文件**: `locales/en_US.json`

```json
{
  "bill_upload": {
    "processing_file": "Processing file {current}/{total}: {filename}",
    "recognized": "Recognized {count} transaction(s)",
    "no_transactions": "No transactions found",
    "completed": "✅ All files processed"
  }
}
```

### 验收标准

- [ ] 上传多个文件时，逐个显示进度
- [ ] 每个文件显示识别结果（成功/失败）
- [ ] 完成后状态自动折叠
- [ ] 中英文提示正确显示

---

## 任务3: 首页进度引导 🟡

### 目标

在首页显示用户完成进度，引导下一步操作，降低新用户学习成本。

### 当前体验问题

**首页代码**（`app.py:33-50`）只显示异常提醒，新用户不知道从哪里开始：
```python
def _render_home() -> None:
    st.title("WeFinance Copilot")
    st.subheader(i18n.t("app.subtitle"))

    # 只有异常提醒，没有引导
    if active_anomalies:
        st.error(...)
```

### 优化方案

**策略**: 添加进度卡片，显示4步流程的完成状态。

**文件**: `app.py`

**实现**:

#### Step 1: 添加进度检查函数

在`app.py`顶部添加：
```python
def _check_user_progress() -> dict:
    """检查用户完成进度"""
    return {
        "has_transactions": bool(st.session_state.get("transactions")),
        "has_insights": bool(st.session_state.get("analysis_summary")),
        "has_chat": bool(st.session_state.get("chat_history")),
        "has_recommendations": bool(st.session_state.get("product_recommendations")),
    }
```

#### Step 2: 修改`_render_home()`函数

在异常提醒之后，添加进度卡片：
```python
def _render_home() -> None:
    i18n = get_i18n()
    st.title("WeFinance Copilot")
    st.subheader(i18n.t("app.subtitle"))

    # 现有的异常提醒代码保持不变
    active_anomalies = session_utils.get_active_anomalies()
    if active_anomalies:
        st.error(i18n.t("app.anomaly_warning"))
        # ... 现有代码

    # 新增：进度引导
    st.markdown("---")
    st.subheader(i18n.t("app.progress_title"))

    progress = _check_user_progress()

    # 定义4步流程
    steps = [
        ("upload", i18n.t("app.step_upload"), "bill_upload", progress["has_transactions"]),
        ("insights", i18n.t("app.step_insights"), "spending_insights", progress["has_insights"]),
        ("chat", i18n.t("app.step_chat"), "advisor_chat", progress["has_chat"]),
        ("invest", i18n.t("app.step_invest"), "investment_recs", progress["has_recommendations"]),
    ]

    # 渲染进度卡片
    for step_id, step_name, page_name, is_done in steps:
        col1, col2 = st.columns([0.1, 0.9])
        with col1:
            st.markdown("✅" if is_done else "⭕")
        with col2:
            st.markdown(f"**{step_name}**")
            if not is_done:
                st.caption(i18n.t(f"app.hint_{step_id}"))
                # 只为第一个未完成步骤显示按钮
                if st.button(i18n.t("app.btn_start"), key=f"start_{step_id}"):
                    st.session_state["selected_page"] = page_name
                    st.rerun()
                break  # 只显示到第一个未完成步骤
```

#### Step 3: 添加i18n字符串

**文件**: `locales/zh_CN.json`

在`app`节点下添加：
```json
{
  "app": {
    "progress_title": "📋 快速开始",
    "step_upload": "上传账单",
    "step_insights": "查看消费分析",
    "step_chat": "咨询AI顾问",
    "step_invest": "获取投资建议",
    "hint_upload": "上传您的账单图片，开始智能分析",
    "hint_insights": "查看您的消费趋势和洞察",
    "hint_chat": "向AI顾问提问您的理财问题",
    "hint_invest": "获取个性化投资建议",
    "btn_start": "开始 →"
  }
}
```

**文件**: `locales/en_US.json`

```json
{
  "app": {
    "progress_title": "📋 Quick Start",
    "step_upload": "Upload Bills",
    "step_insights": "View Spending Insights",
    "step_chat": "Chat with AI Advisor",
    "step_invest": "Get Investment Recommendations",
    "hint_upload": "Upload your bill images to start smart analysis",
    "hint_insights": "View your spending trends and insights",
    "hint_chat": "Ask AI advisor about your financial questions",
    "hint_invest": "Get personalized investment recommendations",
    "btn_start": "Start →"
  }
}
```

### 验收标准

- [ ] 首页显示4步进度卡片
- [ ] 已完成步骤显示✅，未完成显示⭕
- [ ] 只显示到第一个未完成步骤
- [ ] 点击"开始"按钮正确跳转
- [ ] 中英文提示正确显示

---

## 任务4: 全局Budget设置 🟢

### 目标

将Budget输入统一到侧边栏，避免在Advisor Chat和其他页面重复输入。

### 当前问题

**Advisor Chat**（`pages/advisor_chat.py:30-38`）有budget输入：
```python
budget = st.number_input(
    i18n.t("chat.budget_label"),
    min_value=0.0,
    value=float(st.session_state["monthly_budget"]),
    step=500.0,
)
st.session_state["monthly_budget"] = budget
```

**问题**: 用户需要在每个页面都设置budget，重复劳动。

### 优化方案

**策略**: 将budget输入移到侧边栏，全局可见。

**文件**: `app.py`

**实现**:

在`main()`函数中，sidebar代码之后添加：
```python
def main() -> None:
    init_session_state()
    i18n = get_i18n()

    # 现有sidebar代码...
    with st.sidebar:
        # ... locale切换等代码

        # 新增：全局Budget设置
        st.markdown("---")
        st.markdown(f"**{i18n.t('app.global_settings')}**")

        budget = st.number_input(
            i18n.t("app.monthly_budget"),
            min_value=0.0,
            value=float(st.session_state.get("monthly_budget", 5000.0)),
            step=500.0,
            help=i18n.t("app.budget_help"),
            key="global_budget_input"
        )
        st.session_state["monthly_budget"] = budget
        st.caption(f"{i18n.t('app.current_budget')}: ¥{budget:,.0f}")
```

### 需要移除的代码

**文件**: `pages/advisor_chat.py`

删除或注释掉budget输入部分（第29-38行）：
```python
# 删除这部分代码：
# col_budget, col_hint = st.columns([1, 2])
# with col_budget:
#     budget = st.number_input(...)
#     st.session_state["monthly_budget"] = budget
```

改为直接从session读取：
```python
# 新代码：
budget = st.session_state.get("monthly_budget", 5000.0)
st.info(i18n.t("chat.current_budget", budget=f"¥{budget:,.0f}"))
```

### 需要添加的i18n字符串

**文件**: `locales/zh_CN.json`

```json
{
  "app": {
    "global_settings": "⚙️ 全局设置",
    "monthly_budget": "月度预算（元）",
    "budget_help": "设置您的月度预算，所有功能将自动使用此值",
    "current_budget": "当前预算"
  },
  "chat": {
    "current_budget": "使用预算：{budget}"
  }
}
```

**文件**: `locales/en_US.json`

```json
{
  "app": {
    "global_settings": "⚙️ Global Settings",
    "monthly_budget": "Monthly Budget (CNY)",
    "budget_help": "Set your monthly budget, all features will use this value",
    "current_budget": "Current Budget"
  },
  "chat": {
    "current_budget": "Using budget: {budget}"
  }
}
```

### 验收标准

- [ ] 侧边栏显示Budget输入框
- [ ] Advisor Chat页面移除Budget输入，显示当前使用的Budget
- [ ] Budget值在所有页面共享
- [ ] 修改Budget立即生效
- [ ] 中英文提示正确显示

---

## 测试策略

### 单元测试

对于新增的功能，遵循以下测试策略：

1. **任务1（修复测试）**:
   - 直接运行`pytest tests/test_ocr_service.py -v`验证
   - 确保所有Vision OCR测试通过

2. **任务2-4（UI优化）**:
   - UI改动主要靠手动测试
   - 确保不破坏现有功能

### 手动测试清单

完成所有任务后，执行以下手动测试：

```bash
# 1. 启动应用
streamlit run app.py --server.port 8501

# 2. 测试流程
- [ ] 打开首页，看到进度卡片
- [ ] 侧边栏看到Budget设置
- [ ] 点击"上传账单"，上传测试图片
- [ ] 观察实时进度显示（逐文件）
- [ ] 识别完成后，进度卡片更新
- [ ] 点击"查看消费分析"，使用全局Budget
- [ ] 点击"AI顾问"，确认Budget显示正确
- [ ] 切换英文，验证所有新增文案翻译正确
```

---

## 技术细节与注意事项

### 关于st.status

Streamlit的`st.status`从1.28.0开始支持，用法：
```python
with st.status("Processing...", expanded=True) as status:
    st.write("Step 1")
    # ... do work
    status.update(label="Done!", state="complete")
```

**状态**: `running`（默认）、`complete`、`error`

### 关于session_state一致性

**重要**: 所有session_state修改必须通过`utils/session.py`的helper函数，避免：
```python
# WRONG:
st.session_state["monthly_budget"] = 6000

# CORRECT:
from utils.session import set_monthly_budget  # 如果有这个函数
set_monthly_budget(6000)
```

如果`utils/session.py`没有`set_monthly_budget`函数，直接修改是可以的（因为budget是简单值，无需验证）。

### 关于i18n格式化

使用参数化字符串：
```python
# 在locales/zh_CN.json:
{
  "message": "识别到 {count} 笔交易"
}

# 在代码中:
i18n.t("message", count=5)  # 输出: "识别到 5 笔交易"
```

---

## 优先级总结

### 必须完成（比赛前）:
1. ✅ **任务1**: 修复5个失败测试（1小时）
2. ✅ **任务2**: Vision OCR进度反馈（30分钟）

### 建议完成（提升UX）:
3. 🟡 **任务3**: 首页进度引导（1小时）
4. 🟡 **任务4**: 全局Budget设置（20分钟）

### 总时间估算: 2.5-3小时

---

## 验收总清单

完成所有任务后，确保：

- [ ] 所有pytest测试通过（22+新增）
- [ ] Vision OCR上传有实时进度显示
- [ ] 首页有进度卡片引导
- [ ] Budget在侧边栏全局设置
- [ ] 中英文所有新增字符串翻译完整
- [ ] 手动测试流程通过
- [ ] 应用正常运行，无报错

---

## 参考文件

- UX/UI分析: `UX_UI_OPTIMIZATION_PLAN.md`
- 项目规则: `.claude/PROJECT_RULES.md`
- 架构文档: `CLAUDE.md`
- 现有测试: `tests/test_ocr_service.py`
- Vision OCR实现: `services/vision_ocr_service.py`
- i18n引擎: `utils/i18n.py`

---

## 遇到问题怎么办

### 如果测试仍然失败
1. 检查mock是否正确（OpenAI客户端路径）
2. 查看错误日志，确认是否是import问题
3. 运行单个测试调试: `pytest tests/test_ocr_service.py::test_name -v -s`

### 如果UI不显示
1. 检查i18n字符串是否添加到两个locale文件
2. 确认key路径正确（如`app.progress_title`）
3. 使用`st.write(st.session_state)`调试状态

### 如果进度卡片逻辑错误
1. 在`_check_user_progress()`添加debug输出
2. 确认session_state的key名称正确
3. 测试不同场景（无数据、部分数据、全部数据）

---

## Good Luck! 🚀

这些任务会显著提升用户体验，同时修复测试保证代码质量。完成后，WeFinance Copilot将更加易用和稳定！
