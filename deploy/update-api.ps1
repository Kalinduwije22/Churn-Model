# =============================================================================
# update-api.ps1 — roll a new version of the churn-api image into the EXISTING
# Container App, keeping the same public URL.
#
# Use this after changing the API or the web UI (app/templates/index.html).
# Rebuilds locally, pushes a fresh tag, and updates the running app in place.
#
# PREREQS: API already deployed, Docker running, az login done.
#   powershell -ExecutionPolicy Bypass -File .\deploy\update-api.ps1
# =============================================================================
$ErrorActionPreference = "Stop"
function Check($s){ if($LASTEXITCODE -ne 0){Write-Host "`nFAILED at: $s" -ForegroundColor Red; exit 1} }

$RG  = "rg-churn-demo"
$APP = "churn-api"
$TAG = "v" + (Get-Date -Format "yyyyMMddHHmm")   # unique tag forces a new revision

Write-Host ">> discover ACR"
$ACR = az acr list --resource-group $RG --query "[0].name" -o tsv; Check "acr list"
$ACR_SERVER = az acr show --name $ACR --query loginServer -o tsv; Check "acr show"
$IMG = "$ACR_SERVER/churn-api:$TAG"

Write-Host ">> build $IMG"
docker build --platform linux/amd64 -t $IMG .; Check "docker build"

Write-Host ">> push"
az acr login --name $ACR; Check "acr login"
docker push $IMG; Check "docker push"

Write-Host ">> update the running app to the new image"
az containerapp update --name $APP --resource-group $RG --image $IMG -o none; Check "containerapp update"

$URL = az containerapp show --name $APP --resource-group $RG `
  --query properties.configuration.ingress.fqdn -o tsv; Check "show"
Write-Host ""
Write-Host "Updated. Same URL, new version live:  https://$URL"
