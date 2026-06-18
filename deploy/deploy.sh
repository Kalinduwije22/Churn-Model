#!/usr/bin/env bash
# =============================================================================
# deploy.sh — deploy the churn API to Azure Container Apps (free-tier friendly).
#
# What it does:
#   1. creates a resource group
#   2. creates an Azure Container Registry (ACR) and builds the image IN the
#      cloud (so you don't need Docker working locally for the cloud build)
#   3. creates a Container Apps environment
#   4. deploys the app with scale-to-zero (min replicas = 0)
#
# Cost: Container Apps' monthly free grant (180k vCPU-s, 360k GiB-s, 2M reqs)
# plus scale-to-zero means a low-traffic demo costs ~nothing. ACR Basic has a
# small monthly fee (~$5) — delete it after pushing, or use the $200 credit.
#
# PREREQS: Azure CLI installed + `az login` done. Run from the repo root.
# Run:  bash deploy/deploy.sh
# =============================================================================
set -euo pipefail

# ---- edit these ----
RG="rg-churn-demo"
LOCATION="southeastasia"          # closest region to Sri Lanka
ACR="churnacr$RANDOM"             # must be globally unique, lowercase
APP="churn-api"
ENV="churn-env"
IMAGE="churn-api:v1"
# --------------------

echo ">> 1/5 resource group"
az group create --name "$RG" --location "$LOCATION" -o none

echo ">> 2/5 container registry"
az acr create --resource-group "$RG" --name "$ACR" --sku Basic --admin-enabled true -o none

echo ">> 3/5 build image in the cloud (no local Docker needed)"
az acr build --registry "$ACR" --image "$IMAGE" . 

echo ">> 4/5 container apps environment"
az containerapp env create --name "$ENV" --resource-group "$RG" --location "$LOCATION" -o none

echo ">> 5/5 deploy app (scale-to-zero)"
ACR_SERVER=$(az acr show --name "$ACR" --query loginServer -o tsv)
ACR_USER=$(az acr credential show --name "$ACR" --query username -o tsv)
ACR_PASS=$(az acr credential show --name "$ACR" --query 'passwords[0].value' -o tsv)

az containerapp create \
  --name "$APP" \
  --resource-group "$RG" \
  --environment "$ENV" \
  --image "$ACR_SERVER/$IMAGE" \
  --registry-server "$ACR_SERVER" \
  --registry-username "$ACR_USER" \
  --registry-password "$ACR_PASS" \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 2 \
  --cpu 0.5 --memory 1.0Gi \
  -o none

URL=$(az containerapp show --name "$APP" --resource-group "$RG" --query properties.configuration.ingress.fqdn -o tsv)
echo
echo "==============================================================="
echo " Deployed!  Public URL:  https://$URL"
echo "   health:   https://$URL/health"
echo "   docs:     https://$URL/docs"
echo "==============================================================="
echo
echo "To avoid charges when done:"
echo "   az group delete --name $RG --yes --no-wait"
