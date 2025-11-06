# WeFinance Copilot 截图指南

## 目标
为 README.md 和 README_EN.md 添加 5-8 张双语界面截图，展示应用核心功能。

## 前置条件

1. **启动应用**：
```bash
cd /mnt/d/Hackathon/WeFinance
source /home/jason/miniconda3/etc/profile.d/conda.sh
conda activate wefinance
streamlit run app.py --server.port 8501
```

2. **访问地址**: http://localhost:8501

3. **截图工具**:
   - Windows: Win + Shift + S
   - macOS: Cmd + Shift + 4
   - Chrome DevTools: Ctrl+Shift+P → "Capture screenshot"

## 必须截图的页面（8张）

### 1. 首页 - 中文版 (01_home_zh.png)
- 路径: 首页（默认）
- 语言: 点击右上角切换到中文
- 重点: WeFinance Copilot标题、功能简介、异常提醒（如有）
- 截图范围: 完整页面

### 2. 首页 - 英文版 (01_home_en.png)
- 路径: 首页
- 语言: 点击右上角切换到English
- 重点: 英文标题、功能介绍
- 截图范围: 完整页面

### 3. 智能顾问对话 - 中文版 (02_advisor_chat_zh.png)
- 路径: 侧边栏 → "智能顾问对话"
- 语言: 中文
- 操作: 输入测试问题，如"我最近消费太高了，有什么建议吗？"
- 重点: 对话界面、LLM回复、思维链展示
- 截图范围: 包含输入框和完整对话

### 4. 智能顾问对话 - 英文版 (02_advisor_chat_en.png)
- 路径: 侧边栏 → "Advisor Chat"
- 语言: English
- 操作: 输入英文问题，如"What are my spending patterns?"
- 重点: 英文对话界面
- 截图范围: 完整对话

### 5. 账单上传 - Vision OCR识别 (03_bill_upload_zh.png)
**重点功能 - Vision OCR**
- 路径: 侧边栏 → "账单上传"
- 语言: 中文
- 操作:
  1. 上传测试图片: `assets/sample_bills/bill_dining.png`
  2. 等待Vision OCR识别完成
  3. 查看识别结果表格
- 重点:
  - 上传界面
  - OCR识别后的交易记录表格
  - 显示日期、商户、分类、金额
- 截图范围: 包含上传按钮、识别结果表格

### 6. 账单上传 - 英文版 (03_bill_upload_en.png)
- 路径: 侧边栏 → "Bill Upload"
- 语言: English
- 操作: 上传同样的测试图片
- 重点: 英文界面的识别结果
- 截图范围: 完整页面

### 7. 投资推荐 (04_investment_recs_zh.png)
- 路径: 侧边栏 → "投资推荐"
- 语言: 中文
- 重点:
  - 风险评估结果
  - 推荐的投资产品
  - 风险等级标注
  - 推理链（如有）
- 截图范围: 完整推荐列表

### 8. 消费分析 (05_spending_insights_zh.png)
- 路径: 侧边栏 → "消费分析"
- 语言: 中文
- 重点:
  - 消费统计图表
  - 分类饼图/柱状图
  - 趋势分析
  - 洞察卡片
- 截图范围: 包含所有图表和分析卡片

## 截图规范

### 文件命名
```
序号_页面名称_语言.png
例如: 01_home_zh.png, 03_bill_upload_en.png
```

### 存储位置
```
docs/screenshots/
├── 01_home_zh.png
├── 01_home_en.png
├── 02_advisor_chat_zh.png
├── 02_advisor_chat_en.png
├── 03_bill_upload_zh.png
├── 03_bill_upload_en.png
├── 04_investment_recs_zh.png
└── 05_spending_insights_zh.png
```

### 图片要求
- **格式**: PNG（推荐）或 JPG
- **分辨率**: 至少 1280x720，推荐 1920x1080
- **质量**: 清晰可读，避免模糊
- **裁剪**: 保留完整UI，去除浏览器地址栏和书签栏
- **文件大小**: 单张不超过 2MB（便于GitHub加载）

### 截图技巧
1. **完整页面**: 使用 F11 全屏模式，去除浏览器UI干扰
2. **滚动截图**: 长页面使用 Chrome DevTools 的 "Capture full size screenshot"
3. **隐私保护**: 如果有真实数据，确保隐私信息已脱敏
4. **光标隐藏**: 截图前移开鼠标光标

## 测试数据准备

### 账单上传测试图片
```bash
# 已生成的测试图片
assets/sample_bills/bill_dining.png    # 餐饮账单（4笔交易）
assets/sample_bills/bill_mixed.png     # 混合账单（4笔交易）
assets/sample_bills/bill_shopping.png  # 购物账单（3笔交易）
```

### 智能顾问测试问题
中文：
- "我最近消费太高了，有什么建议吗？"
- "如何规划我的退休储蓄？"
- "分析一下我的餐饮支出"

英文：
- "My spending is too high recently, any advice?"
- "What are my spending patterns?"
- "How should I plan my retirement savings?"

## 完成后检查清单

- [ ] 8张截图已保存到 `docs/screenshots/` 目录
- [ ] 文件命名符合规范
- [ ] 图片清晰可读
- [ ] 包含中英文双语界面
- [ ] Vision OCR功能展示完整（重点）
- [ ] 文件大小合理（单张 < 2MB）
- [ ] 准备好更新README.md和README_EN.md

## 下一步

截图完成后，需要更新README文件：
1. 在 "功能展示" / "Features" 章节插入截图
2. 使用相对路径引用: `![描述](docs/screenshots/01_home_zh.png)`
3. 添加截图说明文字
4. 确保中英文README都更新

## 注意事项

1. **Vision OCR是核心亮点**:
   - 必须展示账单上传后的识别结果表格
   - 显示100%识别准确率
   - 强调从PaddleOCR到GPT-4o Vision的升级

2. **双语展示**:
   - 至少首页和账单上传需要双语截图
   - 其他页面可以只截中文版

3. **真实性**:
   - 使用真实的测试图片（assets/sample_bills/）
   - 显示真实的识别结果
   - 不要使用mock数据

4. **美观性**:
   - 确保UI完整无遮挡
   - 调整浏览器窗口到合适大小
   - 避免截图时显示错误信息
