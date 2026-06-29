from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration from .env file"""

    # FastAPI
    fast_api_host: str = "0.0.0.0"
    fast_api_port: int = 8000
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./child_safety.db"

    # JWT
    jwt_secret_key: str = "T311M0M"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # AI Model
    model_path: str = "./models/grooming-detector-finetuned"
    device: str = "cpu"
    risk_threshold: float = 0.5

    # COPPA
    data_retention_days: int = 30
    parent_verification_required: bool = True
    encryption_key: str = "your-encryption-key-min-32-chars"

    # Roblox
    roblox_api_key: str = ""
    roblox_api_timeout: int = 10

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
