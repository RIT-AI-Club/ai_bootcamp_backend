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

# Cloud Run Service
resource "google_cloud_run_v2_service" "auth_service" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    # Scaling configuration
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    # Container configuration
    containers {
      image = var.image_url

      # Resource limits
      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        cpu_idle = true
        startup_cpu_boost = true
      }

      # Port configuration (Cloud Run expects 8080 by default)
      ports {
        container_port = 8080
      }

      # Mount GCS credentials secret as volume
      volume_mounts {
        name       = "gcp-key-volume"
        mount_path = "/secrets"
      }

      # Environment variables (only set if provided)
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      # Only set DATABASE_URL if provided (not empty/placeholder)
      dynamic "env" {
        for_each = var.database_url != "" && var.database_url != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "DATABASE_URL"
          value = var.database_url
        }
      }

      # Only set JWT secrets if provided
      dynamic "env" {
        for_each = var.jwt_secret_key != "" && var.jwt_secret_key != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "JWT_SECRET_KEY"
          value = var.jwt_secret_key
        }
      }

      dynamic "env" {
        for_each = var.jwt_refresh_secret_key != "" && var.jwt_refresh_secret_key != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "JWT_REFRESH_SECRET_KEY"
          value = var.jwt_refresh_secret_key
        }
      }

      dynamic "env" {
        for_each = var.session_secret_key != "" && var.session_secret_key != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "SESSION_SECRET_KEY"
          value = var.session_secret_key
        }
      }

      env {
        name  = "JWT_ALGORITHM"
        value = "HS256"
      }

      env {
        name  = "ACCESS_TOKEN_EXPIRE_MINUTES"
        value = "60"
      }

      env {
        name  = "REFRESH_TOKEN_EXPIRE_DAYS"
        value = "7"
      }

      # Only set CORS if provided
      dynamic "env" {
        for_each = var.cors_origins != "" && var.cors_origins != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "CORS_ORIGINS"
          value = var.cors_origins
        }
      }

      # Google OAuth (optional)
      dynamic "env" {
        for_each = var.google_client_id != "" && var.google_client_id != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "GOOGLE_CLIENT_ID"
          value = var.google_client_id
        }
      }

      dynamic "env" {
        for_each = var.google_client_secret != "" && var.google_client_secret != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "GOOGLE_CLIENT_SECRET"
          value = var.google_client_secret
        }
      }

      dynamic "env" {
        for_each = var.google_redirect_uri != "" && var.google_redirect_uri != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "GOOGLE_REDIRECT_URI"
          value = var.google_redirect_uri
        }
      }

      # Google Cloud Storage (optional)
      dynamic "env" {
        for_each = var.gcs_bucket_name != "" && var.gcs_bucket_name != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "GCS_BUCKET_NAME"
          value = var.gcs_bucket_name
        }
      }

      dynamic "env" {
        for_each = var.gcs_project_id != "" && var.gcs_project_id != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "GCS_PROJECT_ID"
          value = var.gcs_project_id
        }
      }

      dynamic "env" {
        for_each = var.google_application_credentials != "" && var.google_application_credentials != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "GOOGLE_APPLICATION_CREDENTIALS"
          value = var.google_application_credentials
        }
      }

      # Frontend URL for OAuth redirects
      dynamic "env" {
        for_each = var.frontend_url != "" && var.frontend_url != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "FRONTEND_URL"
          value = var.frontend_url
        }
      }

      # Email notification configuration
      dynamic "env" {
        for_each = var.smtp_host != "" && var.smtp_host != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "SMTP_HOST"
          value = var.smtp_host
        }
      }

      dynamic "env" {
        for_each = var.smtp_port != 0 ? [1] : []
        content {
          name  = "SMTP_PORT"
          value = tostring(var.smtp_port)
        }
      }

      dynamic "env" {
        for_each = var.smtp_username != "" && var.smtp_username != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "SMTP_USERNAME"
          value = var.smtp_username
        }
      }

      dynamic "env" {
        for_each = var.smtp_password != "" && var.smtp_password != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "SMTP_PASSWORD"
          value = var.smtp_password
        }
      }

      dynamic "env" {
        for_each = var.smtp_from_email != "" && var.smtp_from_email != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "SMTP_FROM_EMAIL"
          value = var.smtp_from_email
        }
      }

      dynamic "env" {
        for_each = var.smtp_from_name != "" && var.smtp_from_name != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "SMTP_FROM_NAME"
          value = var.smtp_from_name
        }
      }

      dynamic "env" {
        for_each = var.smtp_use_tls != "" && var.smtp_use_tls != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "SMTP_USE_TLS"
          value = var.smtp_use_tls
        }
      }

      dynamic "env" {
        for_each = var.admin_emails != "" && var.admin_emails != "placeholder-will-be-ignored" ? [1] : []
        content {
          name  = "ADMIN_EMAILS"
          value = var.admin_emails
        }
      }

      dynamic "env" {
        for_each = var.email_notifications_enabled != "" ? [1] : []
        content {
          name  = "EMAIL_NOTIFICATIONS_ENABLED"
          value = var.email_notifications_enabled
        }
      }

      dynamic "env" {
        for_each = var.send_student_notifications != "" ? [1] : []
        content {
          name  = "SEND_STUDENT_NOTIFICATIONS"
          value = var.send_student_notifications
        }
      }

      dynamic "env" {
        for_each = var.send_admin_notifications != "" ? [1] : []
        content {
          name  = "SEND_ADMIN_NOTIFICATIONS"
          value = var.send_admin_notifications
        }
      }

      env {
        name  = "EMAIL_RATE_LIMIT_PER_HOUR"
        value = tostring(var.email_rate_limit_per_hour)
      }

      env {
        name  = "EMAIL_RETRY_ATTEMPTS"
        value = tostring(var.email_retry_attempts)
      }

      env {
        name  = "EMAIL_RETRY_DELAY_SECONDS"
        value = tostring(var.email_retry_delay_seconds)
      }

      # Startup probe for health checks
      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 5
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
      }

      # Liveness probe
      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 30
        failure_threshold     = 3
      }
    }

    # Timeout and concurrency
    timeout = "60s"

    max_instance_request_concurrency = 80

    # Mount secret as volume
    volumes {
      name = "gcp-key-volume"
      secret {
        secret       = "gcp-key"
        default_mode = 292 # 0444 in decimal (read-only)
        items {
          version = "latest"
          path    = "gcp-key.json"
        }
      }
    }

    # Service account (uses default compute service account if not specified)
    # service_account = "your-service-account@${var.project_id}.iam.gserviceaccount.com"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  # Note: We don't use lifecycle ignore_changes here
  # Instead, we control env updates via the --skip-env-update flag
  # which uses dynamic blocks to conditionally set env vars
}

# IAM policy for public access (if enabled)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count = var.allow_unauthenticated ? 1 : 0

  project  = google_cloud_run_v2_service.auth_service.project
  location = google_cloud_run_v2_service.auth_service.location
  name     = google_cloud_run_v2_service.auth_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
