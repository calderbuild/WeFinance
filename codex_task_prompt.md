# WeFinance Copilot - 下一阶段开发任务

## 当前项目状态

### 已完成工作
1. ✅ **Vision OCR升级完成** (100%识别率)
   - 替换PaddleOCR → GPT-4o Vision LLM
   - 文件: `services/vision_ocr_service.py` (145行, 4.7KB)
   - 测试: 11/11交易记录完美识别
   - 应用已集成并运行在 http://localhost:8501

2. ✅ **测试通过** (16/16 tests passing)
   - 覆盖率: 58%
   - 所有核心功能正常工作

3. ✅ **应用运行稳定**
   - Streamlit运行在port 8501
   - 所有4个页面正常访问
   - Vision OCR实时生效

## 待完成任务（按优先级排序）

### 🔴 P0: Task 8 - 添加UI截图到README（最高优先级）

**为什么优先**: 2025深圳国际金融科技大赛需要展示应用界面，截图是评委第一印象。

**任务详情**:
1. **截图数量**: 5-8张（必须包含中英文双语）
2. **存储位置**: `docs/screenshots/`
3. **命名规范**: `序号_页面名称_语言.png`
4. **必须截图的页面**:
   - 01_home_zh.png - 首页（中文）
   - 01_home_en.png - 首页（英文）
   - 02_advisor_chat_zh.png - 智能顾问对话（中文）
   - 02_advisor_chat_en.png - 智能顾问对话（英文）
   - 03_bill_upload_zh.png - **账单上传（Vision OCR核心功能）**
   - 03_bill_upload_en.png - 账单上传（英文）
   - 04_investment_recs_zh.png - 投资推荐
   - 05_spending_insights_zh.png - 消费分析

**重点关注**:
- **Vision OCR展示是核心亮点**:
  - 必须截图展示账单上传后的识别结果
  - 使用测试图片: `assets/sample_bills/bill_dining.png`
  - 显示完整的交易记录表格（日期、商户、分类、金额）
  - 在README中强调: "100%识别准确率，从PaddleOCR升级到GPT-4o Vision"

**截图步骤**:
```bash
# 1. 确认应用运行
curl http://localhost:8501

# 2. 浏览器访问
# 打开 http://localhost:8501

# 3. 切换语言
# 点击右上角语言切换按钮（中文/English）

# 4. 依次访问各页面截图
# - 首页（Home）
# - 智能顾问对话（Advisor Chat）
# - 账单上传（Bill Upload）← 重点
# - 投资推荐（Investment Recs）
# - 消费分析（Spending Insights）

# 5. 保存截图到 docs/screenshots/
```

**截图规范**:
- 格式: PNG
- 分辨率: 至少1280x720
- 完整UI: 去除浏览器地址栏
- 清晰度: 确保文字可读
- 文件大小: 单张<2MB

**更新README**:
完成截图后，需要在README.md和README_EN.md中添加：

```markdown
## 功能展示 / Features

### 首页 / Home
![首页](docs/screenshots/01_home_zh.png)

### 账单上传 - Vision OCR识别 / Bill Upload - Vision OCR
**核心亮点**: 使用GPT-4o Vision实现100%识别准确率
![账单上传](docs/screenshots/03_bill_upload_zh.png)

### 智能顾问对话 / Advisor Chat
![智能顾问](docs/screenshots/02_advisor_chat_zh.png)

... (其他页面)
```

**验收标准**:
- [ ] 8张截图已保存到`docs/screenshots/`
- [ ] 文件命名规范
- [ ] Vision OCR功能完整展示（必须有识别结果表格）
- [ ] README.md和README_EN.md已更新
- [ ] 截图在GitHub上正常加载

**详细指南**: 参考 `docs/screenshot_guide.md`

---

### 🟠 P1: Task 3 - 提升测试覆盖率（58% → 70%+）

**目标**: 将整体测试覆盖率从58%提升到70%以上。

**当前薄弱模块**:
1. `modules/chat_manager.py` - 48%覆盖率
2. `utils/session.py` - 36%覆盖率
3. `services/ocr_service.py` - Vision OCR新实现需要测试

