# FreshGuard Local Multi-Service Runner (PowerShell)
param (
    [switch]$NoFrontend,
    [switch]$WithBifrost,
    [int]$Port = 8000
)

$RootDir = Split-Path -Parent $PSScriptRoot
$VerifDir = Join-Path $RootDir "verification-service"
$FrontendDir = Join-Path $RootDir "frontend"
$ExamplesDir = Join-Path $RootDir "examples"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🛡️  FreshGuard System Pre-Flight Check" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Python check
$pyVer = python --version 2>&1
Write-Host "  [✓] Python Runtime: $pyVer" -ForegroundColor Green

# 2. Node check
$nodeVer = node -v 2>&1
Write-Host "  [✓] Node.js Runtime: $nodeVer" -ForegroundColor Green

# 3. Go check
$goVer = go version 2>&1
Write-Host "  [✓] Go Runtime: $goVer" -ForegroundColor Green

Write-Host "============================================================`n" -ForegroundColor Cyan

$processes = @()

# 1. Start Python verification service
Write-Host "🚀 Starting Python Verification Service on http://127.0.0.1:$Port..." -ForegroundColor Yellow
$pyProc = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port" -WorkingDirectory $VerifDir -PassThru
$processes += $pyProc

# 2. Start Frontend
if (-not $NoFrontend) {
    Write-Host "🎨 Starting Frontend Dev Server on http://localhost:3000..." -ForegroundColor Yellow
    $frontProc = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory $FrontendDir -PassThru
    $processes += $frontProc
}

Write-Host "`n✨ FreshGuard is running!" -ForegroundColor Green
Write-Host "   • Verification API:  http://127.0.0.1:$Port"
Write-Host "   • API Documentation: http://127.0.0.1:$Port/docs"
Write-Host "   • Verification UI:   http://localhost:3000"
Write-Host "`nPress Enter or terminate this script to stop all services..."

Read-Host

Write-Host "`n🛑 Stopping FreshGuard services..." -ForegroundColor Red
foreach ($p in $processes) {
    try {
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    } catch {}
}
Write-Host "✓ All FreshGuard services stopped." -ForegroundColor Green

