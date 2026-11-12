# 局域网演示：让同一局域网内的其他电脑用浏览器访问本机看板
# 用法：双击「局域网演示.bat」

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  局域网演示模式（别人电脑用浏览器访问）" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[提示] 还没建虚拟环境，请先双击「启动看板.bat」" -ForegroundColor Yellow
    exit 1
}

$ips = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254*" } |
    Select-Object -ExpandProperty IPAddress)

Write-Host "本机局域网地址（对方电脑用浏览器打开下面任意一个）：" -ForegroundColor Green
foreach ($ip in $ips) {
    Write-Host ("   http://{0}:8501" -f $ip) -ForegroundColor Green
}
Write-Host ""
Write-Host "前提：对方电脑与本机连同一个 Wi-Fi/局域网，并且本机防火墙放行 TCP 8501。" -ForegroundColor DarkGray
Write-Host ""

# 尝试添加防火墙入站规则（需要管理员权限，失败不影响启动）
$rule = netsh advfirewall firewall add rule name="Streamlit-8501" dir=in action=allow protocol=TCP localport=8501 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] 防火墙规则已添加（TCP 8501 入站放行）" -ForegroundColor Green
} else {
    Write-Host "[注意] 未能自动添加防火墙规则（需要管理员权限）。若对方打不开，请手动放行 TCP 8501。" -ForegroundColor Yellow
}
Write-Host ""

if ($env:NOBROWSER -ne "1") {
    Start-Process "http://127.0.0.1:8501"
}
Write-Host "正在启动服务，关闭窗口或按 Ctrl+C 可停止……" -ForegroundColor Cyan
Write-Host ""

& $venvPython -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
