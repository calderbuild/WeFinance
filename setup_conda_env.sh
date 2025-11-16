#!/bin/bash
# WeFinance Copilot - Conda环境安装脚本
#
# 使用方法：
#   chmod +x setup_conda_env.sh
#   ./setup_conda_env.sh

set -e  # 遇到错误立即退出

echo "================================================"
echo "WeFinance Copilot - Conda环境安装"
echo "================================================"
echo ""

# 检查conda是否安装
if ! command -v conda &> /dev/null
then
    echo "❌ 错误：未检测到conda，请先安装Miniconda或Anaconda"
    echo "   下载地址："
    echo "   - Miniconda: https://docs.conda.io/en/latest/miniconda.html"
    echo "   - Anaconda: https://www.anaconda.com/products/distribution"
    exit 1
fi

echo "✅ 检测到conda: $(conda --version)"
echo ""

# 检查environment.yml是否存在
if [ ! -f "environment.yml" ]; then
    echo "❌ 错误：未找到environment.yml文件"
    echo "   请确保在项目根目录下运行此脚本"
    exit 1
fi

echo "📋 配置文件：environment.yml"
echo ""

# 询问是否配置国内镜像源（加速）
read -p "是否配置清华镜像源（推荐国内用户）？[y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "⚙️  配置清华镜像源..."
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/
    conda config --set show_channel_urls yes
    echo "✅ 镜像源配置完成"
    echo ""
fi

# 检查环境是否已存在
if conda env list | grep -q "^wefinance "; then
    echo "⚠️  检测到wefinance环境已存在"
    read -p "是否删除并重建？[y/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        echo "🗑️  删除旧环境..."
        conda env remove -n wefinance -y
        echo "✅ 旧环境已删除"
        echo ""
    else
        echo "ℹ️  将更新现有环境"
        echo ""
    fi
fi

# 创建或更新环境
echo "📦 安装依赖包（这可能需要几分钟）..."
echo ""

if conda env list | grep -q "^wefinance "; then
    # 更新现有环境
    conda env update -f environment.yml --prune
else
    # 创建新环境
    conda env create -f environment.yml
fi

echo ""
echo "✅ 环境安装完成！"
echo ""

# 验证安装
echo "🔍 验证安装..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate wefinance

echo "   Python版本: $(python --version)"
echo "   已安装包数: $(conda list | wc -l)"
echo ""

# 检查关键包
echo "📋 关键包验证："
python -c "import streamlit; print(f'   ✅ streamlit {streamlit.__version__}')" || echo "   ❌ streamlit 安装失败"
python -c "import pandas; print(f'   ✅ pandas {pandas.__version__}')" || echo "   ❌ pandas 安装失败"
python -c "import openai; print(f'   ✅ openai {openai.__version__}')" || echo "   ❌ openai 安装失败"
python -c "import langchain; print(f'   ✅ langchain {langchain.__version__}')" || echo "   ❌ langchain 安装失败"

echo ""
echo "================================================"
echo "🎉 安装成功！"
echo "================================================"
echo ""
echo "下一步操作："
echo "1. 激活环境："
echo "   conda activate wefinance"
echo ""
echo "2. 配置API密钥："
echo "   cp .env.example .env"
echo "   # 编辑.env文件，填入你的OPENAI_API_KEY"
echo ""
echo "3. 运行应用："
echo "   streamlit run app.py"
echo ""
echo "4. 运行测试："
echo "   pytest tests/"
echo ""
