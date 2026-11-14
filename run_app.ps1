# 启动看板：自动找可用的 Python 虚拟环境，然后运行 Streamlit
# 用法：双击「启动看板.bat」（它只是调用本脚本，避免批处理的中文编码问题）

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  沃尔玛客户购买行为数据分析与可视化" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# 1) 本目录 .venv
$python = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path $python) {
    Write-Host "[1/3] 使用本目录的虚拟环境" -ForegroundColor Green
}
else {
    # 2) 同级「大数据实训」的 .venv
    $candidate = Join-Path $root "..\大数据实训\.venv\Scripts\python.exe"
    if (Test-Path $candidate) {
        $python = (Resolve-Path $candidate).Path
        Write-Host "[1/3] 使用同级「大数据实训」的虚拟环境" -ForegroundColor Green
    }
    else {
        Write-Host "[1/3] 未发现虚拟环境，正在创建……" -ForegroundColor Yellow
        $created = $false
        foreach ($exe in @("py", "python")) {
            $cmd = Get-Command $exe -ErrorAction SilentlyContinue
            if (-not $cmd) { continue }
            if ($exe -eq "py") { & py -3 -m venv .venv } else { & python -m venv .venv }
            if (Test-Path $python) { $created = $true; break }
        }
        if (-not $created) {
            Write-Host "[错误] 创建虚拟环境失败，请先安装 Python 3.10+" -ForegroundColor Red
            exit 1
        }
        Write-Host "[2/3] 安装依赖（需要联网，约 1-3 分钟）……" -ForegroundColor Yellow
        & $python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    }
}

Write-Host "[3/3] 启动看板，稍后浏览器会自动打开 http://localhost:8501" -ForegroundColor Cyan
Write-Host "      关闭本窗口即可停止看板。" -ForegroundColor DarkGray
Write-Host ""
& $python -m streamlit run app.py