**执行步骤**:

1. **安装工具**:
```bash
pip install pytest-cov
```

2. **查看当前覆盖率**:
```bash
pytest --cov=modules --cov=services --cov=utils --cov-report=term-missing
```

3. **分析缺失覆盖**:
```bash
pytest --cov=modules --cov=services --cov=utils --cov-report=html
# 打开 htmlcov/index.html 查看详细报告
```

4. **优先补充测试用例**:

**a) modules/chat_manager.py** (目标: 48% → 70%):
- 测试LLM fallback机制
- 测试历史对话缓存
- 测试白名单功能
- 测试错误处理路径

**b) utils/session.py** (目标: 36% → 60%):
- 测试session初始化
- 测试locale切换
- 测试数据持久化
- 测试异常处理

**c) services/vision_ocr_service.py** (新文件，需要创建测试):
```python
# tests/test_vision_ocr_service.py

import pytest
from services.vision_ocr_service import VisionOCRService
from unittest.mock import patch, MagicMock

def test_vision_ocr_init():
    """测试VisionOCRService初始化"""
    service = VisionOCRService(model="gpt-4o")
    assert service.model == "gpt-4o"

@patch('services.vision_ocr_service.OpenAI')
def test_extract_transactions_success(mock_openai):
    """测试成功提取交易记录"""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '''[
        {"date": "2025-11-01", "merchant": "测试商户", "category": "餐饮", "amount": 45.0}
    ]'''
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    service = VisionOCRService()
    image_bytes = b'fake_image_data'
    transactions = service.extract_transactions_from_image(image_bytes)

    assert len(transactions) == 1
    assert transactions[0].merchant == "测试商户"

@patch('services.vision_ocr_service.OpenAI')
def test_extract_transactions_json_error(mock_openai):
    """测试JSON解析失败的容错"""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = 'invalid json'
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    service = VisionOCRService()
    transactions = service.extract_transactions_from_image(b'fake')

    assert transactions == []  # 应返回空列表而非崩溃
```

5. **运行测试确保通过**:
```bash
pytest tests/ -v
```

6. **验证覆盖率达标**:
```bash
pytest --cov=modules --cov=services --cov=utils --cov-report=term
# 检查 TOTAL 是否 >= 70%
```

**验收标准**:
- [ ] 整体覆盖率 >= 70%
- [ ] 所有测试通过（16+ tests passing）
- [ ] Vision OCR有测试覆盖
- [ ] 核心模块覆盖率显著提升
- [ ] 生成HTML覆盖率报告

---

### 🟡 P2: Task 5 - 添加LLM超时处理（可选）

**目标**: 为所有LLM调用添加timeout保护，防止API超时导致应用卡死。

**影响模块**:
1. `services/langchain_agent.py` - LangChain调用
2. `modules/chat_manager.py` - 智能顾问对话
3. `services/vision_ocr_service.py` - Vision OCR调用

**实现方案**:

1. **修改 services/vision_ocr_service.py**:
```python
# 在 extract_transactions_from_image 方法中添加timeout
response = self.client.chat.completions.create(
    model=self.model,
    messages=[...],
    max_tokens=2000,
    temperature=0.0,
    timeout=30.0,  # 添加30秒超时
)
```

2. **修改 modules/chat_manager.py**:
```python
try:
    response = llm_client.chat.completions.create(
        model=model,
        messages=messages,
        timeout=30.0,  # 30秒超时
    )
except TimeoutError:
    # 使用现有fallback机制
    return fallback_response()
```

3. **修改 services/langchain_agent.py**:
```python
from langchain.llms import OpenAI

llm = OpenAI(
    model_name="gpt-4o",
    timeout=30,  # 30秒超时
)
```

