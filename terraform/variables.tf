variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region for Cloud Run"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "aibc-auth-service"
}

variable "image_url" {
  description = "Docker image URL (will be set by deployment script)"
  type        = string
}

variable "database_url" {
  description = "PostgreSQL connection string"
  type        = string
  sensitive   = true
  default     = ""
}

variable "jwt_secret_key" {
  description = "JWT secret key for access tokens"
  type        = string
  sensitive   = true
  default     = ""
}

variable "jwt_refresh_secret_key" {
  description = "JWT secret key for refresh tokens"
  type        = string
  sensitive   = true
  default     = ""
}

variable "session_secret_key" {
  description = "Session secret key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "google_client_id" {
  description = "Google OAuth Client ID"
  type        = string
  default     = ""
}

variable "google_client_secret" {
  description = "Google OAuth Client Secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "google_redirect_uri" {
  description = "Google OAuth Redirect URI"
  type        = string
  default     = ""
}

variable "gcs_bucket_name" {
  description = "Google Cloud Storage bucket name"
  type        = string
  default     = ""
}

variable "gcs_project_id" {
  description = "GCS Project ID"
  type        = string
  default     = ""
}

variable "google_application_credentials" {
  description = "Path to GCS credentials in container"
  type        = string
  default     = ""
}

variable "frontend_url" {
  description = "Frontend URL for OAuth redirects"
  type        = string
  default     = ""
}

variable "cors_origins" {
  description = "Allowed CORS origins (comma-separated)"
  type        = string
  default     = "https://yourdomain.com"
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
}

variable "cpu" {
  description = "CPU allocation for Cloud Run instances"
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Memory allocation for Cloud Run instances"
  type        = string
  default     = "512Mi"
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated access to the service"
  type        = bool
  default     = true
}
