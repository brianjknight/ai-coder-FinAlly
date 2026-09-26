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
