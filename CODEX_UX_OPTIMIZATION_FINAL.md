# Codex - UX优化最终冲刺任务

## 🎉 当前成果回顾

**已完成** ✅:
- ✅ **双语支持完善**: 所有OCR错误、UI反馈都已i18n化
- ✅ **手动输入优化**: Tab式UI（JSON/CSV/表格编辑器），零代码门槛
- ✅ **测试全绿**: 21/21 passing (9.54s)
- ✅ **代码质量**: 所有主要模块已双语化

**技术栈确认**:
- Streamlit: 1.51.0 ✅ (支持st.status)
- Python: 3.12.3
- Vision OCR: 100%识别率
- 测试框架: pytest

---

## 🎯 剩余核心任务（按优先级）

### 🔴 P0: Vision OCR实时进度反馈（30分钟）

**为什么是P0**:
- Vision OCR耗时2-5秒，用户等待时需要反馈
- 直接影响demo演示体验
- 实现成本低，效果显著

### 🟠 P1: 首页进度引导（1小时）

**为什么是P1**:
- 新用户不知道从哪里开始
- 降低学习成本，提升首次使用体验
- 体现产品的用户导向设计

### 🟡 P2: 全局Budget设置（20分钟）

**为什么是P2**:
- 减少重复输入
- 提升操作效率
- 符合DRY原则

---

## 🔴 任务1: Vision OCR实时进度反馈

### 目标

上传多个账单图片时，显示逐文件的识别进度，让用户知道发生了什么。

### 当前体验

**文件**: `pages/bill_upload.py`

**当前代码**（约第239行）:
```python
with st.spinner(i18n.t("bill_upload.spinner")):
    results = ocr_service.process_files(uploaded_files)
```

**问题**:
- 只有spinner转圈，用户不知道进度
- 上传5张图片，等待10-25秒却无反馈
- 无法知道是在处理哪一张

### 优化实现

**使用st.status显示流式进度**

**找到代码位置**: `pages/bill_upload.py:236-244`（处理上传文件的部分）

**完整替换为**:

```python
# 使用st.status显示实时进度（支持多文件）
with st.status(i18n.t("bill_upload.processing_status"), expanded=True) as status:
    results = []
    total_files = len(uploaded_files)

    # 逐个处理文件
    for idx, uploaded_file in enumerate(uploaded_files, 1):
        # 显示当前处理的文件
        st.write(f"📄 {i18n.t('bill_upload.processing_file', current=idx, total=total_files, filename=uploaded_file.name)}")

        try:
            # 处理单个文件
            file_results = ocr_service.process_files([uploaded_file])
            results.extend(file_results)

            # 显示识别结果
            if file_results and file_results[0].transactions:
                txn_count = len(file_results[0].transactions)
                st.success(f"✅ {i18n.t('bill_upload.recognized_count', count=txn_count)}")

                # 预览前3笔交易
                for txn in file_results[0].transactions[:3]:
                    st.caption(f"  {txn.date} | {txn.merchant} | ¥{txn.amount:.2f}")

                if len(file_results[0].transactions) > 3:
                    st.caption(f"  ... {i18n.t('bill_upload.and_more', count=len(file_results[0].transactions)-3)}")
            else:
                st.warning(f"⚠️ {i18n.t('bill_upload.no_transactions_in_file')}")

        except Exception as e:
            st.error(f"❌ {i18n.t('bill_upload.file_process_error', filename=uploaded_file.name, error=str(e))}")
            # 继续处理下一个文件
            continue

    # 完成状态
    total_txn = sum(len(r.transactions) for r in results if r.transactions)
    status.update(
        label=i18n.t("bill_upload.all_files_processed", total=total_files, transactions=total_txn),
        state="complete",
        expanded=False
    )
```

### 添加i18n字符串

**文件**: `locales/zh_CN.json`

在`bill_upload`节点添加：
```json
{
  "bill_upload": {
    "processing_status": "正在处理账单文件...",
    "processing_file": "正在处理第 {current}/{total} 个文件：{filename}",
    "recognized_count": "识别到 {count} 笔交易",
    "and_more": "以及其他 {count} 笔",
    "no_transactions_in_file": "未识别到交易记录",
    "file_process_error": "文件 {filename} 处理失败：{error}",
    "all_files_processed": "✅ 完成！共处理 {total} 个文件，识别 {transactions} 笔交易"
  }
}
```

**文件**: `locales/en_US.json`

