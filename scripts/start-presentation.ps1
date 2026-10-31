[CmdletBinding()]
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendPython = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"
$frontendRoot = Join-Path $projectRoot "frontend"
$runRoot = Join-Path $env:TEMP "netrca-presentation"

if (-not (Test-Path -LiteralPath $backendPython)) {
    throw "Backend virtual environment is missing. Run the backend setup in README.md first."
}
if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot "node_modules"))) {
    throw "Frontend dependencies are missing. Run npm install in the frontend folder first."
}

New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

function Get-ListeningProcess([int]$Port) {
    Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty OwningProcess
}

$backendOwner = Get-ListeningProcess 8000
$frontendOwner = Get-ListeningProcess 3000
if ($backendOwner -or $frontendOwner) {
    $details = @()
    if ($backendOwner) { $details += "port 8000 (PID $backendOwner)" }
    if ($frontendOwner) { $details += "port 3000 (PID $frontendOwner)" }
    throw "NetRCA presentation ports are already in use: $($details -join ', '). Close the existing terminals or run scripts\stop-presentation.ps1, then retry."
}

$backendOut = Join-Path $runRoot "backend.log"
$backendErr = Join-Path $runRoot "backend-error.log"
$frontendOut = Join-Path $runRoot "frontend.log"
$frontendErr = Join-Path $runRoot "frontend-error.log"

$backend = Start-Process -FilePath $backendPython `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory (Join-Path $projectRoot "backend") -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr

$env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000/api/v1"
$env:NEXT_PUBLIC_NETRCA_PRESENTATION_MODE = "true"
$frontend = Start-Process -FilePath "npm.cmd" `
    -ArgumentList @("run", "dev", "--", "--hostname", "127.0.0.1", "--port", "3000") `
    -WorkingDirectory $frontendRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr

Set-Content -LiteralPath (Join-Path $runRoot "backend.pid") -Value $backend.Id
Set-Content -LiteralPath (Join-Path $runRoot "frontend.pid") -Value $frontend.Id

function Wait-ForUrl([string]$Url, [int]$Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) { return $true }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

$backendReady = Wait-ForUrl "http://127.0.0.1:8000/api/v1/health" 20
$frontendReady = Wait-ForUrl "http://127.0.0.1:3000" 45

if (-not $backendReady -or -not $frontendReady) {
    Write-Host "Presentation startup did not complete." -ForegroundColor Red
    Write-Host "Backend log: $backendErr"
    Write-Host "Frontend log: $frontendErr"
    exit 1
}

Write-Host "NetRCA presentation is ready." -ForegroundColor Green
Write-Host "Dashboard: http://127.0.0.1:3000"
Write-Host "API health: http://127.0.0.1:8000/api/v1/health"
Write-Host "Mode: synthetic browser-only presentation data; no remote database writes"
Write-Host "Stop: .\scripts\stop-presentation.ps1"

if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:3000"
}
