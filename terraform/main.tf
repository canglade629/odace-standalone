terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Service Account for Cloud Run
resource "google_service_account" "odace_pipeline" {
  account_id   = "odace-pipeline-sa"
  display_name = "Odace Data Pipeline Service Account"
  description  = "Service account for Odace data pipeline Cloud Run service"
}

# Grant GCS permissions to service account
resource "google_storage_bucket_iam_member" "pipeline_bucket_admin" {
  bucket = var.gcs_bucket
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.odace_pipeline.email}"
}

# Grant Firestore permissions to service account
resource "google_project_iam_member" "firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.odace_pipeline.email}"
}

# Secret Manager for admin secret
resource "google_secret_manager_secret" "admin_secret" {
  secret_id = "odace-admin-secret"
  
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "admin_secret_version" {
  secret = google_secret_manager_secret.admin_secret.id
  secret_data = var.admin_secret
}

# Grant service account access to read the secret
resource "google_secret_manager_secret_iam_member" "admin_secret_access" {
  secret_id = google_secret_manager_secret.admin_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.odace_pipeline.email}"
}

# Artifact Registry repository for Docker images
resource "google_artifact_registry_repository" "odace_repo" {
  location      = var.region
  repository_id = "odace-pipeline"
  description   = "Docker repository for Odace data pipeline"
  format        = "DOCKER"
}

# Cloud Run service
resource "google_cloud_run_v2_service" "odace_pipeline" {
  name     = "odace-pipeline"
  location = var.region
  
  template {
    service_account = google_service_account.odace_pipeline.email
    
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.odace_repo.repository_id}/odace-pipeline:latest"
      
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      
      env {
        name  = "GCS_BUCKET"
        value = var.gcs_bucket
      }
      
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      
      env {
        name = "ADMIN_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.admin_secret.secret_id
            version = "latest"
          }
        }
      }
      
      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }
      
      ports {
        container_port = 8080
      }
    }
    
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
    
    timeout = "3600s"  # 1 hour timeout for long-running pipelines
  }
  
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
  
  depends_on = [
    google_artifact_registry_repository.odace_repo,
    google_secret_manager_secret_version.admin_secret_version
  ]
}

# IAM policy to allow public access (or restrict as needed)
resource "google_cloud_run_service_iam_member" "public_access" {
  count = var.allow_public_access ? 1 : 0
  
  location = google_cloud_run_v2_service.odace_pipeline.location
  service  = google_cloud_run_v2_service.odace_pipeline.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# For authenticated access only
resource "google_cloud_run_service_iam_member" "authenticated_access" {
  count = var.allow_public_access ? 0 : 1
  
  location = google_cloud_run_v2_service.odace_pipeline.location
  service  = google_cloud_run_v2_service.odace_pipeline.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.odace_pipeline.email}"
}

