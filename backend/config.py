"""PoCP AI Commons — Configuration Management

Centralized configuration with environment variable defaults.
"""

import os
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# --- Database ---
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'pocp.db'}",
)

# --- JWT Authentication ---
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24h

# --- Auth Mode ---
# "demo" — no auth, pass entity_id in request (default for local dev)
# "jwt" — JWT bearer token required for write operations
AUTH_MODE = os.getenv("AUTH_MODE", "demo")

# --- CORS ---
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# --- Rate Limiting ---
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# --- AI Verification ---
AI_VERIFIER_MODEL = os.getenv("AI_VERIFIER_MODEL", "simulated")  # simulated | deepseek | openai | ollama
AI_VERIFIER_THRESHOLD = float(os.getenv("AI_VERIFIER_THRESHOLD", "0.7"))
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# --- Seed ---
SEED_ON_STARTUP = os.getenv("SEED_ON_STARTUP", "true").lower() in ("true", "1", "yes")

# --- Default Reward Values ---
DEFAULT_REWARD_CP = int(os.getenv("DEFAULT_REWARD_CP", "20"))
DEFAULT_REWARD_AI_CREDITS = int(os.getenv("DEFAULT_REWARD_AI_CREDITS", "80"))
REGISTRATION_AI_CREDITS = int(os.getenv("REGISTRATION_AI_CREDITS", "100"))
