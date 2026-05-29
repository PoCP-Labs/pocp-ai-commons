"""
PoCP AI Commons — Configuration
=================================
Centralized configuration loaded from environment variables with sensible defaults.
"""

import os


class Settings:
    """Application settings loaded from environment."""

    # JWT / Auth
    SECRET_KEY: str = os.getenv("POCP_SECRET_KEY", "pocp-dev-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("POCP_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("POCP_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Registration
    REGISTRATION_AI_CREDITS: float = float(os.getenv("POCP_REGISTRATION_AI_CREDITS", "100.0"))

    # CORS
    CORS_ORIGINS: list[str] = os.getenv("POCP_CORS_ORIGINS", "*").split(",")


settings = Settings()
