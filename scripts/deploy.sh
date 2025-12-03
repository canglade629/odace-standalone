#!/bin/bash
# Deployment script for Odace Data Pipeline using local Docker

set -e

# Configuration
PROJECT_ID="icc-project-472009"
REGION="europe-west1"
SERVICE_NAME="odace-pipeline"
ARTIFACT_REGISTRY="${REGION}-docker.pkg.dev"
REPOSITORY="odace-pipeline"

echo "🚀 Starting deployment of Odace Data Pipeline"

# Check if required tools are installed
command -v gcloud >/dev/null 2>&1 || { echo "❌ gcloud CLI is required but not installed. Aborting." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ docker is required but not installed. Aborting." >&2; exit 1; }

# Authenticate with gcloud
echo "📝 Authenticating with GCP..."
gcloud config set project ${PROJECT_ID}

# Configure Docker for Artifact Registry
echo "🔑 Configuring Docker authentication..."
gcloud auth configure-docker ${ARTIFACT_REGISTRY} --quiet

# Build Docker image locally for AMD64 (Cloud Run requirement)
echo "🏗️  Building Docker image locally for AMD64..."
IMAGE_NAME="${ARTIFACT_REGISTRY}/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}"
IMAGE_TAG="latest"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

docker build --platform linux/amd64 -t ${FULL_IMAGE} .

# Push to Artifact Registry
echo "📤 Pushing image to Artifact Registry..."
docker push ${FULL_IMAGE}

# Deploy to Cloud Run
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${FULL_IMAGE} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --service-account odace-pipeline-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCS_BUCKET=jaccueille,ENVIRONMENT=production" \
  --set-secrets="ADMIN_SECRET=odace-admin-secret:latest"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

echo "✅ Deployment complete!"
echo "🌐 Service URL: ${SERVICE_URL}"
echo ""
echo "Next steps:"
echo "1. Test health: curl ${SERVICE_URL}/health"
echo "2. Test API: curl -H 'Authorization: Bearer YOUR_API_KEY' ${SERVICE_URL}/api/pipeline/list"
echo "3. Visit ${SERVICE_URL}/docs for API documentation"


