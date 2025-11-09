# WeFinance Copilot - 下一阶段优化PRD

## 文档信息
- 版本: v1.0
- 创建时间: 2025-01-06
- 目标时间线: 竞赛演示前3-5天
- 负责人: 慧眼队

---

## 一、当前状态诊断

### 已完成的工作

过去几天我们完成了核心UX优化：
- Vision OCR实时进度反馈（用户不再面对黑盒等待）
- 首页进度引导卡片（60%的用户能完整走完流程）
- 全局预算设置（消除了重复输入）
- 页面直接访问修复（提升了可用性）

代码规模：3167行Python代码，21个测试用例全部通过，5个文件依赖session state管理数据。

应用现在能跑起来，演示也没问题。但有三个致命问题。

### 问题1：数据持久化缺失（P0 - 竞赛演示的定时炸弹）

**现象**：
用户上传了10张账单，AI识别出40笔交易，设置了5000元预算，跟AI顾问聊了5轮，获得了投资建议。然后不小心刷新了浏览器。

结果：所有数据归零，从头再来。

**根本原因**：
我们用session state存储所有数据，这是Streamlit的内存缓存机制，浏览器刷新=会话结束=数据蒸发。

不是因为我们"追求轻量化设计"，是因为我们还没做数据持久化。README里写的"无数据库依赖"是优点，但没说"用户数据不保存"也是优点。

**为什么是定时炸弹**：
竞赛演示时，评委问："能看看上周的账单分析吗？" 你说："刷新了浏览器，数据没了。" 评委心里想："这玩意儿实用性在哪？"

**真实场景影响**：
- 演示中途断网重连：数据丢失
- 评委想重看某个步骤：刷新页面=重新开始
- 想对比不同预算下的建议：每次调整都要重新上传账单

这不是边缘场景，这是必然发生的事。

**现有代码证据**：
```python
# utils/session.py - 所有数据都在内存
st.session_state["transactions"] = transactions
st.session_state["monthly_budget"] = budget
st.session_state["chat_history"] = history

# 刷新浏览器 → st.session_state清空 → 数据消失
```

5个核心文件依赖session state，没有一个做了持久化fallback。

### 问题2：错误处理像"程序员写给程序员看的"（P0 - 用户体验杀手）

**现象**：
用户上传账单，OCR调用OpenAI API，网络慢或配额用完了，页面卡死30秒，然后弹出：
```
Error: HTTPStatusError 429 Too Many Requests
at openai.chat.completions.create() line 245
```

用户：？？？我该干什么？

**根本原因**：
我们的错误处理分两种：
1. 不处理，直接让Python异常堆栈砸用户脸上
2. 处理了，返回空列表/None，用户不知道发生了什么

都不是正常产品该做的事。

**真实代码证据**：
```python
# services/vision_ocr_service.py:145
try:
    response = self.client.chat.completions.create(...)
except Exception as e:
    logger.error(f"OCR failed: {e}")
    return []  # 用户不知道为什么失败，也不知道该做什么
```

没有timeout设置（网络慢=永久等待），没有用户友好的错误提示（技术堆栈不是人话），没有降级方案（API失败了，至少告诉用户可以手动输入）。

**为什么是用户体验杀手**：
演示时，评委上传一张账单，网络抖了一下，页面卡住。你说："稍等，可能是网络问题。" 评委心里想："这系统不稳定啊。"

然后评委刷新页面想重试，数据又没了（问题1）。双重打击。

### 问题3：测试覆盖率58%，但不是数字的问题（P1 - 质量保证）

**现象**：
21个测试用例全部通过，但核心流程没测到：
- Vision OCR的错误处理路径（网络失败、API限流、JSON解析失败）
- 数据持久化加载逻辑（因为还没实现）
- 全局预算设置的边界条件（负数、超大数、并发修改）

**为什么不是数字的问题**：
测试覆盖率70%不代表质量好，30%也可能刚好覆盖了所有关键路径。

问题不是"还差12%才到70%"，问题是：
1. 我们没测Vision OCR失败时会发生什么（这是核心竞争力）
2. 我们没测用户刷新浏览器会丢失什么数据（因为没做持久化）
3. 我们没测LLM调用超时会如何（因为没设timeout）

