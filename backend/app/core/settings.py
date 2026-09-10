from functools import lru_cache
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AnalysisEngineSettings(BaseModel):
    liquidity_lookback: int = 3
    equal_level_tolerance_pct: float = 0.0005
    compression_recent_window: int = 5
    compression_baseline_window: int = 20
    compression_threshold: float = 0.6
    expansion_recent_window: int = 5
    expansion_baseline_window: int = 20
    expansion_threshold: float = 1.5
    direction_threshold: float = 0.3


class Settings(BaseSettings):
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql+psycopg://trader:change-me@localhost:5433/liquidity_bot"

    analysis: AnalysisEngineSettings = Field(default_factory=AnalysisEngineSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