```json
{
  "bill_upload": {
    "processing_status": "Processing bill files...",
    "processing_file": "Processing file {current}/{total}: {filename}",
    "recognized_count": "Recognized {count} transaction(s)",
    "and_more": "and {count} more",
    "no_transactions_in_file": "No transactions found",
    "file_process_error": "Failed to process {filename}: {error}",
    "all_files_processed": "✅ Done! Processed {total} file(s), recognized {transactions} transaction(s)"
  }
}
```

### 验收标准

**手动测试**:
```bash
streamlit run app.py --server.port 8501
```

1. 进入"账单上传"页面
2. 上传单个图片（`assets/sample_bills/bill_dining.png`）
   - [ ] 显示："正在处理第1/1个文件：bill_dining.png"
   - [ ] 显示："✅ 识别到4笔交易"
   - [ ] 预览前3笔交易详情
3. 上传多个图片（3个sample bills）
   - [ ] 逐个显示处理进度："第1/3"、"第2/3"、"第3/3"
   - [ ] 每个文件显示识别结果
   - [ ] 完成后折叠，显示总计
4. 切换英文，验证所有提示翻译正确

---

## 🟠 任务2: 首页进度引导

### 目标

首页显示用户完成的进度（⭕/✅），引导下一步操作，降低新用户学习成本。

### 当前体验问题

**文件**: `app.py`

当前首页（`_render_home()`函数）只显示异常提醒，新用户打开应用后：
- ❌ 不知道从哪里开始
- ❌ 不清楚应用的完整流程
- ❌ 需要自己探索侧边栏

### 优化实现

#### Step 1: 添加进度检查函数

在`app.py`顶部（`st.set_page_config`之后，约第32行）添加：

```python
def _check_user_progress() -> dict:
    """检查用户在理财流程中的完成进度

    Returns:
        dict: 包含4个步骤完成状态的字典
    """
    return {
        "has_transactions": bool(st.session_state.get("transactions")),
        "has_insights": bool(st.session_state.get("analysis_summary")),
        "has_chat": len(st.session_state.get("chat_history", [])) > 0,
        "has_recommendations": bool(st.session_state.get("product_recommendations")),
    }
```

#### Step 2: 修改首页渲染函数

找到`_render_home()`函数（约第37行），在异常提醒代码**之后**添加进度引导：

```python
def _render_home() -> None:
    """Render the landing page with progress guide and anomaly alerts."""
    i18n = get_i18n()
    st.title("WeFinance Copilot")
    st.subheader(i18n.t("app.subtitle"))

    # ============ 现有的异常提醒代码（保持不变）============
    active_anomalies = session_utils.get_active_anomalies()
    anomaly_message = st.session_state.get("anomaly_message", "")

    if active_anomalies:
        st.error(i18n.t("app.anomaly_warning"))
        for anomaly in active_anomalies[:3]:
            # ... 现有代码保持不变

    # ============ 新增：进度引导卡片 ============
    st.markdown("---")
    st.subheader(i18n.t("app.progress_guide_title"))
    st.caption(i18n.t("app.progress_guide_subtitle"))

    progress = _check_user_progress()

    # 定义4步理财流程
    steps = [
        {
            "id": "upload",
            "name": i18n.t("app.step_upload_bills"),
            "page_key": "账单上传",  # 对应PAGES字典的key
            "hint": i18n.t("app.hint_upload_bills"),
            "done": progress["has_transactions"],
            "icon": "📸"
        },
        {
            "id": "insights",
            "name": i18n.t("app.step_view_insights"),
            "page_key": "消费分析",
            "hint": i18n.t("app.hint_view_insights"),
            "done": progress["has_insights"],
            "icon": "📊"
        },
        {
            "id": "chat",
            "name": i18n.t("app.step_chat_advisor"),
            "page_key": "智能顾问对话",
            "hint": i18n.t("app.hint_chat_advisor"),
            "done": progress["has_chat"],
            "icon": "💬"
        },
        {
            "id": "invest",
            "name": i18n.t("app.step_get_recommendations"),
            "page_key": "投资推荐",
            "hint": i18n.t("app.hint_get_recommendations"),
            "done": progress["has_recommendations"],
            "icon": "💰"
        },
    ]

    # 渲染进度卡片
    for step in steps:
        col1, col2, col3 = st.columns([0.08, 0.8, 0.12])

        with col1:
            # 完成状态图标
            if step["done"]:
                st.markdown("✅")
            else:
                st.markdown("⭕")

        with col2:
            # 步骤名称和提示
            st.markdown(f"{step['icon']} **{step['name']}**")

            if not step["done"]:
                st.caption(step["hint"])

        with col3:
            # 只为第一个未完成步骤显示按钮
            if not step["done"]:
                button_key = f"goto_{step['id']}"
                if st.button(i18n.t("app.btn_go"), key=button_key, type="primary"):
                    # 设置选中页面（通过侧边栏导航机制）
                    st.session_state["selected_page"] = step["page_key"]
                    st.rerun()

                # 只显示第一个未完成步骤的按钮
                break

    # 如果全部完成，显示鼓励信息
    if all(step["done"] for step in steps):
        st.success(i18n.t("app.all_steps_completed"))
        st.balloons()  # 庆祝动画
```

