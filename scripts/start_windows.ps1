<<<<<<< HEAD
# Start the FinAlly container (Windows PowerShell). Idempotent.
# Usage: .\scripts\start_windows.ps1 [-Build] [-NoOpen] [-Port 8000]
[CmdletBinding()]
param(
    [switch]$Build,
    [switch]$NoOpen,
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

$Image = 'finally'
$Container = 'finally'
$Volume = 'finally-data'
$Url = "http://localhost:$Port"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error 'docker is not installed or not on PATH.'
    exit 1
}

if (-not (Test-Path '.env')) {
    if (Test-Path '.env.example') {
        Write-Host 'No .env found - creating one from .env.example (add your OPENROUTER_API_KEY).'
        Copy-Item '.env.example' '.env'
    } else {
        Write-Error '.env file is missing.'
        exit 1
    }
}

# Native command failures should not throw on their own; we check $LASTEXITCODE.
$ErrorActionPreference = 'Continue'

docker image inspect $Image *> $null
$imageExists = ($LASTEXITCODE -eq 0)

if ($Build -or -not $imageExists) {
    Write-Host "Building Docker image '$Image'..."
    docker build -t $Image .
    if ($LASTEXITCODE -ne 0) { Write-Host 'Docker build failed.' -ForegroundColor Red; exit 1 }
}

docker container inspect $Container *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Replacing existing container '$Container'..."
    docker rm -f $Container | Out-Null
}

docker run -d --name $Container -v "${Volume}:/app/db" -p "${Port}:8000" --env-file .env $Image | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host 'Failed to start container.' -ForegroundColor Red; exit 1 }

Write-Host 'Waiting for FinAlly to become healthy...'
$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "$Url/api/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $healthy = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
}

if ($healthy) {
    Write-Host "FinAlly is running at $Url" -ForegroundColor Green
} else {
    Write-Host "Container started but health check has not passed yet. Check: docker logs $Container" -ForegroundColor Yellow
    Write-Host "URL: $Url"
}

if (-not $NoOpen) {
    Start-Process $Url
}
=======
$ErrorActionPreference = "Stop"
$ContainerName = "finally"
$ImageName = "finally"

# Stop existing container if running
docker rm -f $ContainerName 2>$null

# Build if --build flag passed or image doesn't exist
if ($args -contains "--build" -or -not (docker image inspect $ImageName 2>$null)) {
    Write-Host "Building FinAlly Docker image..."
    docker build -t $ImageName .
}

# Run container
docker run -d `
    --name $ContainerName `
    -p 8000:8000 `
    -v finally-data:/app/db `
    --env-file .env `
    $ImageName

Write-Host ""
Write-Host "FinAlly is running at http://localhost:8000"
Write-Host "Stop with: .\scripts\stop_windows.ps1"
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
