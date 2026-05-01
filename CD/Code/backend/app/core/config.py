import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

# Resolve .env path: walk up from this file to the StockAI root
_THIS_DIR = Path(__file__).resolve().parent  # backend/app/core/
# We need to go from core -> app -> backend -> StockAI (3 levels)
_STOCKAI_ROOT = _THIS_DIR.parent.parent.parent
_ENV_FILE = _STOCKAI_ROOT / ".env"

if not _ENV_FILE.exists():
    # Attempt one more level up just in case of different nesting
    _STOCKAI_ROOT_ALT = _THIS_DIR.parent.parent.parent.parent
    if (_STOCKAI_ROOT_ALT / ".env").exists():
        _STOCKAI_ROOT = _STOCKAI_ROOT_ALT
        _ENV_FILE = _STOCKAI_ROOT / ".env"

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "StockAI Pro"
    
    # API Keys
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    INDIA_MARKET_API_KEY: str = ""
    
    # Simulation Settings
    DEFAULT_MODEL_PROVIDER: str = "groq"
    DEFAULT_MODEL_NAME: str = "llama-3.3-70b-versatile"

settings = Settings()
