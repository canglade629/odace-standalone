output "cloud_run_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.odace_pipeline.uri
}

output "service_account_email" {
  description = "Email of the service account"
  value       = google_service_account.odace_pipeline.email
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository path"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.odace_repo.repository_id}"
}

output "secret_name" {
  description = "Name of the admin secret in Secret Manager"
  value       = google_secret_manager_secret.admin_secret.secret_id
}

