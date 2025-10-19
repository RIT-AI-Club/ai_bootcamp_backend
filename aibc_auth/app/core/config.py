from pydantic_settings import BaseSettings
from typing import List
import secrets
import os

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_REFRESH_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    SESSION_SECRET_KEY: str = secrets.token_urlsafe(32)

    # Frontend URL for OAuth redirects
    FRONTEND_URL: str = "http://localhost:3000"

    # Optimize bcrypt for Cloud Run (reduce from 12 to 10 for serverless)
    # Still secure: 10 rounds = ~100ms vs 12 rounds = ~250ms
    BCRYPT_ROUNDS: int = 10 if os.getenv("K_SERVICE") else 12

    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_MAX_LENGTH: int = 128

    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30

    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_EXPIRE_HOURS: int = 1

    # Google Cloud Storage Configuration
    GCS_BUCKET_NAME: str = "aibc-submissions"
    GCS_PROJECT_ID: str = "your-gcp-project-id"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # Email Notification Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@aiclub-bootcamp.com"
    SMTP_FROM_NAME: str = "AI Bootcamp"
    SMTP_USE_TLS: bool = True

    # Admin Recipients for notifications
    ADMIN_EMAILS: str = "romanslack1@gmail.com"

    # Email Feature Flags
    EMAIL_NOTIFICATIONS_ENABLED: bool = True
    SEND_STUDENT_NOTIFICATIONS: bool = True
    SEND_ADMIN_NOTIFICATIONS: bool = True
    EMAIL_RATE_LIMIT_PER_HOUR: int = 50
    EMAIL_RETRY_ATTEMPTS: int = 3
    EMAIL_RETRY_DELAY_SECONDS: int = 60

    ENVIRONMENT: str = "development"

    def get_cors_origins(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS

    def get_admin_emails(self) -> List[str]:
        if isinstance(self.ADMIN_EMAILS, str):
            return [email.strip() for email in self.ADMIN_EMAILS.split(",")]
        return self.ADMIN_EMAILS
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()