这些都是演示时会翻车的场景。

**真实数据**：
- `tests/test_ocr_service.py`：只测了成功路径，没测失败路径
- `tests/test_chat_manager.py`：mock了LLM响应，没测真实API失败
- `tests/test_integration.py`：端到端流程测试，但假设所有外部依赖都正常

测试写得挺好，但测的是"一切顺利"的情况。演示时Murphy定律告诉你：会出错的地方一定会出错。

---

## 二、优化目标（Linus式思考）

### Linus的三个问题

**1. "Is this a real problem or imagined?"**

数据持久化：真实问题。刷新浏览器=数据丢失，这不是边缘场景，是必然发生的事。

错误处理：真实问题。网络抖动、API限流、JSON解析失败，这些在演示时都会遇到。

测试覆盖率58%：伪问题。数字本身不重要，重要的是我们没测关键故障路径。

**2. "Is there a simpler way?"**

数据持久化不需要数据库。localStorage（浏览器本地存储）或JSON文件（用户主目录）足够。

错误处理不需要复杂框架。简单的try-catch + 人话错误提示 + 降级方案。

测试覆盖率提升不需要硬凑数字。写3-5个针对性测试，覆盖故障场景，比写20个success path测试有用。

**3. "What will this break?"**

数据持久化：需要考虑向后兼容。已有session state的代码不能改，只需要加一层持久化wrapper。

错误处理：要确保不影响正常流程。只在异常路径上加友好提示，success path不变。

测试：只增不改，不会break现有测试。

### 核心设计原则

**1. 数据结构优先于逻辑修补**

不要在每个页面里加`if st.session_state.get("data_loaded") == False: load_from_storage()`。

而是在`utils/session.py`里加一个`@ensure_loaded`装饰器，自动处理加载/保存。

**2. 特殊case消失才是好代码**

不要写：
```python
if network_error:
    show_error_A()
elif api_limit:
    show_error_B()
elif timeout:
    show_error_C()
```

而是：
```python
try:
    result = safe_call_with_fallback(api_func, timeout=30)
except UserFacingError as e:
    st.error(e.message)  # 统一的用户友好错误提示
```

**3. 复杂度要匹配问题严重程度**

数据持久化：严重问题（演示翻车），但解决方案简单（200行代码）。

错误处理：严重问题（用户体验差），但解决方案简单（100行代码）。

测试覆盖率：中等问题（质量保证），解决方案也简单（5-10个测试用例）。

不要过度设计。

---

## 三、优先级排序（基于竞赛演示风险）

### P0 - 演示前必须完成（否则会翻车）

**1. 数据持久化 - 防止"刷新归零"（预计2-3小时）**

风险：演示时评委刷新页面/网络断开重连/想重看某个步骤，数据丢失。

解决方案：
- localStorage持久化（浏览器关闭也保留）
- 自动保存/加载（用户无感知）
- 数据导出功能（JSON/CSV下载）

实现复杂度：低（200行代码，主要在`utils/session.py`）

**2. 错误处理增强 - "人话"错误提示（预计1-2小时）**

风险：演示时网络抖动/API限流，页面卡死或显示技术堆栈。

解决方案：
- LLM调用加timeout（30秒）
- API失败显示友好提示："网络连接不稳定，请稍后重试，或手动输入交易记录"
- 降级方案：OCR失败→手动输入；LLM失败→cached响应

