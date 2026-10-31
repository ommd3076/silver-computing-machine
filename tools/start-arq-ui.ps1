[CmdletBinding()]
param(
    [switch]$Lan,
    [ValidateSet('Web', 'Native', 'Both')]
    [string]$ExpoMode = 'Web'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$uiRepo = Join-Path $repo 'nmit-frontend'
$viteDir = Join-Path $uiRepo 'frontend'
$expoDir = Join-Path $uiRepo 'apps\driver-mobile'
$runId = Get-Date -Format 'yyyyMMdd-HHmmss'
$runtimeDir = Join-Path $repo ".runtime\arq-ui\$runId"
$logDir = Join-Path $runtimeDir 'logs'
$manifestPath = Join-Path $runtimeDir 'processes.json'

function Test-LocalPort([int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $pending = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        return $pending.AsyncWaitHandle.WaitOne(250) -and $client.Connected
    } catch { return $false }
    finally { $client.Dispose() }
}

function Get-PrivateLanAddress {
    $candidates = Get-NetIPConfiguration | Where-Object {
        $_.NetAdapter.Status -eq 'Up' -and $_.IPv4DefaultGateway
    } | ForEach-Object { $_.IPv4Address } | Where-Object {
        $_ -and ($_.IPAddress -like '10.*' -or $_.IPAddress -match '^192\.168\.' -or
            $_.IPAddress -match '^172\.(1[6-9]|2[0-9]|3[01])\.')
    }
    foreach ($candidate in $candidates) { return $candidate.IPAddress }
    throw 'Could not find an active IPv4 address with a default gateway. Connect to the intended LAN and retry.'
}

function Assert-TokenEnvironment {
    $names = @('DEBUGLEAF_DISPATCHER_TOKEN', 'DEBUGLEAF_RESEARCHER_TOKEN', 'DEBUGLEAF_ADMIN_TOKEN')
    $values = @()
    foreach ($name in $names) {
        $item = Get-Item -Path "Env:$name" -ErrorAction SilentlyContinue
        if (-not $item -or [string]::IsNullOrEmpty($item.Value)) {
            throw "LAN mode requires $name in the launching shell. Values are not displayed or written by this script."
        }
        $values += $item.Value
    }
    if (@($values | Select-Object -Unique).Count -ne 3) {
        throw 'LAN mode requires three distinct role tokens. Values are not displayed or written by this script.'
    }
}

function Start-LoggedProcess([string]$Name, [string]$File, [string[]]$Arguments, [string]$WorkingDirectory) {
    $outLog = Join-Path $logDir "$Name.out.log"
    $errLog = Join-Path $logDir "$Name.err.log"
    $proc = Start-Process -FilePath $File -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput $outLog -RedirectStandardError $errLog
    return [ordered]@{ name = $Name; pid = $proc.Id; startedAt = (Get-Date).ToString('o'); stdout = $outLog; stderr = $errLog }
}

if (-not (Test-Path -LiteralPath (Join-Path $viteDir 'node_modules\.bin\vite.cmd'))) { throw 'Missing web dependencies. Run npm ci in nmit-frontend/frontend first.' }
if (-not (Test-Path -LiteralPath (Join-Path $expoDir 'node_modules\.bin\expo.cmd'))) { throw 'Missing Expo dependencies. Run npm ci in nmit-frontend/apps/driver-mobile first.' }

$ports = @(5173)
if ($ExpoMode -in @('Web', 'Both')) { $ports += 8082 }
if ($ExpoMode -in @('Native', 'Both')) { $ports += 8081 }
$busyPorts = @($ports | Where-Object { Test-LocalPort $_ })
if ($busyPorts.Count) { throw "Port(s) already have a localhost listener: $($busyPorts -join ', '). Stop the existing service or choose a free port before starting this stack." }

$hostAddress = '127.0.0.1'
$displayHost = '127.0.0.1'
if ($Lan) {
    Assert-TokenEnvironment
    $hostAddress = '0.0.0.0'
    $displayHost = Get-PrivateLanAddress
    $apiForClient = "http://${displayHost}:8001"
} else {
    $apiForClient = 'http://127.0.0.1:8001'
}

New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$oldApiTarget = $env:ARQ_API_TARGET
$oldExpoApiUrl = $env:EXPO_PUBLIC_API_URL
$processes = @()
try {
    $env:ARQ_API_TARGET = $apiForClient
    $processes += Start-LoggedProcess 'vite' 'npm.cmd' @('run', 'dev', '--', '--host', $hostAddress, '--port', '5173', '--strictPort') $viteDir

    if ($ExpoMode -in @('Web', 'Both')) {
        $env:EXPO_PUBLIC_API_URL = $apiForClient
        $expoHost = if ($Lan) { 'lan' } else { 'localhost' }
        $processes += Start-LoggedProcess 'expo-web' 'npm.cmd' @('run', 'web', '--', '--host', $expoHost, '--port', '8082') $expoDir
    }
    if ($ExpoMode -in @('Native', 'Both')) {
        # In local mode, the Android emulator reaches the coordinator's API via 10.0.2.2.
        $env:EXPO_PUBLIC_API_URL = if ($Lan) { $apiForClient } else { 'http://10.0.2.2:8001' }
        $processes += Start-LoggedProcess 'expo-native' 'npm.cmd' @('start', '--', '--lan', '--port', '8081') $expoDir
    }
} catch {
    foreach ($proc in $processes) {
        try { & taskkill.exe /PID $proc.pid /T /F 2>$null | Out-Null } catch { }
    }
    throw
} finally {
    if ($null -eq $oldApiTarget) { Remove-Item Env:ARQ_API_TARGET -ErrorAction SilentlyContinue } else { $env:ARQ_API_TARGET = $oldApiTarget }
    if ($null -eq $oldExpoApiUrl) { Remove-Item Env:EXPO_PUBLIC_API_URL -ErrorAction SilentlyContinue } else { $env:EXPO_PUBLIC_API_URL = $oldExpoApiUrl }
}

$processes | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Host "Run data and logs: $runtimeDir"
Write-Host "API:      http://${displayHost}:8001 (coordinator-managed; not started here)"
Write-Host "Vite:     http://${displayHost}:5173"
if ($ExpoMode -in @('Web', 'Both')) { Write-Host "Expo web: http://${displayHost}:8082" }
if ($ExpoMode -in @('Native', 'Both')) { Write-Host 'Expo native: Metro on port 8081; open the Expo Go URL from logs/expo-native.out.log' }
Write-Host "Process manifest: $manifestPath"
Write-Host 'Pairing codes for this isolated demo database: PAIR01 and PAIR02 (each can be redeemed once).'
Write-Host 'The API service and its database are coordinator-managed; this script does not reset or remove data.'
