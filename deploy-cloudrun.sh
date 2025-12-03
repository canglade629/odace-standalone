#!/bin/bash
set -e

# Configuration
PROJECT_ID="icc-project-472009"
REGION="europe-west1"
SERVICE_NAME="odace-backend"

echo "🚀 Deploying ${SERVICE_NAME} to Cloud Run from source"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Deploy directly from source (Cloud Build will build the image)
echo "📦 Building and deploying with Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --source . \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --set-env-vars "ENVIRONMENT=production" \
    --project ${PROJECT_ID}

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment successful!"
echo ""
echo "🌐 Service URL:"
gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --format 'value(status.url)'