**测试超时场景**:
```python
# tests/test_timeout.py

@patch('openai.OpenAI.chat.completions.create')
def test_vision_ocr_timeout(mock_create):
    """测试Vision OCR超时处理"""
    import time

    def slow_response(*args, **kwargs):
        time.sleep(35)  # 模拟超时
        raise TimeoutError("Request timeout")

    mock_create.side_effect = slow_response

    service = VisionOCRService()
    transactions = service.extract_transactions_from_image(b'fake')

    # 应返回空列表，而非崩溃
    assert transactions == []
```

**验收标准**:
- [ ] 所有LLM调用添加timeout=30
- [ ] 超时时触发现有fallback机制
- [ ] 添加超时测试用例
- [ ] 所有测试通过
- [ ] 应用运行稳定

---

## 技术上下文

### Vision OCR实现细节
- **文件**: `services/vision_ocr_service.py`
- **模型**: GPT-4o (通过newapi.deepwisdom.ai)
- **API Key**: 在.env文件中配置
- **测试图���**: `assets/sample_bills/*.png`
- **识别率**: 100% (11/11交易记录)
- **响应时间**: 约2-5秒/图片

### 依赖配置
```bash
# .env文件
OPENAI_API_KEY=sk-debs5nl5QYdw7AwnXMxHSzxVu1e15KzJsgwHK9Khp25STqMe
OPENAI_BASE_URL=https://newapi.deepwisdom.ai/v1
OPENAI_MODEL=gpt-4o
```

### 应用架构
```
app.py (Streamlit主入口)
├── pages/
│   ├── advisor_chat.py      # 智能顾问对话
│   ├── bill_upload.py        # 账单上传 (Vision OCR)
│   ├── investment_recs.py    # 投资推荐
│   └── spending_insights.py  # 消费分析
├── services/
│   ├── vision_ocr_service.py  # Vision OCR服务
│   ├── ocr_service.py         # OCR主接口
│   └── langchain_agent.py     # LangChain代理
├── modules/
│   ├── chat_manager.py        # 对话管理
│   └── analysis.py            # 数据分析
└── utils/
    └── session.py             # Session管理
```

## 工作流程建议

### Day 1: 截图任务（2-3小时）
1. 启动应用
2. 访问所有页面并截图
3. 保存到docs/screenshots/
4. 更新README.md和README_EN.md
5. 提交commit

### Day 2: 测试覆盖率（4-6小时）
1. 安装pytest-cov
2. 运行覆盖率报告
3. 为chat_manager.py添加测试
4. 为session.py添加测试
5. 为vision_ocr_service.py添加测试
6. 验证覆盖率>=70%
7. 提交commit

### Day 3: 超时处理（可选，2-3小时）
1. 为所有LLM调用添加timeout
2. 编写超时测试用例
3. 运行完整测试套件
4. 提交commit

## 质量标准

### 必须保持
- ✅ 所有测试通过
- ✅ 应用正常运行
- ✅ Vision OCR功能正常
- ✅ 无破坏性变更

### 提交前检查
```bash
# 1. 测试通过
pytest tests/ -v

# 2. 覆盖率达标
pytest --cov=modules --cov=services --cov=utils --cov-report=term

# 3. 应用启动
streamlit run app.py --server.port 8501

# 4. 手动测试
# - 上传账单图片
# - 智能顾问对话
# - 查看投资推荐
# - 查看消费分析
```

## 问题排查

### 如果截图遇到问题
- 检查应用是否运行: `curl http://localhost:8501`
- 检查端口占用: `lsof -i :8501`
- 重启应用: `pkill -f streamlit && streamlit run app.py`

### 如果测试失败
- 查看错误信息: `pytest tests/ -v --tb=short`
- 检查依赖: `pip list | grep pytest`
- 清理缓存: `pytest --cache-clear`

### 如果Vision OCR失败
- 检查.env配置
- 验证API key: `echo $OPENAI_API_KEY`
- 测试API连通性: `python test_vision_ocr.py`

## 参考文档
- 截图指南: `docs/screenshot_guide.md`
- Vision OCR测试: `test_vision_ocr.py`
- 项目README: `README.md`

## 联系方式
如有问题，请在代码中留言或创建issue。

---

**Good luck! 期待看到精美的截图和提升的测试覆盖率！** 🚀
