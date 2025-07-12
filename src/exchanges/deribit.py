import asyncio
import aiohttp
from datetime import datetime
from typing import AsyncGenerator
from loguru import logger

from .types import Instrument, Ticker


class DeribitExchange:
    """Deribit exchange client for market data."""

    BASE_URL = "https://www.deribit.com"

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self.instruments = {
            "BTC-PERP": Instrument(
                symbol="BTC-PERP",
                exchange="Deribit",
                instrument_type="perpetual",
                base_asset="BTC",
                quote_asset="USD",
                min_size=0.001,
                tick_size=0.5,
                price_precision=1,
            )
        }

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def get_ticker(self, symbol: str) -> Ticker | None:
        """Get ticker data for a symbol.

        Args:
            symbol: Trading symbol (e.g., 'BTC-PERP')

        Returns:
            Ticker object or None if failed
        """
        if not self.session:
            logger.error("Session not initialized")
            return None

        try:
            # Map our symbols to Deribit API symbols
            deribit_symbol = symbol.replace("-PERP", "-PERPETUAL")

            url = f"{self.BASE_URL}/api/v2/public/ticker"
            params = {"instrument_name": deribit_symbol}

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Deribit API error: {response.status}")
                    return None

                data = await response.json()

                if data.get("error"):
                    logger.error(f"Deribit API error: {data['error']}")
                    return None

                ticker_data = data["result"]

                return Ticker(
                    symbol=symbol,
                    exchange="Deribit",
                    timestamp=datetime.fromtimestamp(ticker_data["timestamp"] / 1000),
                    bid=float(ticker_data["best_bid_price"]),
                    ask=float(ticker_data["best_ask_price"]),
                    last_price=float(ticker_data["last_price"]),
                    volume_24h=float(ticker_data["stats"]["volume"]),
                )

        except Exception as e:
            logger.error(f"Error fetching Deribit ticker for {symbol}: {e}")
            return None

    async def stream(self) -> AsyncGenerator[tuple[datetime, str, float, float], None]:
        """Stream ticker data for BTC-PERP.

        Yields:
            Tuple of (timestamp, symbol, bid, ask)
        """
        symbols = ["BTC-PERP"]

        while True:
            for symbol in symbols:
                ticker = await self.get_ticker(symbol)
                if ticker:
                    yield (ticker.timestamp, symbol, ticker.bid, ticker.ask)
                    logger.debug(
                        f"Deribit {symbol}: bid={ticker.bid}, ask={ticker.ask}"
                    )
                else:
                    logger.warning(f"Failed to get ticker for {symbol}")

            # Wait 10 seconds before next poll
            await asyncio.sleep(10)
