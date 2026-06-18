# =============================================================================
# deploy.ps1 — deploy the churn API to Azure Container Apps from PowerShell.
#
# Native Windows equivalent of deploy.sh — no bash required.
#
# PREREQS:
#   1. Azure CLI installed:  https://aka.ms/installazurecliwindows
#   2. Signed in:            az login
#   3. Run from the repo root:   .\deploy\deploy.ps1
#
# Cost note: Container Apps' monthly free grant + scale-to-zero means a
# low-traffic demo costs ~nothing. ACR Basic has a small monthly fee — delete
# the resource group when done (command printed at the end).
# =============================================================================

$ErrorActionPreference = "Stop"

# ---- edit these ----
$RG       = "rg-churn-demo"
$LOCATION = "southeastasia"          # closest region to Sri Lanka
$ACR      = "churnacr$(Get-Random)"  # must be globally unique, lowercase
$APP      = "churn-api"
$ENVNAME  = "churn-env"
$IMAGE    = "churn-api:v1"
# --------------------

Write-Host ">> 1/5 resource group"
az group create --name $RG --location $LOCATION -o none

Write-Host ">> 2/5 container registry"
az acr create --resource-group $RG --name $ACR --sku Basic --admin-enabled true -o none

Write-Host ">> 3/5 build image in the cloud (no local Docker needed)"
az acr build --registry $ACR --image $IMAGE .

Write-Host ">> 4/5 container apps environment"
az containerapp env create --name $ENVNAME --resource-group $RG --location $LOCATION -o none

Write-Host ">> 5/5 deploy app (scale-to-zero)"
$ACR_SERVER = az acr show --name $ACR --query loginServer -o tsv
$ACR_USER   = az acr credential show --name $ACR --query username -o tsv
$ACR_PASS   = az acr credential show --name $ACR --query "passwords[0].value" -o tsv

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

$URL = az containerapp show --name $APP --resource-group $RG --query properties.configuration.ingress.fqdn -o tsv
Write-Host ""
Write-Host "==============================================================="
Write-Host " Deployed!  Public URL:  https://$URL"
Write-Host "   health:   https://$URL/health"
Write-Host "   docs:     https://$URL/docs"
Write-Host "==============================================================="
Write-Host ""
Write-Host "To avoid charges when done:"
Write-Host "   az group delete --name $RG --yes --no-wait"
