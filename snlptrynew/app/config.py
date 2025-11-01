"""Application settings loaded from environment variables."""
from functools import lru_cache
from pathlib import Path
from typing import Optional

try:
    # Pydantic v2 style
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field
    V2 = True
except Exception:  # fallback to pydantic v1
    from pydantic import BaseSettings, Field
    V2 = False


class Settings(BaseSettings):
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    embedding_model: str = Field("all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    top_k: int = Field(5, env="TOP_K")
    index_path: Path = Field(Path("index") / "vector_index.faiss", env="INDEX_PATH")
    metadata_path: Path = Field(Path("index") / "metadata.json", env="METADATA_PATH")
    openai_base_url: Optional[str] = Field(None, env="OPENAI_BASE_URL")
    openai_chat_model: str = Field("gpt-4o-mini", env="OPENAI_CHAT_MODEL")

    # Optional ingestion keys and thresholds
    news_api_key: Optional[str] = Field(None, env="NEWS_API_KEY")
    finnhub_api_key: Optional[str] = Field(None, env="FINNHUB_API_KEY")
    supported_th: float = Field(0.55, env="SUPPORTED_TH")
    uncertain_th: float = Field(0.35, env="UNCERTAIN_TH")

    # Online fallback controls
    online_fallback_enabled: bool = Field(True, env="ONLINE_FALLBACK_ENABLED")
    online_days: int = Field(14, env="ONLINE_DAYS")
    online_top_k: int = Field(3, env="ONLINE_TOP_K")
    online_timeout_s: float = Field(6.0, env="ONLINE_TIMEOUT_S")
    online_allow_domains: Optional[str] = Field(
        "reuters.com,apnews.com,wsj.com,bloomberg.com,sec.gov,investor.*",
        env="ONLINE_ALLOW_DOMAINS",
    )

    # CORS: allowed frontend origins (comma-separated)
    cors_allowed_origins: str = Field(
        "http://localhost:3000,http://127.0.0.1:3000,http://[::1]:3000",
        env="CORS_ALLOWED_ORIGINS",
    )

    if V2:
        # pydantic v2 style config
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    else:
        # pydantic v1 style config
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = "ignore"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
