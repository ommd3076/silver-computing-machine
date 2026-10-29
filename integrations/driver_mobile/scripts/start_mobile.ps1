# DebugLeaf Driver Mobile Integration - Expo Mobile App Startup Script (PowerShell)
# Launches Expo Metro bundler for physical phone testing via Expo Go

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MobileDir = (Resolve-Path "$ScriptDir\..\mobile").Path
Set-Location $MobileDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " STARTING DEBUGLEAF EXPO MOBILE APPLICATION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Discover Host IP
$HostIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi*", "Ethernet*" -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } | Select-Object -First 1).IPAddress
if (-not $HostIP) { $HostIP = "127.0.0.1" }

$env:EXPO_PUBLIC_API_URL = "http://${HostIP}:8000/api/v1/demo"
Write-Host "[*] Mobile API Target: $env:EXPO_PUBLIC_API_URL" -ForegroundColor Green

# 2. Check Node / npm availability
$NodeCmd = Get-Command "node" -ErrorAction SilentlyContinue
if (-not $NodeCmd) {
    Write-Host "`n[!] Node.js is not detected on PATH." -ForegroundColor Yellow
    Write-Host "    To run Metro bundler for Expo Go on physical phones, install Node.js (LTS v20+)." -ForegroundColor White
    Write-Host "    After installing Node.js:" -ForegroundColor White
    Write-Host "      1. cd integrations/driver_mobile/mobile" -ForegroundColor White
    Write-Host "      2. npm install" -ForegroundColor White
    Write-Host "      3. npx expo start --lan" -ForegroundColor White
    Write-Host "      4. Scan QR code using Expo Go on Phone A and Phone B" -ForegroundColor White
    exit 0
}

Write-Host "[*] Node version: $((node -v))" -ForegroundColor Green
if (-not (Test-Path "node_modules")) {
    Write-Host "[*] Installing dependencies with npm..." -ForegroundColor Cyan
    npm install
}

Write-Host "`nStarting Expo Metro Bundler in LAN mode..." -ForegroundColor Cyan
npx expo start --lan
