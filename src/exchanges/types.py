"""Data types for exchange connectivity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class Instrument:
    """Represents a trading instrument."""

    symbol: str
    exchange: str
    instrument_type: Literal["spot", "perpetual", "option"]
    base_asset: str
    quote_asset: str
    min_size: float = 0.0
    tick_size: float = 0.01
    price_precision: int = 2


@dataclass
class Ticker:
    """Represents a market ticker with bid/ask prices."""

    symbol: str
    exchange: str
    timestamp: datetime
    bid: float
    ask: float
    last_price: float
    volume_24h: float = 0.0

    @property
    def mid_price(self) -> float:
        """Calculate the mid price."""
        return (self.bid + self.ask) / 2

    @property
    def spread(self) -> float:
        """Calculate the bid-ask spread."""
        return self.ask - self.bid

    @property
    def spread_percentage(self) -> float:
        """Calculate the spread as a percentage of mid price."""
        if self.mid_price == 0:
            return 0.0
        return (self.spread / self.mid_price) * 100
