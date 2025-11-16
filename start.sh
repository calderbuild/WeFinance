#!/bin/bash
# WeFinance Copilot - 一键启动脚本
#
# 使用方法：
#   chmod +x start.sh
#   ./start.sh

set -e  # 遇到错误立即退出

echo "================================================"
echo "WeFinance Copilot - 启动应用"
echo "================================================"
echo ""

# 检查conda是否安装
if ! command -v conda &> /dev/null
then
    echo "❌ 错误：未检测到conda"
    echo "   请先运行 ./setup_conda_env.sh 安装环境"
    exit 1
fi

# 检查环境是否存在
if ! conda env list | grep -q "^wefinance "; then
    echo "❌ 错误：wefinance环境未安装"
    echo "   请先运行 ./setup_conda_env.sh 安装环境"
    exit 1
fi

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "⚠️  警告：未找到.env文件"
    echo "   请复制.env.example并配置API密钥："
    echo "   cp .env.example .env"
    echo "   然后编辑.env文件填入OPENAI_API_KEY"
    echo ""
    read -p "是否继续启动？[y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]
    then
        exit 1
    fi
fi

echo "🚀 激活conda环境..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate wefinance

echo "✅ 环境已激活: wefinance"
echo ""

echo "🌐 启动Streamlit应用..."
echo "   访问地址: http://localhost:8501"
echo "   按Ctrl+C停止应用"
echo ""

# 启动应用
streamlit run app.py --server.port 8501
