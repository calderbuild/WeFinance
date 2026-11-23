# WeFinance 部署指南

## 1. 方案概览
- **在线体验（推荐）**：直接通过 [Anna 应用商店](https://anna.partners/store/@calderbuild/wefinance?ref=github-deploy) 使用托管版 WeFinance，无需维护服务器或公共演示密钥。
- **本地运行**：使用 Conda 或 pip 启动 `streamlit run app.py`，通过 `.env` 配置你自己的视觉与对话模型 API Key。
- **私有环境 / 准生产**：将同一代码包装为 Docker，部署到自有服务器或托管 K8s，账单数据不出域。

> 说明：项目不再维护官方 Streamlit Community Cloud 公开演示（免费实例约 12 小时无人访问会休眠，且不适合长期托管共享 API 密钥）；下方仅保留供个人按需自建的参考步骤。

## 2. 本地与自托管部署（推荐）
### 2.1 本地启动
1. 准备依赖：`conda env create -f environment.yml && conda activate wefinance`（或使用 Python 3.10+ 执行 `pip install -r requirements.txt`）。
2. 复制环境变量模板：`cp .env.example .env`，填入 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`、`LLM_PROVIDER`。
3. 运行 `streamlit run app.py --server.port 8501`，访问 `http://localhost:8501`。
4. 上传 `assets/sample_bills/bill_dining.png` 验证 OCR，打开 “Insights / Advisor” 分页验证对话能力。

### 2.2 容器与内网部署
1. **私有云容器**：使用 `python:3.10-slim` 作为基础镜像，拷贝代码与 `requirements.txt`，执行 `pip install -r requirements.txt`，然后以 `streamlit run app.py --server.port=8080 --server.headless=true` 作为入口；结合 K8s HPA 根据会话量扩缩容。
2. **内网 GPU 节点**：安装 Conda 环境 `conda env create -f environment.yml`，通过 Nginx 反向代理给内网用户，保障账单数据不出域。

## 3. Secret 与配置管理
- 不要将 `.env` 或真实密钥加入仓库；仅提交 `.env.example` 与 `.streamlit/secrets.toml.example` 作为模板。
- 本地调试通过 `.env` 注入环境变量；若自行部署到第三方托管平台，请在平台 Secrets 中配置同名变量。
- 新增第三方服务依赖时，请同步更新 `.env.example`、`README` 与 `DEPLOY.md`。

## 4. 可选：自行部署到 Streamlit Community Cloud
如果你希望在自己的账号下单独搭建一个演示实例：
1. 登录 https://share.streamlit.io/ ，选择 **New app → From existing repo**，绑定你的 fork 与目标分支（Python 选 3.10）。
2. 在 **Advanced settings → Secrets** 填入 `.streamlit/secrets.toml.example` 中的键。
3. 需注意 Community Cloud 免费实例在约 12 小时无访问后会休眠，且请自行控制所填 API Key 的消费额度。
