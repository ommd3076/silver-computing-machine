# DebugLeaf Driver Mobile Integration - Server Startup Script (PowerShell)
# Launches unified FastAPI ASGI application on host 0.0.0.0:8000

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path "$ScriptDir\..\..\..").Path
Set-Location $RepoRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " STARTING DEBUGLEAF UNIFIED ASGI SERVER" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Environment variables defaults for demo
if (-not $env:DEBUGLEAF_AUTH_MODE) { $env:DEBUGLEAF_AUTH_MODE = "token" }
if (-not $env:DEBUGLEAF_DISPATCHER_TOKEN) { $env:DEBUGLEAF_DISPATCHER_TOKEN = "DEBUGLEAF_DISPATCHER_SECRET_KEY_9988" }
if (-not $env:DEBUGLEAF_ADMIN_TOKEN) { $env:DEBUGLEAF_ADMIN_TOKEN = "DEBUGLEAF_ADMIN_SECRET_KEY_7766" }
if (-not $env:DEBUGLEAF_RESEARCHER_TOKEN) { $env:DEBUGLEAF_RESEARCHER_TOKEN = "DEBUGLEAF_RESEARCHER_SECRET_KEY_5544" }
if (-not $env:DEBUGLEAF_DEMO_FIXTURE_MODE) { $env:DEBUGLEAF_DEMO_FIXTURE_MODE = "1" }

# 2. Run Preflight Diagnostics
& ".\.venv\Scripts\python.exe" "integrations\driver_mobile\scripts\preflight.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Preflight checks failed. Aborting startup." -ForegroundColor Red
    exit 1
}

# 3. Discover Host IP
$HostIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi*", "Ethernet*" -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } | Select-Object -First 1).IPAddress
if (-not $HostIP) { $HostIP = "127.0.0.1" }

Write-Host "`n[*] Server Listening at:" -ForegroundColor Green
Write-Host "    Local:   http://localhost:8000/api/v1/demo" -ForegroundColor White
Write-Host "    Network: http://${HostIP}:8000/api/v1/demo" -ForegroundColor White
Write-Host "    OpenAPI: http://${HostIP}:8000/api/v1/demo/openapi.json" -ForegroundColor White
Write-Host "    Docs:    http://${HostIP}:8000/api/v1/demo/docs" -ForegroundColor White
Write-Host "`n[*] Dispatcher Bearer Token: $env:DEBUGLEAF_DISPATCHER_TOKEN" -ForegroundColor Yellow
Write-Host "[*] Demo Pairing Codes:       PAIR01 (Driver 1), PAIR02 (Driver 2)" -ForegroundColor Yellow

Write-Host "`nLaunching Uvicorn single worker process..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m uvicorn integrations.driver_mobile.server.app:app --host 0.0.0.0 --port 8000
