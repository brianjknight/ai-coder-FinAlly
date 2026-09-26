<<<<<<< HEAD
# Stop and remove the FinAlly container (Windows PowerShell). Idempotent.
# The 'finally-data' volume is NOT removed, so your data persists.
$Container = 'finally'

docker container inspect $Container *> $null
if ($LASTEXITCODE -eq 0) {
    docker rm -f $Container | Out-Null
    Write-Host "FinAlly container stopped and removed. Data volume 'finally-data' preserved."
} else {
    Write-Host 'FinAlly container is not running.'
}
=======
$ErrorActionPreference = "Stop"
$ContainerName = "finally"

docker stop $ContainerName 2>$null
if ($?) { Write-Host "FinAlly stopped." } else { Write-Host "FinAlly is not running." }
docker rm $ContainerName 2>$null
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
