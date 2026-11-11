import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR.parent
STORAGE_DIR = BASE_DIR / "storage"

class Settings(BaseSettings):
    PROJECT_NAME: str = "WARISCRYPT - Secure Digital Inheritance System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "wariscrypt-super-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database URL: default SQLite, or MySQL if specified in .env
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{BASE_DIR / 'wariscrypt.db'}"
    )
    
    # Face match threshold (0.0 to 1.0)
    FACE_MATCH_THRESHOLD: float = 0.65
    
    # Storage folders
    STORAGE_PATH: Path = STORAGE_DIR
    ASSETS_PATH: Path = STORAGE_DIR / "encrypted_assets"
    REF_IMAGES_PATH: Path = STORAGE_DIR / "reference_images"
    STEGO_PATH: Path = STORAGE_DIR / "stego_images"
    CLAIM_PATH: Path = STORAGE_DIR / "claim_uploads"
    BIOMETRICS_PATH: Path = STORAGE_DIR / "biometrics"
    KEYS_PATH: Path = STORAGE_DIR / "keys"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
for p in [
    settings.STORAGE_PATH,
    settings.ASSETS_PATH,
    settings.REF_IMAGES_PATH,
    settings.STEGO_PATH,
    settings.CLAIM_PATH,
    settings.BIOMETRICS_PATH,
    settings.KEYS_PATH,
]:
    p.mkdir(parents=True, exist_ok=True)
