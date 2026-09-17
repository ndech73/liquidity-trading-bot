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
    # Strategy & Rejection confirmation thresholds
    require_rejection_confirmation: bool = True
    rejection_confirmation_candles: int = 3
    stop_buffer_pct: float = 0.0005
    allow_ranging_trend: bool = True
    require_expansion: bool = False
    require_htf_alignment: bool = True
    max_stop_loss_pips: float | None = 22.0
    min_penetration_ticks: int = 0
    min_penetration_atr_ratio: float = 0.10
    min_penetration_pips_floor: float = 0.8
    require_stay_beyond: bool = False
    min_rejection_wick_pct: float = 0.35
    rejection_close_range_pct: float = 0.50
    min_volume_multiplier: float = 0.0
    volume_ma_period: int = 20
    require_trend_alignment: bool = False
    require_recent_compression: bool = False
    compression_lookback_candles: int = 6
    # Early Break-Even configuration
    early_breakeven_trigger_pips: float = 15.0
    early_breakeven_buffer_pips: float = 3.0
    # Structure classification
    structure_lookback_swings: int = 6
    # Session / Killzone Filter (UTC hours)
    enable_session_filter: bool = True
    session_start_hour_utc: int = 7
    session_end_hour_utc: int = 18


AnalysisSettings = AnalysisEngineSettings

# Approved 7 High-Alpha Production Trading Basket
PRODUCTION_WATCHLIST: list[str] = [
    "EURJPY",
    "USDCHF",
    "NZDUSD",
    "USDCAD",
    "EURGBP",
    "GBPUSD",
    "EURUSD",
]


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

