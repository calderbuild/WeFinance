# Conda环境管理指南

本项目使用conda进行环境和依赖管理，确保开发环境的一致性和可复现性。

## 为什么使用Conda？

1. **跨平台**：Windows/Linux/macOS统一管理
2. **依赖隔离**：避免不同项目的包冲突
3. **版本锁定**：确保团队使用相同的包版本
4. **二进制包**：conda优先提供预编译包，安装更快
5. **科学计算优化**：对numpy、pandas等包有专门优化

## 快速开始

### 方式1：自动安装脚本（推荐）

**Linux/Mac**：
```bash
chmod +x setup_conda_env.sh
./setup_conda_env.sh
```

**Windows**：
```cmd
setup_conda_env.bat
```

### 方式2：手动安装

```bash
# 1. 创建环境
conda env create -f environment.yml

# 2. 激活环境
conda activate wefinance

# 3. 验证安装
python --version  # 应显示Python 3.10.x
conda list        # 查看已安装的包
```

## 环境配置说明

### environment.yml结构

```yaml
name: wefinance                # 环境名称
channels:                      # 包下载源
  - conda-forge                # 社区维护，包更新快
  - defaults                   # Anaconda官方源
dependencies:
  # Conda包（优先）
  - python=3.10
  - pandas=2.0.*
  - numpy=1.24.*
  # ...

  # Pip包（必要时）
  - pip:
    - streamlit==1.28.0
    - paddleocr==2.7.0
    # ...
```

### 依赖分类

| 类别 | 包名 | 来源 | 原因 |
|------|------|------|------|
| **核心环境** | python, pip | conda | 基础环境 |
| **数据科学** | pandas, numpy, scipy | conda | 二进制优化，安装快 |
| **图像处理** | pillow, opencv | conda | 依赖复杂，conda处理更好 |
| **可视化** | plotly, matplotlib | conda | 依赖少，稳定 |
| **开发工具** | pytest, black, ruff | conda | 开发标准工具 |
| **Web框架** | streamlit | pip | conda版本滞后 |
| **OCR引擎** | paddleocr, paddlepaddle | pip | 无conda版本 |
| **LLM框架** | openai, langchain | pip | 更新频繁，conda滞后 |

## 常用命令

### 环境管理

```bash
# 查看所有环境
conda env list
conda info --envs

# 激活环境
conda activate wefinance

# 退出环境
conda deactivate

# 删除环境
conda env remove -n wefinance

# 克隆环境
conda create --name wefinance-backup --clone wefinance
```

### 包管理

```bash
# 查看已安装的包
conda list
conda list | grep pandas  # 查看特定包

# 查看包详情
conda info pandas

# 搜索包
conda search plotly

# 安装包（优先conda）
conda install pandas
conda install -c conda-forge package-name

# 如果conda没有，用pip
pip install package-name

# 更新包
conda update pandas
conda update --all  # 更新所有包（谨慎使用）

# 删除包
conda remove pandas
```

### 环境导出与导入

```bash
# 导出完整环境（包含所有依赖）
conda env export > environment_full.yml

# 导出手动安装的包（推荐，更简洁）
conda env export --from-history > environment.yml

# 从yml导入
conda env create -f environment.yml

# 更新现有环境
conda env update -f environment.yml --prune
```

## 国内镜像源配置

### 清华镜像（推荐）

```bash
# 添加镜像源
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/

# 显示源地址
conda config --set show_channel_urls yes

# 查看配置
conda config --show channels
```

### 恢复默认源

```bash
conda config --remove-key channels
```

### pip镜像（可选）

```bash
# 临时使用
pip install package-name -i https://pypi.tuna.tsinghua.edu.cn/simple

# 永久配置
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

## 添加新依赖

### Conda包（优先）

1. 搜索包是否存在：
   ```bash
   conda search package-name
   ```

2. 编辑`environment.yml`：
   ```yaml
   dependencies:
     - package-name=1.0.*
   ```

3. 更新环境：
   ```bash
   conda env update -f environment.yml --prune
   ```

### Pip包（必要时）

1. 编辑`environment.yml`的pip部分：
   ```yaml
   - pip:
     - package-name==1.0.0
   ```

2. 更新环境：
   ```bash
   conda env update -f environment.yml --prune
   ```

## 常见问题

### 1. 环境创建失败

**问题**：`ResolvePackageNotFound` 或 `CondaError`

**解决**：
```bash
# 清理缓存
conda clean --all

