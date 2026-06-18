# =============================================================================
# deploy-frontend.ps1 — deploy the Streamlit web UI to Azure Container Apps.
#
# Reuses the resource group, ACR, and Container Apps environment created by the
# API deploy (deploy.ps1). Auto-discovers the existing ACR and the API's URL, so
# you don't hardcode anything. Builds the frontend image locally and pushes it
# (ACR Tasks is blocked on the student tier).
#
# PREREQS: the API must already be deployed (deploy.ps1 done), Docker running,
#          az login done. Run from repo root:
#   powershell -ExecutionPolicy Bypass -File .\deploy\deploy-frontend.ps1
# =============================================================================

$ErrorActionPreference = "Stop"
function Check($step) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nFAILED at: $step (exit $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
}

# ---- fixed names (must match deploy.ps1) ----
$RG      = "rg-churn-demo"
$ENVNAME = "churn-env"
$APIAPP  = "churn-api"
$APP     = "churn-ui"
$IMAGE   = "churn-ui:v1"
# ---------------------------------------------

Write-Host ">> 1/5 discover existing ACR in $RG"
$ACR = az acr list --resource-group $RG --query "[0].name" -o tsv
Check "acr list"
if ([string]::IsNullOrWhiteSpace($ACR)) {
    Write-Host "No ACR found in $RG. Deploy the API first (deploy.ps1)." -ForegroundColor Red
    exit 1
}
$ACR_SERVER = az acr show --name $ACR --query loginServer -o tsv
Check "acr show"
Write-Host "   using ACR: $ACR_SERVER"

Write-Host ">> 2/5 discover the API URL"
$API_FQDN = az containerapp show --name $APIAPP --resource-group $RG `
  --query properties.configuration.ingress.fqdn -o tsv
Check "api show"
$API_URL = "https://$API_FQDN"
Write-Host "   API_URL: $API_URL"

Write-Host ">> 3/5 build frontend image locally (linux/amd64)"
docker build --platform linux/amd64 -t $IMAGE .\frontend
Check "docker build"

Write-Host ">> 4/5 push image to ACR"
az acr login --name $ACR
Check "acr login"
docker tag $IMAGE "$ACR_SERVER/$IMAGE"
Check "docker tag"
docker push "$ACR_SERVER/$IMAGE"
Check "docker push"

Write-Host ">> 5/5 deploy frontend app (passes API_URL as env var)"
$ACR_USER = az acr credential show --name $ACR --query username -o tsv
Check "acr cred user"
$ACR_PASS = az acr credential show --name $ACR --query "passwords[0].value" -o tsv
Check "acr cred pass"

az containerapp create `
  --name $APP `
  --resource-group $RG `
  --environment $ENVNAME `
  --image "$ACR_SERVER/$IMAGE" `
  --registry-server $ACR_SERVER `
  --registry-username $ACR_USER `
  --registry-password $ACR_PASS `
  --target-port 8501 `
  --ingress external `
  --min-replicas 0 `
  --max-replicas 2 `
  --cpu 0.5 --memory 1.0Gi `
  --env-vars "API_URL=$API_URL" `
  -o none
Check "containerapp create"

$URL = az containerapp show --name $APP --resource-group $RG `
  --query properties.configuration.ingress.fqdn -o tsv
Check "containerapp show"

Write-Host ""
Write-Host "==============================================================="
Write-Host " Web UI deployed!  Open:  https://$URL"
Write-Host "==============================================================="
Write-Host ""
Write-Host "It calls the API at: $API_URL"
