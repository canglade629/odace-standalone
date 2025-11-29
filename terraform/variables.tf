variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "icc-project-472009"
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "europe-west1"
}

variable "gcs_bucket" {
  description = "GCS bucket name for data storage"
  type        = string
  default     = "jaccueille"
}

variable "admin_secret" {
  description = "Admin secret for API key management"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Environment (development/production)"
  type        = string
  default     = "production"
}

variable "allow_public_access" {
  description = "Allow public access to Cloud Run service (set to false for IAM-based auth)"
  type        = bool
  default     = true
}

