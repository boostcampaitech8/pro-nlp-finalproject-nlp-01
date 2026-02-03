import os
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # App Config
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    ENV: str = os.getenv("ENV", "development")
    
    # GCP Config
    GCP_PROJECT_ID: Optional[str] = os.getenv("GCP_PROJECT_ID")
    GCP_REGION: str = os.getenv("GCP_REGION", "asia-northeast3")
    CLOUD_RUN_JOB_NAME: str = os.getenv("CLOUD_RUN_JOB_NAME", "pro-nlp-jobs")
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "")

    # AI / LLM Keys
    NCP_CLOVASTUDIO_API_KEY: str = os.getenv("NCP_CLOVASTUDIO_API_KEY", "")
    NCP_CLOVASTUDIO_BASE_URL: str = os.getenv("NCP_CLOVASTUDIO_BASE_URL", "https://clovastudio.stream.ntruss.com")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Kakao
    KAKAO_REST_API_KEY: str = os.getenv("KAKAO_REST_API_KEY", "")
    KAKAO_CLIENT_SECRET: str = os.getenv("KAKAO_CLIENT_SECRET", "")
    KAKAO_REDIRECT_URI: str = os.getenv("KAKAO_REDIRECT_URI", "")

    # GitHub OAuth (GH_ prefix to avoid GitHub Actions Secrets restriction)
    GH_OAUTH_CLIENT_ID: str = os.getenv("GH_OAUTH_CLIENT_ID", os.getenv("GITHUB_CLIENT_ID", ""))  # Fallback for compatibility
    GH_OAUTH_CLIENT_SECRET: str = os.getenv("GH_OAUTH_CLIENT_SECRET", os.getenv("GITHUB_CLIENT_SECRET", ""))
    GH_OAUTH_REDIRECT_URI: str = os.getenv("GH_OAUTH_REDIRECT_URI", os.getenv("GITHUB_REDIRECT_URI", ""))

    # Notion OAuth
    NOTION_OAUTH_CLIENT_ID: str = os.getenv("NOTION_OAUTH_CLIENT_ID", os.getenv("NOTION_CLIENT_ID", ""))
    NOTION_OAUTH_CLIENT_SECRET: str = os.getenv("NOTION_OAUTH_CLIENT_SECRET", os.getenv("NOTION_CLIENT_SECRET", ""))
    NOTION_OAUTH_REDIRECT_URI: str = os.getenv("NOTION_OAUTH_REDIRECT_URI", "")

    # Job Config (GH_ prefix to avoid GitHub Actions Secrets restriction)
    GH_API_TOKEN: str = os.getenv("GH_API_TOKEN", os.getenv("GITHUB_TOKEN", ""))  # Fallback for compatibility
    NOTION_TOKEN: str = os.getenv("NOTION_TOKEN", "")

    # DB Config
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pro_nlp_db")

    # Admin Config
    ADMIN_SECRET: str = os.getenv("ADMIN_SECRET", "nlp-final-admin-secret")
    
    # Internal Backend URL (for Job -> Backend communication)
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    INTERNAL_API_SECRET: str = os.getenv("INTERNAL_API_SECRET", "pro-nlp-internal-secret-change-me")
    
    # Redis (Upstash)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")

    # Frontend URL for OAuth Redirects
    FRONTEND_URL: Optional[str] = os.getenv("FRONTEND_URL")

    class Config:
        case_sensitive = True

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v or v == "postgresql://postgres:postgres@localhost:5432/pro_nlp_db":
            if os.getenv("ENV") in ["production", "preview"]:
                 raise ValueError("DATABASE_URL must be explicitly set in production/preview environments")
            logger.warning("Using default development DATABASE_URL")
        return v

    @field_validator("GCP_PROJECT_ID")
    @classmethod
    def validate_gcp_project(cls, v: Optional[str]) -> Optional[str]:
        if not v and os.getenv("ENV") in ["production", "preview"]:
            raise ValueError("GCP_PROJECT_ID is required in production/preview")
        return v
    
    @field_validator("BACKEND_URL")
    @classmethod
    def validate_backend_url(cls, v: str) -> str:
        if not v:
            return "http://localhost:8000"
        if not v.startswith(("http://", "https://")):
            return f"https://{v}"
        return v

    @field_validator("GOOGLE_API_KEY", "NCP_CLOVASTUDIO_API_KEY")
    @classmethod
    def validate_api_keys(cls, v: str) -> str:
        if not v:
            logger.warning(f"Critical API Key is missing. Some AI features may not work.")
        return v

settings = Settings()
