@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ===============================================
echo   沃尔玛客户购买行为数据分析与可视化
echo ===============================================
echo.

if exist ".venv\Scripts\python.exe" goto :run

echo [1/3] 未发现虚拟环境，正在创建...
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m venv .venv
) else (
    python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 创建虚拟环境失败，请先安装 Python 3.10 以上版本。
    pause
    exit /b 1
)

echo [2/3] 正在安装依赖（需要联网，约 1-3 分钟）...
".venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

:run
echo [3/3] 正在启动看板，稍后浏览器会自动打开 http://localhost:8501
echo       关闭本窗口即可停止看板。
echo.
".venv\Scripts\python.exe" -m streamlit run app.py

pause
