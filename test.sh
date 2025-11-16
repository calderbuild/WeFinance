#!/bin/bash
# WeFinance Copilot - 一键测试脚本
#
# 使用方法：
#   chmod +x test.sh
#   ./test.sh

set -e  # 遇到错误立即退出

echo "================================================"
echo "WeFinance Copilot - 运行测试套件"
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

echo "🚀 激活conda环境..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate wefinance

echo "✅ 环境已激活: wefinance"
echo ""

# 运行代码格式化检查
echo "📝 检查代码格式 (black)..."
if command -v black &> /dev/null
then
    black --check . || {
        echo "⚠️  代码格式不符合规范"
        echo "   运行 'black .' 自动格式化"
    }
    echo "✅ 代码格式检查完成"
else
    echo "⚠️  black未安装，跳过格式化检查"
fi
echo ""

# 运行代码质量检查
echo "🔍 检查代码质量 (ruff)..."
if command -v ruff &> /dev/null
then
    ruff check . || {
        echo "⚠️  发现代码质量问题"
        echo "   运行 'ruff check --fix .' 自动修复部分问题"
    }
    echo "✅ 代码质量检查完成"
else
    echo "⚠️  ruff未安装，跳过质量检查"
fi
echo ""

# 运行单元测试
echo "🧪 运行单元测试..."
pytest tests/ -v

echo ""
echo "================================================"
echo "✅ 测试完成！"
echo "================================================"
echo ""
echo "可选：运行覆盖率测试"
echo "   pytest --cov=modules --cov=services --cov=utils --cov-report=term-missing"
echo ""
