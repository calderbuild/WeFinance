@echo off
REM WeFinance Copilot - 一键启动脚本 (Windows)
REM
REM 使用方法：双击运行或在命令行执行 start.bat

echo ================================================
echo WeFinance Copilot - 启动应用
echo ================================================
echo.

REM 检查conda是否安装
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 错误：未检测到conda
    echo    请先运行 setup_conda_env.bat 安装环境
    pause
    exit /b 1
)

REM 检查环境是否存在
conda env list | findstr /C:"wefinance" >nul
if %errorlevel% neq 0 (
    echo ❌ 错误：wefinance环境未安装
    echo    请先运行 setup_conda_env.bat 安装环境
    pause
    exit /b 1
)

REM 检查.env文件
if not exist ".env" (
    echo ⚠️  警告：未找到.env文件
    echo    请复制.env.example并配置API密钥：
    echo    copy .env.example .env
    echo    然后编辑.env文件填入OPENAI_API_KEY
    echo.
    set /p CONTINUE="是否继续启动？[y/N]: "
    if /i not "!CONTINUE!"=="y" (
        exit /b 1
    )
)

echo 🚀 激活conda环境...
call conda activate wefinance

echo ✅ 环境已激活: wefinance
echo.

echo 🌐 启动Streamlit应用...
echo    访问地址: http://localhost:8501
echo    按Ctrl+C停止应用
echo.

REM 启动应用
streamlit run app.py --server.port 8501