# 强制重建
conda env create -f environment.yml --force
```

### 2. 包版本冲突

**问题**：`UnsatisfiableError: The following specifications were found to be incompatible`

**解决**：
```bash
# 放宽版本限制（environment.yml）
- pandas>=2.0.0  # 而不是 pandas=2.0.5

# 或使用conda-forge源
conda install -c conda-forge package-name
```

### 3. pip和conda混用问题

**最佳实践**：
1. **优先conda**：能用conda安装的尽量用conda
2. **pip在后**：先用conda安装大部分包，最后用pip补充
3. **明确记录**：在environment.yml中清晰区分conda和pip依赖

**避免**：
```bash
# ❌ 不推荐：直接pip install
pip install pandas  # 可能与conda的numpy版本冲突

# ✅ 推荐：在environment.yml中管理
```

### 4. GPU支持（PaddlePaddle）

**CPU版本**（默认）：
```yaml
- pip:
  - paddlepaddle==2.5.0
```

**GPU版本**（CUDA 11.x）：
```yaml
- pip:
  - paddlepaddle-gpu==2.5.0
```

安装后验证：
```bash
python -c "import paddle; print(paddle.device.cuda.device_count())"
```

### 5. Windows下路径问题

**问题**：`conda activate wefinance` 不生效

**解决**：
```cmd
# 初始化conda（首次）
conda init cmd.exe

# 重启命令行窗口
# 然后激活环境
conda activate wefinance
```

### 6. M1/M2 Mac兼容性

**问题**：某些包在Apple Silicon上不可用

**解决**：
```bash
# 使用Rosetta模式安装x86版本
CONDA_SUBDIR=osx-64 conda env create -f environment.yml
conda activate wefinance
conda config --env --set subdir osx-64
```

## 性能优化

### 加速包解析

```bash
# 安装更快的依赖解析器
conda install -n base conda-libmamba-solver

# 使用libmamba解析器
conda config --set solver libmamba
```

### 减少环境大小

```bash
# 清理缓存
conda clean --all

# 只导出手动安装的包
conda env export --from-history > environment.yml
```

## 开发工作流

### 日常开发

```bash
# 1. 激活环境
conda activate wefinance

# 2. 开发代码
streamlit run app.py

# 3. 运行测试
pytest tests/

# 4. 退出环境
conda deactivate
```

### 添加新功能

```bash
# 1. 需要新包
conda search new-package

# 2. 更新environment.yml
# 添加：- new-package=1.0.*

# 3. 更新环境
conda env update -f environment.yml --prune

# 4. 验证安装
python -c "import new_package; print(new_package.__version__)"
```

### 团队协作

```bash
# 1. 拉取代码
git pull

# 2. 检查environment.yml是否有更新
git diff environment.yml

# 3. 如果有更新，同步环境
conda env update -f environment.yml --prune

# 4. 继续开发
```

## 最佳实践

1. **版本锁定策略**：
   - 生产环境：精确版本 `pandas==2.0.5`
   - 开发环境：小版本范围 `pandas=2.0.*`
   - 宽松依赖：大版本范围 `pandas>=2.0.0`

2. **环境命名规范**：
   - 项目名称：`wefinance`
   - 带版本：`wefinance-v1.0`
   - 开发环境：`wefinance-dev`

3. **定期维护**：
   ```bash
   # 每月一次
   conda update conda
   conda update --all
   conda clean --all
   ```

4. **备份关键环境**：
   ```bash
   conda create --name wefinance-backup --clone wefinance
   ```

5. **文档化依赖**：
   - 在`environment.yml`中添加注释
   - 说明为什么需要某个包
   - 记录版本选择的原因

## 参考资料

- [Conda官方文档](https://docs.conda.io/)
- [Conda-Forge社区](https://conda-forge.org/)
- [Conda速查表](https://docs.conda.io/projects/conda/en/latest/user-guide/cheatsheet.html)
- [清华大学开源镜像站](https://mirrors.tuna.tsinghua.edu.cn/help/anaconda/)

## 技术支持

遇到问题？按以下顺序排查：

1. 查看本文档的"常见问题"部分
2. 运行诊断命令：
   ```bash
   conda info
   conda list
   conda config --show
   ```
3. 搜索错误信息：`conda [错误信息]`
4. 提交Issue：[项目GitHub仓库]

---

**最后更新**：2025-11-06
**维护者**：WeFinance Copilot团队