实现复杂度：低（100行代码，主要在services/*）

**3. 竞赛演示材料（预计3-4小时）**

风险：评委看不到专业的UI截图、演示视频、技术PPT。

任务：
- 6-8张高质量UI截图（中英文各一套）
- 3-5分钟演示视频（展示核心功能流程）
- 15-20页PPT（技术亮点 + 商业价值 + Demo）

实现复杂度：中（需要设计工具，但内容已有）

### P1 - 演示后优化（提升竞争力）

**4. 关键路径测试增强（预计1-2小时）**

目标：不是提升覆盖率数字，是确保故障场景不翻车。

测试场景：
- Vision OCR失败路径（网络错误、JSON解析失败、API限流）
- 数据持久化加载/保存（localStorage读写、数据版本兼容）
- 并发场景（多用户同时使用、快速切换页面）

实现复杂度：低（5-10个测试用例）

**5. 性能优化（预计1小时）**

目标：演示时响应速度不能太慢（评委没耐心等）。

优化点：
- LLM调用加缓存（相同query不重复调用）
- 图片压缩（大图片OCR慢）
- 前端加载状态优化（spinner/skeleton）

实现复杂度：低（主要是配置调优）

### P2 - 可选增强（时间充裕再做）

**6. 数据导出/导入（预计1-2小时）**

功能：用户可以下载JSON/CSV格式的账单数据，下次上传恢复。

价值：解决跨设备/跨浏览器数据同步问题。

实现复杂度：低（基于持久化层扩展）

**7. 多语言优化（预计0.5小时）**

功能：完善英文翻译，确保所有UI文案都有对应翻译。

价值：国际化竞赛展示。

实现复杂度：低（主要是翻译工作）

---

## 四、详细实现方案

### 方案1：数据持久化（P0）

#### 问题分析

当前架构：
```
用户操作 → st.session_state[key] = value → 内存
刷新浏览器 → st.session_state清空 → 数据丢失
```

目标架构：
```
用户操作 → st.session_state[key] = value → 内存
         ↓
         localStorage/JSON文件 → 持久化
页面加载 → 自动从localStorage恢复 → st.session_state
```

#### 技术选型

**方案A：浏览器localStorage（推荐）**

优点：
- Streamlit原生支持（st.experimental_get_query_params/set_query_params）
- 无需服务器端存储
- 自动跨会话保留
- 简单，200行代码搞定

缺点：
- 容量限制（5-10MB，对我们足够）
- 跨浏览器不共享（可接受，单用户场景）

**方案B：JSON文件（备选）**

优点：
- 无容量限制
- 可导出/导入
- 方便调试

缺点：
- 需要文件I/O权限
- 多用户部署时需考虑隔离

#### 实现细节

**核心代码**（utils/session.py）：

```python
import json
from typing import Any, Optional
from functools import wraps

# 持久化存储key前缀
STORAGE_PREFIX = "wefinance_"

def save_to_storage(key: str, value: Any) -> None:
    """保存数据到localStorage"""
    storage_key = f"{STORAGE_PREFIX}{key}"
    try:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        # 使用st.experimental_set_query_params模拟localStorage
        # 实际部署时可用JS bridge或文件存储
        st.session_state[f"_storage_{key}"] = serialized
    except Exception as e:
        logger.warning(f"Failed to save {key} to storage: {e}")

def load_from_storage(key: str, default: Any = None) -> Optional[Any]:
    """从localStorage加载数据"""
    storage_key = f"_storage_{key}"
    try:
        serialized = st.session_state.get(storage_key)
        if serialized:
            return json.loads(serialized)
    except Exception as e:
        logger.warning(f"Failed to load {key} from storage: {e}")
    return default

def ensure_loaded(func):
    """装饰器：自动从storage加载数据"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 检查session state是否为空
        if "transactions" not in st.session_state:
            # 从storage恢复
            transactions = load_from_storage("transactions", [])
            if transactions:
                st.session_state["transactions"] = transactions

        if "monthly_budget" not in st.session_state:
            budget = load_from_storage("monthly_budget", 5000.0)
            st.session_state["monthly_budget"] = budget

        # 其他字段同理
        return func(*args, **kwargs)
    return wrapper
```

**修改现有代码**（零破坏性）：

```python
# utils/session.py - 现有的setter函数
def set_transactions(transactions: List[Transaction]) -> None:
    st.session_state["transactions"] = transactions
    save_to_storage("transactions", [t.dict() for t in transactions])  # 新增

def set_monthly_budget(budget: float) -> None:
    st.session_state["monthly_budget"] = budget
    save_to_storage("monthly_budget", budget)  # 新增
```

**app.py入口处自动加载**：

```python
# app.py:最顶部
from utils.session import load_from_storage

# 页面首次加载时恢复数据
if "data_loaded" not in st.session_state:
    transactions_data = load_from_storage("transactions", [])
    if transactions_data:
        from models.entities import Transaction
        transactions = [Transaction(**t) for t in transactions_data]
        st.session_state["transactions"] = transactions

    budget = load_from_storage("monthly_budget", 5000.0)
    st.session_state["monthly_budget"] = budget

    st.session_state["data_loaded"] = True
```

#### 验收标准

1. 用户上传账单后刷新浏览器，交易记录依然存在
2. 用户设置预算后刷新浏览器，预算值依然存在
3. 用户聊天历史刷新后依然存在
4. 用户可以手动"清除所有数据"（侧边栏按钮）

#### 风险控制

- 数据版本兼容：加version字段，升级时自动迁移
- 存储失败降级：如果localStorage不可用，退回到纯session state
- 性能：每次保存序列化JSON，<10ms，可接受

### 方案2：错误处理增强（P0）

#### 问题分析

当前错误处理的三个问题：

1. **没有timeout**：LLM调用可能永久卡住
2. **技术堆栈暴露**：用户看到`HTTPStatusError 429`没有意义
3. **没有降级方案**：失败了用户不知道该做什么

#### 实现细节

**统一错误处理装饰器**（utils/error_handling.py，新建）：

```python
import functools
import streamlit as st
from typing import Callable, Any, Optional

class UserFacingError(Exception):
    """用户友好的错误，可以直接展示"""
    def __init__(self, message: str, suggestion: str = None):
        self.message = message
        self.suggestion = suggestion
        super().__init__(message)

def safe_call(
    timeout: int = 30,
    fallback: Any = None,
    error_message: str = "操作失败，请稍后重试"
):
    """装饰器：添加timeout和友好错误提示"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("操作超时")

            # 设置timeout
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)

            try:
                result = func(*args, **kwargs)
                signal.alarm(0)  # 取消timeout
                return result

            except TimeoutError:
                signal.alarm(0)
                raise UserFacingError(
                    "网络响应超时，请检查网络连接后重试",
                    suggestion="您也可以选择手动输入交易记录"
                )

            except Exception as e:
                signal.alarm(0)
                # 将技术错误转换为用户友好错误
                if "429" in str(e) or "Too Many Requests" in str(e):
                    raise UserFacingError(
                        "API调用频率超限，请稍后重试",
                        suggestion="如果问题持续，请联系技术支持"
                    )
                elif "401" in str(e) or "Unauthorized" in str(e):
                    raise UserFacingError(
                        "API密钥配置错误，请检查.env文件",
                        suggestion="确保OPENAI_API_KEY配置正确"
                    )
                elif "Network" in str(e) or "Connection" in str(e):
                    raise UserFacingError(
                        "网络连接失败，请检查网络设置",
                        suggestion="确保能访问OpenAI API服务"
                    )
                else:
                    logger.error(f"Unexpected error in {func.__name__}: {e}")
                    if fallback is not None:
                        return fallback
                    raise UserFacingError(
                        error_message,
                        suggestion="请刷新页面重试，或联系技术支持"
                    )

        return wrapper
    return decorator
```

**应用到LLM调用**（services/vision_ocr_service.py）：

```python
from utils.error_handling import safe_call, UserFacingError

@safe_call(
    timeout=30,
    fallback=[],
    error_message="账单识别失败"
)
def extract_transactions_from_image(self, image_bytes: bytes) -> List[Transaction]:
    """现有的OCR实现，加了装饰器后自动处理超时和错误"""
    # 原有代码不变
    response = self.client.chat.completions.create(...)
    ...
```

**在UI层统一处理**（pages/bill_upload.py）：

```python
from utils.error_handling import UserFacingError

try:
    transactions = ocr_service.process_files(uploaded_files)
    st.success(f"成功识别{len(transactions)}笔交易")
except UserFacingError as e:
    st.error(e.message)
    if e.suggestion:
        st.info(e.suggestion)
    # 提供降级方案
    if st.button("手动输入交易记录"):
        st.session_state["show_manual_entry"] = True
        st.rerun()
```

#### 验收标准

1. LLM调用超过30秒自动timeout，显示友好错误
2. API限流/认证失败时，显示人话错误+解决建议
3. 所有错误都有"降级方案"（手动输入/缓存响应）
4. 技术堆栈不暴露给用户

### 方案3：竞赛演示材料（P0）

#### UI截图清单

**中文版**（6张）：
1. 首页 - 进度引导卡片（展示4步流程）
2. 账单上传 - Vision OCR实时进度（展示识别过程）
3. 消费分析 - 图表+异常检测（展示数据可视化）
4. AI顾问 - 对话界面（展示智能问答）
5. 投资建议 - 推荐结果+解释链（展示可解释AI）
6. 全局设置 - 预算设置+语言切换（展示国际化）

**英文版**（2张）：
1. 首页（英文界面）
2. AI顾问对话（英文界面）

截图要求：
- 分辨率：1920x1080（高清）
- 格式：PNG（无损）
- 真实数据：使用sample_bills的真实识别结果
- 美观：确保界面无报错、无debug信息

#### 演示视频脚本

**时长**：3-5分钟

**流程**：
1. 开场（30秒）：介绍WeFinance Copilot，展示首页进度引导
2. 核心功能演示（2分钟）：
   - 上传账单 → Vision OCR实时识别（展示技术优势）
   - 查看消费分析 → 图表+异常检测（展示数据洞察）
   - AI顾问对话 → 问答+建议（展示智能交互）
   - 投资推荐 → 推荐结果+解释（展示可解释性）
3. 技术亮点（1分钟）：
   - Vision OCR vs PaddleOCR对比（准确率、成本）
   - 数据隐私保护（本地处理）
   - 国际化支持（中英切换）
4. 商业价值（30秒）：目标用户、应用场景、未来规划

录制要求：
- 工具：OBS Studio（开源免费）
- 画质：1080p 30fps
- 配音：清晰普通话，语速适中
- 字幕：关键技术点加字幕强调

#### 竞赛PPT大纲

**页数**：15-20页

**结构**：

1. 封面（1页）：项目名称、团队、slogan
2. 问题背景（2页）：用户痛点、市场需求
3. 解决方案（3页）：产品定位、核心功能、技术架构
4. 技术亮点（4页）：
   - Vision OCR混合架构（准确率100% vs 0%）
   - 数据隐私保护（本地处理零上传）
   - 可解释AI（推荐透明度）
   - 成本优化（97%成本降低）
5. 产品演示（5页）：截图+关键流程说明
6. 竞争优势（2页）：vs传统记账软件、vs纯AI方案
7. 商业价值（2页）：目标用户、盈利模式、增长空间
8. 团队介绍（1页）：慧眼队成员+分工

设计要求：
- 模板：专业商务风格（避免花哨）
- 配色：蓝色系（金融行业通用）
- 图表：数据可视化（对比图、流程图）
- 文字：精炼，每页核心信息1-2句话

### 方案4：关键路径测试增强（P1）

#### 测试场景设计

**场景1：Vision OCR故障路径**（tests/test_ocr_service.py）：

```python
def test_vision_ocr_network_failure():
    """测试网络失败时的降级处理"""
    service = VisionOCRService()

    # Mock API调用抛出网络错误
    with patch.object(service.client.chat.completions, 'create') as mock_create:
        mock_create.side_effect = ConnectionError("Network unreachable")

        # 应该返回空列表，不crash
        result = service.extract_transactions_from_image(b"fake_image")
        assert result == []

def test_vision_ocr_json_parse_failure():
    """测试JSON解析失败时的处理"""
    service = VisionOCRService()

    # Mock返回非JSON格式
    with patch.object(service.client.chat.completions, 'create') as mock_create:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "这不是JSON"
        mock_create.return_value = mock_response

        # 应该返回空列表，记录错误日志
        result = service.extract_transactions_from_image(b"fake_image")
        assert result == []

def test_vision_ocr_timeout():
    """测试API调用超时处理"""
    service = VisionOCRService()

    # Mock API调用超时
    with patch.object(service.client.chat.completions, 'create') as mock_create:
        mock_create.side_effect = TimeoutError()

        # 应该捕获并转换为UserFacingError
        with pytest.raises(UserFacingError) as exc_info:
            service.extract_transactions_from_image(b"fake_image")

        assert "超时" in str(exc_info.value.message)
```

**场景2：数据持久化测试**（tests/test_session.py）：

```python
def test_save_and_load_transactions():
    """测试交易记录的保存和加载"""
    from utils.session import save_to_storage, load_from_storage
    from models.entities import Transaction

    # 构造测试数据
    transactions = [
        Transaction(date="2025-01-01", merchant="测试商户", amount=100.0, category="餐饮")
    ]

    # 保存
    save_to_storage("transactions", [t.dict() for t in transactions])

    # 加载
    loaded_data = load_from_storage("transactions", [])
    loaded_transactions = [Transaction(**t) for t in loaded_data]

    assert len(loaded_transactions) == 1
    assert loaded_transactions[0].merchant == "测试商户"

def test_storage_corruption_handling():
    """测试存储数据损坏时的处理"""
    from utils.session import load_from_storage

    # 模拟损坏的JSON
    st.session_state["_storage_transactions"] = "{invalid json}"

    # 应该返回默认值，不crash
    result = load_from_storage("transactions", [])
    assert result == []
```

**场景3：并发操作测试**（tests/test_concurrent.py，新建）：

```python
import threading
from utils.session import set_monthly_budget, get_monthly_budget

def test_concurrent_budget_updates():
    """测试多线程同时修改预算"""
    def update_budget(value):
        set_monthly_budget(value)

    threads = [
        threading.Thread(target=update_budget, args=(1000 * i,))
        for i in range(10)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 最终值应该是某个线程设置的值，不crash即可
    budget = get_monthly_budget()
    assert budget in [1000 * i for i in range(10)]
```

#### 验收标准

1. 所有新测试通过（5-10个用例）
2. 覆盖关键故障路径（网络、JSON、timeout、并发）
3. 测试运行时间<10秒（不影响开发体验）

---

## 五、时间规划

### 假设场景：距离竞赛演示还有5天

**Day 1-2（8小时）**：P0核心功能
- 数据持久化实现（3小时）
- 错误处理增强（2小时）
- 测试验证（1小时）
- 代码review+提交（2小时）

**Day 3（4小时）**：P0演示材料
- UI截图（1.5小时）
- 演示视频录制（2小时）
- PPT制作（0.5小时初稿）

**Day 4（4小时）**：P1质量保证
- 关键路径测试（2小时）
- 性能优化（1小时）
- PPT完善（1小时）

**Day 5（2小时）**：演练和调优
- 完整演示流程演练（1小时）
- 发现问题并修复（1小时）

总计：18小时（平均每天3.6小时）

### 如果时间更紧张（3天）

只做P0：
- Day 1：数据持久化（4小时）
- Day 2：错误处理+测试（4小时）
- Day 3：演示材料（4小时）

---

## 六、验收标准（Demo演示检查清单）

### 功能完整性

- [ ] 上传账单，刷新浏览器，数据不丢失
- [ ] 设置预算，刷新浏览器，预算保留
- [ ] 聊天历史，刷新浏览器，历史保留
- [ ] 网络失败时显示友好错误，不crash
- [ ] LLM超时（>30秒）自动timeout，显示提示
- [ ] 所有错误都有"下一步该做什么"的建议

### 演示材料

- [ ] 6张中文UI截图，高清无瑕疵
- [ ] 2张英文UI截图
- [ ] 3-5分钟演示视频，画质清晰
- [ ] 15-20页竞赛PPT，设计专业

### 质量保证

- [ ] 21+个测试用例全部通过
- [ ] 关键故障路径有测试覆盖
- [ ] 代码通过black/ruff检查
- [ ] 无console警告/错误

### 演示流程演练

- [ ] 完整走一遍4步流程，无卡顿
- [ ] 故意触发错误（断网、API限流），处理优雅
- [ ] 刷新浏览器，数据恢复正常
- [ ] 切换中英文，界面无破损

---

## 七、风险评估

### 技术风险

**风险1：localStorage容量限制**

可能性：低（我们的数据<1MB，远低于5MB限制）

缓解：如果超限，降级到session state + 数据导出

**风险2：浏览器兼容性**

可能性：中（Safari的localStorage可能有坑）

缓解：测试主流浏览器（Chrome/Edge/Safari），提供JSON导出兜底

**风险3：实时演示网络抖动**

可能性：高（Murphy定律）

缓解：
1. 提前录制备用视频
2. LLM调用加缓存（演示前预热）
3. 准备离线demo数据

### 时间风险

**风险：距离竞赛不到5天，时间紧张**

缓解：
1. 严格按P0/P1/P2优先级执行
2. P0必做，P1选做，P2砍掉
3. 每天code review确保方向正确

### 人员风险

**风险：单人开发，生病/突发事件会影响进度**

缓解：
1. 每天提交代码到GitHub（避免丢失）
2. 关键步骤写文档（方便他人接手）
3. 优先做P0，确保最小可演示版本

---

## 八、成功指标

### 演示效果

**目标**：评委问的3个常见问题都能完美应对：

1. "刷新一下页面试试？" → 数据不丢失 ✓
2. "如果网络断了怎么办？" → 友好错误+降级方案 ✓
3. "这个系统稳定吗？" → 有测试覆盖+错误处理 ✓

### 技术指标

- 数据持久化成功率：100%（localStorage可用时）
- LLM调用成功率：95%+（有timeout+降级）
- 演示流程无crash：100%（关键路径测试覆盖）

### 用户体验指标

- 错误提示可读性：非技术用户能理解
- 降级方案可用性：每个失败都有Plan B
- 演示流畅度：4步流程<3分钟完成

---

## 九、后续规划（竞赛后）

如果时间允许，或者竞赛后持续优化：

### 功能增强

1. **数据分析仪表板**：月度/年度对比、消费趋势预测
2. **多账户管理**：支持多张信用卡/银行账户
3. **预算预警**：超支提醒、智能建议

### 技术架构

1. **后端API化**：从Streamlit单体拆分为前后端
2. **数据库持久化**：从localStorage升级到PostgreSQL
3. **多用户支持**：用户认证、数据隔离

### 商业化准备

1. **SaaS部署**：Docker + Kubernetes
2. **付费功能**：高级分析、定制化建议
3. **API开放**：给第三方记账软件集成

但这些都是"竞赛之后"的事了。现在专注P0。

---

## 十、附录：技术决策记录

### 为什么选择localStorage而不是数据库？

**理由**：
1. 竞赛项目，10天开发周期，引入数据库=额外3天（设计schema、迁移脚本、ORM）
2. 单用户场景，不需要多用户隔离
3. 数据量小（<1MB），localStorage足够
4. 无服务器部署成本（Streamlit Cloud免费额度）

**什么时候需要数据库**：
- 多用户SaaS部署（需要用户隔离）
- 数据量>10MB（localStorage扛不住）
- 需要复杂查询（SQL聚合、JOIN）

现在不需要，不要过度设计。

### 为什么不用Streamlit的st.cache？

**理由**：
1. st.cache是函数级别缓存，不是数据持久化
2. 刷新浏览器会清空cache
3. 我们需要的是"跨会话"的数据保留，不是"同会话内"的加速

**什么时候用st.cache**：
- 计算密集型函数（避免重复计算）
- LLM调用缓存（相同query不重复调用）

这两个场景我们都在用，但不能替代localStorage。

### 为什么错误处理用装饰器而不是try-catch到处写？

**理由**：
1. DRY原则：错误处理逻辑只写一次
2. 特殊case消失：不需要在每个API调用处写if network_error/if timeout/if api_limit
3. 统一体验：所有错误提示风格一致
4. 易于测试：装饰器可以单独测试，不需要测试每个函数的错误分支

**Linus会怎么说**：
"如果你发现自己在复制粘贴错误处理代码，说明你的抽象层次不对。"

---

## 总结

这份PRD解决的不是"功能缺失"，而是"演示翻车风险"。

我们已经有了能跑的MVP，现在要确保：
1. 评委刷新浏览器，数据不丢失（数据持久化）
2. 演示时网络抖动，不crash（错误处理）
3. 评委看到专业的UI/视频/PPT（演示材料）

这三件事做好了，竞赛演示稳了。其他的都是锦上添花。

时间紧张的情况下，严格按P0→P1→P2优先级，确保核心不出问题。
