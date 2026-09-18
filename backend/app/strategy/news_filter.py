"""
News Filter Engine: Avoids entering positions during high-impact macroeconomic news releases.
Protects the bot against slippage, spread widening, and whipsaw volatility around red-folder events.
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from app.analysis_engine.domain.candle import Candle


class NewsFilter:
    """
    Filters out trade entries that coincide with high-impact economic news releases
    and abnormal volatility expansion spikes.
    """

    # Major recurring scheduled news windows in UTC: (start_minute_of_day, end_minute_of_day, currency, description)
    SCHEDULED_WINDOWS = [
        # USD Releases (NFP, CPI, PPI, Retail Sales, GDP, Jobless Claims @ 12:30 UTC)
        (12 * 60 + 15, 13 * 60 + 15, "USD", "US Major Releases (NFP/CPI/GDP/Claims)"),
        # USD Releases (ISM PMIs, JOLTS, Cons. Confidence @ 14:00 UTC)
        (13 * 60 + 45, 14 * 60 + 30, "USD", "US ISM/JOLTS Releases"),
        # USD FOMC Rate Decisions / Fed Press Conference (typically Wednesdays @ 18:00 - 18:30 UTC)
        (17 * 60 + 45, 19 * 60 + 15, "USD", "US FOMC Rate Decision & Presser"),
        # GBP Releases (UK CPI, GDP, Employment @ 06:00 UTC / 07:00 BST)
        (5 * 60 + 45, 6 * 60 + 45, "GBP", "UK Major Releases (CPI/GDP/Jobs)"),
        # GBP BoE Rate Decision (@ 11:00 UTC / 12:00 BST)
        (10 * 60 + 45, 11 * 60 + 45, "GBP", "Bank of England Rate Decision"),
        # EUR Releases (Eurozone CPI @ 09:00 UTC)
        (8 * 60 + 45, 9 * 60 + 30, "EUR", "Eurozone CPI/GDP Releases"),
        # EUR ECB Rate Decision & Press Conference (@ 12:15 - 12:45 UTC)
        (12 * 60 + 0, 13 * 60 + 30, "EUR", "ECB Rate Decision & Presser"),
        # JPY BoJ Rate Decision & Monetary Outlook (Asian session @ ~03:00 - 05:30 UTC)
        (2 * 60 + 30, 6 * 60 + 0, "JPY", "Bank of Japan Policy Decision"),
        # CHF SNB Policy & CPI (@ 06:30 - 07:30 UTC)
        (6 * 60 + 15, 7 * 60 + 45, "CHF", "Swiss SNB Policy / CPI"),
    ]

    def __init__(
        self,
        enable_scheduled_filter: bool = True,
        enable_volatility_spike_filter: bool = True,
        volatility_spike_multiplier: float = 2.5,
        post_news_cooldown_minutes: int | None = None,
    ):
        settings = None
        try:
            from app.core.settings import get_settings
            settings = get_settings().analysis
        except Exception:
            pass

        self.enable_scheduled_filter = enable_scheduled_filter
        self.enable_volatility_spike_filter = enable_volatility_spike_filter
        self.volatility_spike_multiplier = volatility_spike_multiplier
        self.post_news_cooldown_minutes = (
            post_news_cooldown_minutes
            if post_news_cooldown_minutes is not None
            else (getattr(settings, "post_news_cooldown_minutes", 15) if settings else 15)
        )

    def get_currencies_for_symbol(self, symbol: str) -> List[str]:
        """Extracts the base and quote currency codes from symbol."""
        sym = symbol.upper()
        currencies = []
        for c in ["USD", "GBP", "EUR", "JPY", "CHF", "AUD", "NZD", "CAD"]:
            if c in sym:
                currencies.append(c)
        return currencies

    def is_news_time(
        self,
        symbol: str,
        timestamp: datetime,
        current_candle: Optional[Candle] = None,
        history: Optional[List[Candle]] = None,
    ) -> Tuple[bool, str]:
        """
        Determines whether the given candle / timestamp falls within a restricted news window.
        Returns: (is_news_active, reason_string)
        """
        # 1. Check Scheduled News Windows for Symbol's Currencies
        if self.enable_scheduled_filter:
            sym_currencies = set(self.get_currencies_for_symbol(symbol))
            dt_utc = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
            minute_of_day = dt_utc.hour * 60 + dt_utc.minute

            for start_min, end_min, curr, desc in self.SCHEDULED_WINDOWS:
                if curr in sym_currencies:
                    effective_end = end_min + self.post_news_cooldown_minutes
                    if start_min <= minute_of_day <= effective_end:
                        in_cooldown = minute_of_day > end_min
                        label = (
                            f"News Window ({desc} + {self.post_news_cooldown_minutes}m Cooldown)"
                            if in_cooldown
                            else f"News Window ({desc})"
                        )
                        return True, label

        # 2. Check Dynamic Volatility Shock (Spike Candle Filter)
        if self.enable_volatility_spike_filter and current_candle and history and len(history) >= 15:
            recent = history[-15:-1]
            ranges = [c.high - c.low for c in recent]
            avg_range = sum(ranges) / len(ranges) if ranges else 0.0

            if avg_range > 0:
                current_range = current_candle.high - current_candle.low
                if current_range >= avg_range * self.volatility_spike_multiplier:
                    return True, f"Abnormal Volatility Spike ({current_range / avg_range:.1f}x ATR)"

        return False, ""
