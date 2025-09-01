from pydantic_settings import BaseSettings
from typing import List
import secrets

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_REFRESH_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    BCRYPT_ROUNDS: int = 12
    
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_MAX_LENGTH: int = 128
    
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30
    
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_EXPIRE_HOURS: int = 1
    
    ENVIRONMENT: str = "development"
    
    def get_cors_origins(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()