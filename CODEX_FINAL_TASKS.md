# Codex最终任务 - 修复最后的测试 + UX优化

## 当前状态总结 ✅

**测试进展**:
- ✅ Vision OCR tests: 3/3 passing (`tests/test_ocr_service.py`)
- ✅ 其他测试: 20/21 passing
- ❌ **仅剩1个失败**: `tests/test_integration.py::test_error_handling_messages`

**失败原因**:
```
AttributeError: <services.ocr_service.OCRService object> has no attribute '_lazy_engine'
```

测试代码在第259行尝试mock `_lazy_engine`，但Vision OCR重构后这个属性已不存在。

---

## 🔴 任务1: 修复最后的失败测试（15分钟）

### 问题分析

**文件**: `tests/test_integration.py:250-260`

**当前代码**（第259行）:
```python
def test_error_handling_messages(monkeypatch):
    """Ensure OCR/structuring services return user-friendly messages on failure."""

    def _mock_paddle(*_, **__):
        raise RuntimeError("paddle failure")

    ocr = OCRService()
    monkeypatch.setattr(
        ocr, "_lazy_engine", lambda: Mock(ocr=Mock(side_effect=_mock_paddle))
    )  # ❌ _lazy_engine 不存在了
```

**问题**: Vision OCR重构后，`OCRService`不再有`_lazy_engine`属性（那是PaddleOCR的）。

### 解决方案

**策略**: 直接mock `_vision_ocr`来测试错误处理。

**修改文件**: `tests/test_integration.py`

**替换test_error_handling_messages函数**:

```python
def test_error_handling_messages(monkeypatch):
    """Ensure Vision OCR service returns user-friendly messages on failure."""
    from unittest.mock import Mock
    from services.vision_ocr_service import VisionOCRService

    # 创建OCRService实例
    ocr = OCRService()

    # Mock VisionOCRService使其抛出异常
    mock_vision = Mock(spec=VisionOCRService)
    mock_vision.extract_transactions_from_image.side_effect = RuntimeError("Vision API failure")

    # 替换_vision_ocr属性
    monkeypatch.setattr(ocr, "_vision_ocr", mock_vision)

    # 准备测试文件
    from io import BytesIO
    fake_file = BytesIO(b"fake-image")
    fake_file.name = "test.png"

    # 执行并验证
    results = ocr.process_files([fake_file])

    assert len(results) == 1
    record = results[0]
    assert record.filename == "test.png"
    assert record.transactions == []  # 失败时返回空列表
    assert "识别失败" in record.text or "Vision API failure" in record.text
```

### 验收标准

- [ ] 运行 `pytest tests/test_integration.py::test_error_handling_messages -v` 通过
- [ ] 运行 `pytest tests/ -q` 显示 21/21 passing
- [ ] 测试验证了Vision OCR错误时的友好提示

---

## 🟠 任务2: Vision OCR进度反馈UI（30分钟）

### 目标

用户上传多个账单图片时，显示实时识别进度，减少等待焦虑。

### 实现

**文件**: `pages/bill_upload.py`

**定位**: 找到第239行左右的代码：
```python
with st.spinner(i18n.t("bill_upload.spinner")):
    results = ocr_service.process_files(uploaded_files)
```

**替换为**:
```python
# 使用st.status显示进度
with st.status(i18n.t("bill_upload.processing"), expanded=True) as status:
    results = []
    total_files = len(uploaded_files)

    for idx, uploaded_file in enumerate(uploaded_files, 1):
        # 显示当前文件
        st.write(f"📄 {i18n.t('bill_upload.processing_file', current=idx, total=total_files, filename=uploaded_file.name)}")

        # 处理单个文件
        try:
            file_results = ocr_service.process_files([uploaded_file])
            results.extend(file_results)

            # 显示识别结果
            if file_results and file_results[0].transactions:
                txn_count = len(file_results[0].transactions)
                st.success(f"✅ {i18n.t('bill_upload.recognized', count=txn_count)}")
            else:
                st.warning(f"⚠️ {i18n.t('bill_upload.no_transactions_found')}")

        except Exception as e:
            st.error(f"❌ {i18n.t('bill_upload.file_error', filename=uploaded_file.name, error=str(e))}")
            # 继续处理其他文件
            continue

    # 完成
    status.update(label=i18n.t("bill_upload.all_completed"), state="complete", expanded=False)
```

