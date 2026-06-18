# =============================================================================
# deploy.ps1 — deploy the churn API to Azure Container Apps from PowerShell.
#
# Works on Azure for Students (which BLOCKS ACR Tasks / `az acr build`): instead
# of building in the cloud, it builds the image locally with Docker and pushes
# it to ACR. Requires Docker Desktop running.
#
# PREREQS:
#   1. Azure CLI installed + `az login` done (student subscription selected)
#   2. Docker Desktop installed and RUNNING
#   3. Run from the repo root:
#        powershell -ExecutionPolicy Bypass -File .\deploy\deploy.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

function Check($step) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "FAILED at: $step (exit $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
}

# ---- edit these ----
$RG       = "rg-churn-demo"
$LOCATION = "southeastasia"          # closest region to Sri Lanka
$ACR      = "churnacr$(Get-Random)"  # must be globally unique, lowercase
$APP      = "churn-api"
$ENVNAME  = "churn-env"
$IMAGE    = "churn-api:v1"
# --------------------

Write-Host ">> 1/6 resource group"
az group create --name $RG --location $LOCATION -o none
Check "resource group create"

Write-Host ">> 2/6 container registry"
az acr create --resource-group $RG --name $ACR --sku Basic --admin-enabled true -o none
Check "acr create"
$ACR_SERVER = az acr show --name $ACR --query loginServer -o tsv
Check "acr show"

Write-Host ">> 3/6 build image locally (linux/amd64)"
docker build --platform linux/amd64 -t $IMAGE .
Check "docker build"

Write-Host ">> 4/6 push image to ACR"
az acr login --name $ACR
Check "acr login"
docker tag $IMAGE "$ACR_SERVER/$IMAGE"
Check "docker tag"
docker push "$ACR_SERVER/$IMAGE"
Check "docker push"

Write-Host ">> 5/6 container apps environment (no Log Analytics)"
az containerapp env create --name $ENVNAME --resource-group $RG `
  --location $LOCATION --logs-destination none -o none
Check "containerapp env create"

Write-Host ">> 6/6 deploy app (scale-to-zero)"
$ACR_USER = az acr credential show --name $ACR --query username -o tsv
Check "acr cred username"
$ACR_PASS = az acr credential show --name $ACR --query "passwords[0].value" -o tsv
Check "acr cred password"

az containerapp create `
  --name $APP `
  --resource-group $RG `
  --environment $ENVNAME `
  --image "$ACR_SERVER/$IMAGE" `
  --registry-server $ACR_SERVER `
  --registry-username $ACR_USER `
  --registry-password $ACR_PASS `
  --target-port 8000 `
  --ingress external `
  --min-replicas 0 `
  --max-replicas 2 `
  --cpu 0.5 --memory 1.0Gi `
  -o none
Check "containerapp create"

$URL = az containerapp show --name $APP --resource-group $RG `
  --query properties.configuration.ingress.fqdn -o tsv
Check "containerapp show"

Write-Host ""
Write-Host "==============================================================="
Write-Host " Deployed!  Public URL:  https://$URL"
Write-Host "   health:   https://$URL/health"
Write-Host "   docs:     https://$URL/docs"
Write-Host "==============================================================="
Write-Host ""
Write-Host "Tear down when done (stops billing):"
Write-Host "   az group delete --name $RG --yes --no-wait"
