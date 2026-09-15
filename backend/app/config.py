"""Application configuration"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Dropbox Configuration
    dropbox_access_token: Optional[str] = None
    dropbox_app_key: Optional[str] = None
    dropbox_app_secret: Optional[str] = None

    # Storage mode: "dropbox" or "local"
    storage_mode: str = "local"
    local_root: str = "/"

    # Database
    database_url: str = "sqlite:///./dbxclean.db"

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Analysis Configuration
    perceptual_hash_size: int = 8
    similarity_threshold: int = 5
    max_file_size_mb: int = 100
    cache_expiry_hours: int = 24

    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