### 添加i18n字符串

**文件**: `locales/zh_CN.json`

在`bill_upload`节点添加：
```json
{
  "bill_upload": {
    "processing": "正在处理账单...",
    "processing_file": "正在处理第 {current}/{total} 个文件：{filename}",
    "recognized": "识别到 {count} 笔交易",
    "no_transactions_found": "未识别到交易记录",
    "file_error": "文件 {filename} 处理失败：{error}",
    "all_completed": "✅ 所有文件处理完成"
  }
}
```

**文件**: `locales/en_US.json`

```json
{
  "bill_upload": {
    "processing": "Processing bills...",
    "processing_file": "Processing file {current}/{total}: {filename}",
    "recognized": "Recognized {count} transaction(s)",
    "no_transactions_found": "No transactions found",
    "file_error": "File {filename} failed: {error}",
    "all_completed": "✅ All files processed"
  }
}
```

### 验收标准

- [ ] 上传单个文件：显示"正在处理第1/1个文件"
- [ ] 上传多个文件：逐个显示进度
- [ ] 识别成功：显示"✅ 识别到X笔交易"
- [ ] 识别失败：显示"⚠️ 未识别到交易记录"
- [ ] 完成后：状态自动折叠
- [ ] 中英文切换：所有文案正确显示

---

## 🟡 任务3: 首页进度引导（1小时）

### 目标

首页显示用户完成进度，引导下一步操作。

### 实现

**文件**: `app.py`

#### Step 1: 添加进度检查函数

在文件顶部（约第20行，`st.set_page_config`之后）添加：

```python
def _check_user_progress() -> dict:
    """检查用户在理财流程中的完成进度"""
    return {
        "has_transactions": bool(st.session_state.get("transactions")),
        "has_insights": bool(st.session_state.get("analysis_summary")),
        "has_chat": len(st.session_state.get("chat_history", [])) > 0,
        "has_recommendations": bool(st.session_state.get("product_recommendations")),
    }
```

#### Step 2: 修改`_render_home()`函数

找到`_render_home()`函数（约第33行），在异常提醒代码之后添加进度引导：

```python
def _render_home() -> None:
    """Render the landing page with quick project hints."""
    i18n = get_i18n()
    st.title("WeFinance Copilot")
    st.subheader(i18n.t("app.subtitle"))

    # ======== 现有的异常提醒代码保持不变 ========
    active_anomalies = session_utils.get_active_anomalies()
    anomaly_message = st.session_state.get("anomaly_message", "")

    if active_anomalies:
        st.error(i18n.t("app.anomaly_warning"))
        # ... 现有代码

    # ======== 新增：进度引导 ========
    st.markdown("---")
    st.subheader(i18n.t("app.progress_title"))
    st.caption(i18n.t("app.progress_subtitle"))

    progress = _check_user_progress()

    # 定义4步流程
    steps = [
        {
            "id": "upload",
            "name": i18n.t("app.step_upload"),
            "page": "账单上传",  # 对应侧边栏页面名称
            "hint": i18n.t("app.hint_upload"),
            "done": progress["has_transactions"]
        },
        {
            "id": "insights",
            "name": i18n.t("app.step_insights"),
            "page": "消费分析",
            "hint": i18n.t("app.hint_insights"),
            "done": progress["has_insights"]
        },
        {
            "id": "chat",
            "name": i18n.t("app.step_chat"),
            "page": "智能顾问对话",
            "hint": i18n.t("app.hint_chat"),
            "done": progress["has_chat"]
        },
        {
            "id": "invest",
            "name": i18n.t("app.step_invest"),
            "page": "投资推荐",
            "hint": i18n.t("app.hint_invest"),
            "done": progress["has_recommendations"]
        },
    ]

    # 渲染进度卡片
    for step in steps:
        col1, col2 = st.columns([0.08, 0.92])

        with col1:
            if step["done"]:
                st.markdown("✅")
            else:
                st.markdown("⭕")

        with col2:
            st.markdown(f"**{step['name']}**")

            if not step["done"]:
                st.caption(step["hint"])

                # 只为第一个未完成步骤显示按钮
                button_key = f"start_{step['id']}"
                if st.button(i18n.t("app.btn_start"), key=button_key, type="primary"):
                    # 设置选中页面（触发侧边栏导航）
                    st.session_state["selected_page"] = step["page"]
                    st.rerun()

                break  # 只显示到第一个未完成步骤
```