### 添加i18n字符串

**文件**: `locales/zh_CN.json`

在`app`节点添加：
```json
{
  "app": {
    "progress_guide_title": "📋 快速开始指南",
    "progress_guide_subtitle": "跟随以下步骤完成您的智能理财规划",
    "step_upload_bills": "上传账单",
    "step_view_insights": "查看消费分析",
    "step_chat_advisor": "咨询AI顾问",
    "step_get_recommendations": "获取投资建议",
    "hint_upload_bills": "上传您的账单图片，AI将自动识别交易记录",
    "hint_view_insights": "查看您的消费趋势、分类统计和异常提醒",
    "hint_chat_advisor": "向AI顾问提问您的理财问题，获取个性化建议",
    "hint_get_recommendations": "完成风险评估，获取定制化投资组合建议",
    "btn_go": "开始 →",
    "all_steps_completed": "🎉 恭喜！您已完成所有理财规划步骤"
  }
}
```

**文件**: `locales/en_US.json`

```json
{
  "app": {
    "progress_guide_title": "📋 Quick Start Guide",
    "progress_guide_subtitle": "Follow these steps to complete your smart financial planning",
    "step_upload_bills": "Upload Bills",
    "step_view_insights": "View Spending Insights",
    "step_chat_advisor": "Chat with AI Advisor",
    "step_get_recommendations": "Get Investment Recommendations",
    "hint_upload_bills": "Upload your bill images, AI will recognize transactions automatically",
    "hint_view_insights": "View your spending trends, category stats, and anomaly alerts",
    "hint_chat_advisor": "Ask AI advisor about your financial questions and get personalized advice",
    "hint_get_recommendations": "Complete risk assessment and get customized investment portfolio",
    "btn_go": "Start →",
    "all_steps_completed": "🎉 Congratulations! You've completed all financial planning steps"
  }
}
```

### 验收标准

**手动测试**:

1. **初始状态**（无任何数据）:
   - [ ] 首页显示4步进度卡片，都是⭕
   - [ ] 只有"上传账单"显示"开始 →"按钮
   - [ ] 其他3步只显示提示文字，无按钮

2. **完成第1步**（上传账单后）:
   - [ ] 返回首页，"上传账单"显示✅
   - [ ] "查看消费分析"显示⭕ + "开始 →"按钮
   - [ ] 点击按钮跳转到"消费分析"页面

3. **完成所有步骤**:
   - [ ] 4步都显示✅
   - [ ] 显示"🎉 恭喜！您已完成所有理财规划步骤"
   - [ ] 触发气球动画

4. **中英文切换**:
   - [ ] 切换语言后，所有文案正确显示
   - [ ] 按钮点击跳转正常

---

## 🟡 任务3: 全局Budget设置

### 目标

将Budget输入统一到侧边栏，避免在Advisor Chat页面重复输入。

### 当前问题

**Advisor Chat**（`pages/advisor_chat.py`）有独立的budget输入框，用户需要：
- 在Advisor Chat输入budget
- 如果之后访问其他页面，可能需要重新设置
- 体验不一致，重复劳动

### 优化实现

#### Step 1: 在侧边栏添加全局Budget

**文件**: `app.py`

找到`main()`函数中的sidebar部分（约第260-280行，locale切换代码之后），添加：

```python
def main() -> None:
    init_session_state()
    i18n = get_i18n()

    with st.sidebar:
        # ============ 现有的locale切换代码（保持不变）============
        # ...

        # ============ 新增：全局Budget设置 ============
        st.markdown("---")
        st.markdown(f"**{i18n.t('app.global_settings_title')}**")

        # 获取当前budget
        current_budget = st.session_state.get("monthly_budget", 5000.0)

        # Budget输入框
        new_budget = st.number_input(
            i18n.t("app.monthly_budget_label"),
            min_value=0.0,
            max_value=1000000.0,
            value=float(current_budget),
            step=500.0,
            format="%.0f",
            help=i18n.t("app.monthly_budget_help"),
            key="global_budget_sidebar"
        )

        # 更新session state
        if new_budget != current_budget:
            st.session_state["monthly_budget"] = new_budget
            st.toast(i18n.t("app.budget_updated"))

        # 显示当前预算（带格式化）
        st.caption(f"💰 {i18n.t('app.current_budget_display', budget=f'¥{new_budget:,.0f}')}")
```

