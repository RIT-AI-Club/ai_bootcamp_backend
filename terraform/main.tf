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

      # Environment variables
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }

      env {
        name  = "JWT_SECRET_KEY"
        value = var.jwt_secret_key
      }

      env {
        name  = "JWT_REFRESH_SECRET_KEY"
        value = var.jwt_refresh_secret_key
      }

      env {
        name  = "SESSION_SECRET_KEY"
        value = var.session_secret_key
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

      env {
        name  = "CORS_ORIGINS"
        value = var.cors_origins
      }

      # Google OAuth (optional)
      dynamic "env" {
        for_each = var.google_client_id != "" ? [1] : []
        content {
          name  = "GOOGLE_CLIENT_ID"
          value = var.google_client_id
        }
      }

      dynamic "env" {
        for_each = var.google_client_secret != "" ? [1] : []
        content {
          name  = "GOOGLE_CLIENT_SECRET"
          value = var.google_client_secret
        }
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

    # Service account (uses default compute service account if not specified)
    # service_account = "your-service-account@${var.project_id}.iam.gserviceaccount.com"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image
    ]
  }
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