### 添加i18n字符串

**文件**: `locales/zh_CN.json`

在`app`节点添加：
```json
{
  "app": {
    "progress_title": "📋 快速开始",
    "progress_subtitle": "跟随引导完成您的理财规划",
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
    "progress_subtitle": "Follow the guide to complete your financial planning",
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
- [ ] 已完成步骤显示✅
- [ ] 未完成步骤显示⭕和提示文字
- [ ] 只显示到第一个未完成步骤
- [ ] 点击"开始"按钮跳转到对应页面
- [ ] 中英文切换正确

---

## 🟢 任务4: 全局Budget设置（20分钟）

### 目标

将Budget输入统一到侧边栏，避免重复输入。

### 实现

**文件**: `app.py`

#### Step 1: 在侧边栏添加Budget设置

找到`main()`函数中的侧边栏代码（约第250行），在locale切换之后添加：

```python
def main() -> None:
    init_session_state()
    i18n = get_i18n()

    with st.sidebar:
        # ======== 现有的locale切换代码保持不变 ========
        # ...

        # ======== 新增：全局Budget设置 ========
        st.markdown("---")
        st.markdown(f"**{i18n.t('app.global_settings')}**")

        current_budget = st.session_state.get("monthly_budget", 5000.0)

        budget = st.number_input(
            i18n.t("app.monthly_budget"),
            min_value=0.0,
            max_value=1000000.0,
            value=float(current_budget),
            step=500.0,
            help=i18n.t("app.budget_help"),
            key="global_budget_input"
        )

        # 更新session state
        st.session_state["monthly_budget"] = budget

        # 显示当前预算
        st.caption(f"💰 {i18n.t('app.current_budget', budget=f'¥{budget:,.0f}')}")
```

#### Step 2: 修改Advisor Chat页面

**文件**: `pages/advisor_chat.py`

找到第29-38行的budget输入代码，**删除或注释掉**：

```python
# 删除这部分代码（第29-38行）：
# col_budget, col_hint = st.columns([1, 2])
# with col_budget:
#     budget = st.number_input(
#         i18n.t("chat.budget_label"),
#         min_value=0.0,
#         value=float(st.session_state["monthly_budget"]),
#         step=500.0,
#         help=i18n.t("chat.budget_help"),
#     )
#     st.session_state["monthly_budget"] = budget
```

**替换为**（第29行位置）：

```python
# 从session读取budget（已在侧边栏设置）
budget = st.session_state.get("monthly_budget", 5000.0)

# 显示当前使用的budget
st.info(f"💰 {i18n.t('chat.using_budget', budget=f'¥{budget:,.0f}')}")

# 保留示例问题的列（现在占全宽）
st.markdown(
    "\n".join(
        [
            f"**{i18n.t('chat.sample_title')}**",
            f"- {i18n.t('chat.sample_q1')}",
            f"- {i18n.t('chat.sample_q2')}",
            f"- {i18n.t('chat.sample_q3')}",
            f"- {i18n.t('chat.sample_q4')}",
        ]
    )
)
```

### 添加i18n字符串

**文件**: `locales/zh_CN.json`

在`app`节点添加：
```json
{
  "app": {
    "global_settings": "⚙️ 全局设置",
    "monthly_budget": "月度预算（元）",
    "budget_help": "设置您的月度预算，所有功能将自动使用此值",
    "current_budget": "当前预算：{budget}"
  }
}
```

在`chat`节点添加：
```json
{
  "chat": {
    "using_budget": "使用预算：{budget}"
  }
}
```

**文件**: `locales/en_US.json`

```json
{
  "app": {
    "global_settings": "⚙️ Global Settings",
    "monthly_budget": "Monthly Budget (CNY)",
    "budget_help": "Set your monthly budget, all features will use this value automatically",
    "current_budget": "Current budget: {budget}"
  },
  "chat": {
    "using_budget": "Using budget: {budget}"
  }
}
```

### 验收标准

- [ ] 侧边栏显示Budget输入框
- [ ] Advisor Chat页面移除Budget输入
- [ ] Advisor Chat显示当前使用的Budget
- [ ] 修改侧边栏Budget，所有页面立即生效
- [ ] 中英文切换正确

---

## 总体验收清单

完成所有任务后，执行以下验收：

### 测试
```bash
# 1. 运行所有测试
pytest tests/ -v