#### Step 2: 简化Advisor Chat的budget显示

**文件**: `pages/advisor_chat.py`

找到原有的budget输入代码（约第29-38行），**删除或注释掉**：

```python
# ============ 删除这部分（约29-38行）============
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

**替换为简化版**（约第29行位置）：

```python
# 从session读取全局budget（已在侧边栏设置）
budget = st.session_state.get("monthly_budget", 5000.0)

# 显示当前使用的budget（信息提示）
st.info(f"💰 {i18n.t('chat.current_budget_info', budget=f'¥{budget:,.0f}')}")

# 示例问题（现在占全宽，无需col_hint）
st.markdown("---")
st.markdown(
    "\n".join(
        [
            f"**{i18n.t('chat.sample_questions_title')}**",
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
    "global_settings_title": "⚙️ 全局设置",
    "monthly_budget_label": "月度预算（元）",
    "monthly_budget_help": "设置您的月度预算，AI顾问和分析功能将自动使用此值",
    "current_budget_display": "当前预算：{budget}",
    "budget_updated": "预算已更新"
  }
}
```

在`chat`节点添加：
```json
{
  "chat": {
    "current_budget_info": "使用月度预算：{budget}（可在侧边栏修改）",
    "sample_questions_title": "💡 示例问题"
  }
}
```

**文件**: `locales/en_US.json`

```json
{
  "app": {
    "global_settings_title": "⚙️ Global Settings",
    "monthly_budget_label": "Monthly Budget (CNY)",
    "monthly_budget_help": "Set your monthly budget, AI advisor and analysis features will use this value automatically",
    "current_budget_display": "Current budget: {budget}",
    "budget_updated": "Budget updated"
  },
  "chat": {
    "current_budget_info": "Using monthly budget: {budget} (change in sidebar)",
    "sample_questions_title": "💡 Sample Questions"
  }
}
```

### 验收标准

**手动测试**:

1. **侧边栏Budget设置**:
   - [ ] 侧边栏显示"⚙️ 全局设置"
   - [ ] 显示Budget输入框，默认¥5,000
   - [ ] 显示"当前预算：¥5,000"

2. **修改Budget**:
   - [ ] 修改为¥8,000
   - [ ] 显示toast提示"预算已更新"
   - [ ] 下方显示"当前预算：¥8,000"

3. **Advisor Chat集成**:
   - [ ] 进入"智能顾问对话"页面
   - [ ] 不再有budget输入框
   - [ ] 显示："使用月度预算：¥8,000（可在侧边栏修改）"
   - [ ] 对话功能正常，AI读取正确的budget

4. **跨页面一致性**:
   - [ ] 在侧边栏修改budget为¥10,000
   - [ ] 进入任意页面，budget保持¥10,000
   - [ ] 重启应用（st.rerun），budget保持

5. **中英文切换**:
   - [ ] 切换英文，所有文案正确
   - [ ] Budget格式化正确（¥符号保留）

---

## 总体验收清单

完成所有3个任务后，进行完整测试：

### 自动化测试
```bash
# 1. 运行所有测试
pytest tests/ -v

# 预期：21 passed（或更多，如果添加了新测试）
```

### 完整用户流程测试

```bash
# 2. 启动应用
streamlit run app.py --server.port 8501
```

**测试场景：新用户首次使用**

1. **首页**:
   - [ ] 看到4步进度卡片（都是⭕）
   - [ ] 侧边栏看到Budget设置（¥5,000）
   - [ ] 点击"上传账单 → 开始"

2. **上传账单**:
   - [ ] 上传`assets/sample_bills/bill_dining.png`
   - [ ] 看到实时进度："正在处理第1/1个文件..."
   - [ ] 显示："✅ 识别到4笔交易"
   - [ ] 预览前3笔交易
   - [ ] 完成后状态折叠

3. **返回首页**:
   - [ ] "上传账单"显示✅
   - [ ] "查看消费分析"显示⭕ + "开始 →"

4. **修改Budget**:
   - [ ] 在侧边栏改为¥8,000
   - [ ] 看到toast提示"预算已更新"

5. **AI顾问对话**:
   - [ ] 显示"使用月度预算：¥8,000"
   - [ ] 提问："我的餐饮支出高吗？"
   - [ ] AI回答引用了¥8,000预算

6. **完成所有步骤**:
   - [ ] 依次完成4步
   - [ ] 首页显示："🎉 恭喜！您已完成所有理财规划步骤"
   - [ ] 看到气球动画

7. **中英文切换**:
   - [ ] 切换English
   - [ ] 所有新增文案正确显示
   - [ ] 功能正常

### 代码质量检查

```bash
# 3. 代码格式化
black .

# 4. 代码检查
ruff check .
```

---

## 时间估算

- 任务1（进度反馈）: 30分钟
- 任务2（首页引导）: 1小时
- 任务3（全局Budget）: 20分钟
- 测试与调试: 30分钟

**总计**: 约2.5小时

---

## 技术提示

### st.status的注意事项

```python
# CORRECT: 先创建status，在with块内更新
with st.status("Processing...") as status:
    # 处理逻辑
    for i in range(10):
        st.write(f"Step {i}")

    # 完成时更新
    status.update(label="Done!", state="complete", expanded=False)

# WRONG: 在with块外更新
status = st.status("Processing...")
# ... 处理
status.update(...)  # ❌ 会报错
```

### 页面跳转机制

Streamlit没有直接的页面导航API，我们通过设置`selected_page`触发侧边栏的页面选择：

```python
# 在app.py中，PAGES字典定义了页面映射
PAGES = {
    "账单上传": bill_upload,
    "消费分析": spending_insights,
    # ...
}

# 在_render_home()中跳转
if st.button("开始"):
    st.session_state["selected_page"] = "账单上传"  # 必须与PAGES的key完全一致
    st.rerun()  # 触发重新渲染
```

**注意**: 页面名称必须与`PAGES`字典的key**完全匹配**（包括空格）。

### i18n参数化的格式

```python
# 在locales/zh_CN.json中：
{
  "message": "识别到 {count} 笔交易，总金额 {amount}"
}

# 在代码中：
i18n.t("message", count=5, amount="¥123.45")
# 输出："识别到 5 笔交易，总金额 ¥123.45"
```

**支持的格式化**:
- `{variable}` - 简单替换
- `{value:.2f}` - 数字格式化（在Python中先格式化，再传入）

---

## 遇到问题？

### 如果st.status不显示
1. 确认Streamlit版本: `streamlit --version` (需要 >= 1.28.0)
2. 检查代码缩进（必须在`with st.status(...) as status:`块内）
3. 确认`status.update()`在with块内调用

### 如果页面跳转不工作
1. 检查`selected_page`的值: `st.write(st.session_state.get("selected_page"))`
2. 确认值与`PAGES`字典的key完全匹配
3. 确认调用了`st.rerun()`

### 如果i18n字符串不显示
1. 检查JSON格式是否正确（逗号、引号）
2. 确认key路径正确（`app.progress_guide_title`不是`app.progressGuideTitle`）
3. 重启streamlit: `Ctrl+C` → `streamlit run app.py`

### 如果Budget不同步
1. 检查所有页面是否都从`st.session_state["monthly_budget"]`读取
2. 确认没有页面在本地覆盖budget值
3. 使用`st.write(st.session_state)`调试状态

---

## 完成后的状态

完成这3个任务后，WeFinance Copilot将：

**功能完整性** ✅:
- ✅ Vision OCR: 100%识别率 + 实时进度反馈
- ✅ 用户引导: 首页进度卡片 + 流程引导
- ✅ 体验优化: 全局Budget + 零重复输入
- ✅ 双语支持: 完整i18n（中英文）

**测试覆盖** ✅:
- ✅ 21+ tests passing
- ✅ 核心功能测试覆盖

**准备demo演示** ✅:
- ✅ 新用户友好（进度引导）
- ✅ 实时反馈（进度显示）
- ✅ 流畅体验（无重复输入）

**剩余工作** 📋:
- 📸 UI截图（需要GUI环境）
- 📊 测试覆盖率报告（需要pytest-cov）
- ⏰ LLM timeout处理（可选优化）

---

## Good Luck! 🚀

这些UX优化将显著提升用户体验，让WeFinance Copilot更加易用、专业、完整。完成后就可以准备demo演示了！

如有问题随时反馈，我会提供支持。💪
