@echo off
REM WeFinance Copilot - 一键测试脚本 (Windows)
REM
REM 使用方法：双击运行或在命令行执行 test.bat

echo ================================================
echo WeFinance Copilot - 运行测试套件
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

echo 🚀 激活conda环境...
call conda activate wefinance

echo ✅ 环境已激活: wefinance
echo.

REM 运行代码格式化检查
echo 📝 检查代码格式 (black)...
where black >nul 2>nul
if %errorlevel% equ 0 (
    black --check . 2>nul || (
        echo ⚠️  代码格式不符合规范
        echo    运行 'black .' 自动格式化
    )
    echo ✅ 代码格式检查完成
) else (
    echo ⚠️  black未安装，跳过格式化检查
)
echo.

REM 运行代码质量检查
echo 🔍 检查代码质量 (ruff)...
where ruff >nul 2>nul
if %errorlevel% equ 0 (
    ruff check . 2>nul || (
        echo ⚠️  发现代码质量问题
        echo    运行 'ruff check --fix .' 自动修复部分问题
    )
    echo ✅ 代码质量检查完成
) else (
    echo ⚠️  ruff未安装，跳过质量检查
)
echo.

REM 运行单元测试
echo 🧪 运行单元测试...
pytest tests/ -v

echo.
echo ================================================
echo ✅ 测试完成！
echo ================================================
echo.
echo 可选：运行覆盖率测试
echo    pytest --cov=modules --cov=services --cov=utils --cov-report=term-missing
echo.

pause
