"""OKX exchange connectivity for market data."""

import asyncio
import aiohttp
from datetime import datetime
from typing import AsyncGenerator
from loguru import logger

from .types import Instrument, Ticker


class OKXExchange:
    """OKX exchange client for market data."""

    BASE_URL = "https://www.okx.com"

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self.instruments = {
            "BTC-USDT-SPOT": Instrument(
                symbol="BTC-USDT-SPOT",
                exchange="OKX",
                instrument_type="spot",
                base_asset="BTC",
                quote_asset="USDT",
                min_size=0.0001,
                tick_size=0.1,
                price_precision=1,
            ),
            "BTC-USDT-PERP": Instrument(
                symbol="BTC-USDT-PERP",
                exchange="OKX",
                instrument_type="perpetual",
                base_asset="BTC",
                quote_asset="USDT",
                min_size=0.01,
                tick_size=0.1,
                price_precision=1,
            ),
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
            symbol: Trading symbol (e.g., 'BTC-USDT-SPOT')

        Returns:
            Ticker object or None if failed
        """
        if not self.session:
            logger.error("Session not initialized")
            return None

        try:
            # Map our symbols to OKX API symbols
            okx_symbol = symbol.replace("-SPOT", "").replace("-PERP", "-SWAP")

            url = f"{self.BASE_URL}/api/v5/market/ticker"
            params = {"instId": okx_symbol}

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"OKX API error: {response.status}")
                    return None

                data = await response.json()

                if data.get("code") != "0":
                    logger.error(f"OKX API error: {data}")
                    return None

                ticker_data = data["data"][0]

                return Ticker(
                    symbol=symbol,
                    exchange="OKX",
                    timestamp=datetime.fromtimestamp(int(ticker_data["ts"]) / 1000),
                    bid=float(ticker_data["bidPx"]),
                    ask=float(ticker_data["askPx"]),
                    last_price=float(ticker_data["last"]),
                    volume_24h=float(ticker_data["vol24h"]),
                )

        except Exception as e:
            logger.error(f"Error fetching OKX ticker for {symbol}: {e}")
            return None

    async def stream(self) -> AsyncGenerator[tuple[datetime, str, float, float], None]:
        """Stream ticker data for BTC-USDT spot and perpetual.

        Yields:
            Tuple of (timestamp, symbol, bid, ask)
        """
        symbols = ["BTC-USDT-SPOT", "BTC-USDT-PERP"]

        while True:
            for symbol in symbols:
                ticker = await self.get_ticker(symbol)
                if ticker:
                    yield (ticker.timestamp, symbol, ticker.bid, ticker.ask)
                    logger.debug(f"OKX {symbol}: bid={ticker.bid}, ask={ticker.ask}")
                else:
                    logger.warning(f"Failed to get ticker for {symbol}")

            # Wait 10 seconds before next poll
            await asyncio.sleep(10)