# 预期结果：21 passed
```

### 手动测试流程
```bash
# 2. 启动应用
streamlit run app.py --server.port 8501
```

**测试步骤**:
- [ ] 打开首页，看到进度卡片（4步，都是⭕）
- [ ] 侧边栏看到Budget设置（默认¥5,000）
- [ ] 点击"开始 →"，跳转到"账单上传"
- [ ] 上传测试图片：`assets/sample_bills/bill_dining.png`
- [ ] 观察实时进度："正在处理第1/1个文件..."
- [ ] 识别完成显示："✅ 识别到4笔交易"
- [ ] 返回首页，进度卡片更新（第1步✅）
- [ ] 修改侧边栏Budget为¥8,000
- [ ] 进入"智能顾问对话"，显示"使用预算：¥8,000"
- [ ] 切换英文，所有新增文案正确显示

### 代码质量
- [ ] 所有新增代码有中文注释（关键逻辑）
- [ ] i18n字符串完整（中英文对应）
- [ ] 无console错误或警告
- [ ] 代码格式化：`black .`

---

## 时间估算

- 任务1（修复测试）: 15分钟
- 任务2（进度反馈）: 30分钟
- 任务3（首页引导）: 1小时
- 任务4（全局Budget）: 20分钟

**总计**: 约2小时

---

## 技术提示

### st.status用法（任务2）

```python
with st.status("Processing...", expanded=True) as status:
    # 处理逻辑
    st.write("Step 1")
    st.write("Step 2")

    # 完成时更新状态
    status.update(label="Done!", state="complete", expanded=False)
```

状态: `running`（默认）、`complete`、`error`

### session_state页面跳转（任务3）

Streamlit没有内置的页面导航API，我们通过设置`selected_page`来触发侧边栏的页面切换：

```python
if st.button("开始"):
    st.session_state["selected_page"] = "账单上传"  # 页面名称必须与侧边栏一致
    st.rerun()  # 重新渲染
```

**注意**: 页面名称必须与`PAGES`字典的key完全一致（见`app.py`约第273行）。

### i18n参数化字符串

```python
# 在locales/zh_CN.json:
{
  "message": "识别到 {count} 笔交易"
}

# 在代码中:
i18n.t("message", count=5)  # 输出: "识别到 5 笔交易"
```

---

## 遇到问题？

### 如果测试仍然失败
1. 确认mock路径正确：`monkeypatch.setattr(ocr, "_vision_ocr", mock_vision)`
2. 检查import: `from services.vision_ocr_service import VisionOCRService`
3. 运行单个测试调试: `pytest tests/test_integration.py::test_error_handling_messages -v -s`

### 如果st.status不工作
1. 确认Streamlit版本 >= 1.28.0: `pip show streamlit`
2. 如果版本过低，升级: `pip install --upgrade streamlit`

### 如果页面跳转不工作
1. 检查`selected_page`的值是否与`PAGES`字典的key匹配
2. 使用`st.write(st.session_state)`调试状态
3. 确认调用了`st.rerun()`

---

## 完成后的下一步

完成这些任务后，WeFinance Copilot将：
- ✅ 所有测试通过（21/21）
- ✅ Vision OCR有实时进度反馈
- ✅ 首页有清晰的用户引导
- ✅ Budget统一管理，无重复输入

**还需要手动完成的**:
1. UI截图（需要GUI环境）
2. 测试覆盖率验证（需要pytest-cov）
3. LLM timeout处理（可选，P2优先级）

Good luck! 🚀
