from fastapi import APIRouter
from pydantic import BaseModel

from app.core.settings import get_settings

router = APIRouter()


class BotSettingsUpdate(BaseModel):
    maxRiskPerTradePercent: float = 1.0
    maxOpenTrades: int = 5
    compressionThreshold: float = 0.70
    expansionThreshold: float = 1.50
    bridgeHost: str = "127.0.0.1"
    bridgePort: int = 18812


@router.get("/settings")
def get_bot_settings():
    """Returns the current trading bot runtime configuration."""
    s = get_settings()
    return {
        "maxRiskPerTradePercent": 1.0,
        "maxOpenTrades": 5,
        "compressionThreshold": s.analysis.compression_threshold,
        "expansionThreshold": s.analysis.expansion_threshold,
        "bridgeHost": "127.0.0.1",
        "bridgePort": 18812,
    }


@router.post("/settings")
def update_bot_settings(body: BotSettingsUpdate):
    """Updates bot configuration parameters."""
    s = get_settings()
    s.analysis.compression_threshold = body.compressionThreshold
    s.analysis.expansion_threshold = body.expansionThreshold
    return {"status": "updated", "settings": body.dict()}
