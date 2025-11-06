@echo off
REM WeFinance Copilot - Conda环境安装脚本 (Windows)
REM
REM 使用方法：双击运行或在命令行执行 setup_conda_env.bat

echo ================================================
echo WeFinance Copilot - Conda环境安装
echo ================================================
echo.

REM 检查conda是否安装
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 错误：未检测到conda，请先安装Miniconda或Anaconda
    echo    下载地址：
    echo    - Miniconda: https://docs.conda.io/en/latest/miniconda.html
    echo    - Anaconda: https://www.anaconda.com/products/distribution
    pause
    exit /b 1
)

echo ✅ 检测到conda
conda --version
echo.

REM 检查environment.yml是否存在
if not exist "environment.yml" (
    echo ❌ 错误：未找到environment.yml文件
    echo    请确保在项目根目录下运行此脚本
    pause
    exit /b 1
)

echo 📋 配置文件：environment.yml
echo.

REM 询问是否配置国内镜像源
set /p MIRROR="是否配置清华镜像源（推荐国内用户）？[y/N]: "
if /i "%MIRROR%"=="y" (
    echo ⚙️  配置清华镜像源...
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/
    conda config --set show_channel_urls yes
    echo ✅ 镜像源配置完成
    echo.
)

REM 检查环境是否已存在
conda env list | findstr /C:"wefinance" >nul
if %errorlevel% equ 0 (
    echo ⚠️  检测到wefinance环境已存在
    set /p REBUILD="是否删除并重建？[y/N]: "
    if /i "!REBUILD!"=="y" (
        echo 🗑️  删除旧环境...
        conda env remove -n wefinance -y
        echo ✅ 旧环境已删除
        echo.
    ) else (
        echo ℹ️  将更新现有环境
        echo.
    )
)

REM 创建或更新环境
echo 📦 安装依赖包（这可能需要几分钟）...
echo.

conda env list | findstr /C:"wefinance" >nul
if %errorlevel% equ 0 (
    REM 更新现有环境
    conda env update -f environment.yml --prune
) else (
    REM 创建新环境
    conda env create -f environment.yml
)

echo.
echo ✅ 环境安装完成！
echo.

REM 验证安装
echo 🔍 验证安装...
call conda activate wefinance

python --version
echo.

REM 检查关键包
echo 📋 关键包验证：
python -c "import streamlit; print(f'   ✅ streamlit {streamlit.__version__}')" 2>nul || echo    ❌ streamlit 安装失败
python -c "import paddleocr; print('   ✅ paddleocr installed')" 2>nul || echo    ❌ paddleocr 安装失败
python -c "import pandas; print(f'   ✅ pandas {pandas.__version__}')" 2>nul || echo    ❌ pandas 安装失败
python -c "import openai; print(f'   ✅ openai {openai.__version__}')" 2>nul || echo    ❌ openai 安装失败
python -c "import langchain; print(f'   ✅ langchain {langchain.__version__}')" 2>nul || echo    ❌ langchain 安装失败

echo.
echo ================================================
echo 🎉 安装成功！
echo ================================================
echo.
echo 下一步操作：
echo 1. 激活环境：
echo    conda activate wefinance
echo.
echo 2. 配置API密钥：
echo    copy .env.example .env
echo    REM 编辑.env文件，填入你的OPENAI_API_KEY
echo.
echo 3. 运行应用：
echo    streamlit run app.py
echo.
echo 4. 运行测试：
echo    pytest tests/
echo.
pause
