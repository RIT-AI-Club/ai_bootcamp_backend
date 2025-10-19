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

# Email notification variables
variable "smtp_host" {
  description = "SMTP server host"
  type        = string
  default     = ""
}

variable "smtp_port" {
  description = "SMTP server port"
  type        = number
  default     = 587
}

variable "smtp_username" {
  description = "SMTP username"
  type        = string
  sensitive   = true
  default     = ""
}

variable "smtp_password" {
  description = "SMTP password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "smtp_from_email" {
  description = "From email address"
  type        = string
  default     = ""
}

variable "smtp_from_name" {
  description = "From name for emails"
  type        = string
  default     = ""
}

variable "smtp_use_tls" {
  description = "Use TLS for SMTP"
  type        = string
  default     = "true"
}

variable "admin_emails" {
  description = "Admin email addresses (comma-separated)"
  type        = string
  default     = ""
}

variable "email_notifications_enabled" {
  description = "Enable email notifications"
  type        = string
  default     = "true"
}

variable "send_student_notifications" {
  description = "Send student notifications"
  type        = string
  default     = "true"
}

variable "send_admin_notifications" {
  description = "Send admin notifications"
  type        = string
  default     = "true"
}

variable "email_rate_limit_per_hour" {
  description = "Email rate limit per hour"
  type        = number
  default     = 50
}

variable "email_retry_attempts" {
  description = "Email retry attempts"
  type        = number
  default     = 3
}

variable "email_retry_delay_seconds" {
  description = "Email retry delay in seconds"
  type        = number
  default     = 60
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
