"""Historical data collection for correlation analysis and stress testing."""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
import aiohttp

from src.exchanges.okx import OKXExchange
from src.exchanges.deribit import DeribitExchange


class HistoricalDataCollector:
    """Collects and manages historical price data for portfolio analysis."""

    def __init__(self):
        self.okx_exchange = OKXExchange()
        self.deribit_exchange = DeribitExchange()
        self.historical_data: Dict[str, pd.DataFrame] = {}
        self.data_cache_duration = timedelta(hours=1)  # Cache data for 1 hour
        self.last_update: Dict[str, datetime] = {}

    async def __aenter__(self):
        """Async context manager entry."""
        await self.okx_exchange.__aenter__()
        await self.deribit_exchange.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.okx_exchange.__aexit__(exc_type, exc_val, exc_tb)
        await self.deribit_exchange.__aexit__(exc_type, exc_val, exc_tb)

    async def get_historical_data(
        self, symbol: str, days: int = 30, force_refresh: bool = False
    ) -> pd.DataFrame:
        """Get historical price data for a symbol.

        Args:
            symbol: Trading symbol (e.g., 'BTC-USDT')
            days: Number of days of historical data to fetch
            force_refresh: Force refresh even if cached data exists

        Returns:
            DataFrame with historical price data
        """
        # Check if we have recent cached data
        if not force_refresh and self._has_recent_data(symbol):
            logger.debug(f"Using cached data for {symbol}")
            return self.historical_data[symbol]

        try:
            # Determine exchange based on symbol
            exchange = self._get_exchange_for_symbol(symbol)

            # Fetch historical data
            if exchange == "OKX":
                data = await self._fetch_okx_historical(symbol, days)
            elif exchange == "Deribit":
                data = await self._fetch_deribit_historical(symbol, days)
            else:
                raise ValueError(f"Unknown exchange for symbol {symbol}")

            # Store in cache
            self.historical_data[symbol] = data
            self.last_update[symbol] = datetime.now()

            logger.info(f"Fetched {len(data)} historical records for {symbol}")
            return data

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            # Return empty DataFrame if fetch fails
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

    async def get_portfolio_historical_data(
        self, symbols: List[str], days: int = 30
    ) -> Dict[str, pd.DataFrame]:
        """Get historical data for multiple portfolio symbols.

        Args:
            symbols: List of trading symbols
            days: Number of days of historical data to fetch

        Returns:
            Dictionary mapping symbols to their historical data
        """
        tasks = []
        for symbol in symbols:
            task = self.get_historical_data(symbol, days)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        portfolio_data = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch data for {symbol}: {result}")
                portfolio_data[symbol] = pd.DataFrame()
            else:
                portfolio_data[symbol] = result

        return portfolio_data

    def _has_recent_data(self, symbol: str) -> bool:
        """Check if we have recent cached data for a symbol."""
        if symbol not in self.historical_data or symbol not in self.last_update:
            return False

        time_since_update = datetime.now() - self.last_update[symbol]
        return time_since_update < self.data_cache_duration

    def _get_exchange_for_symbol(self, symbol: str) -> str:
        """Determine which exchange a symbol belongs to."""
        # Simple heuristic - can be enhanced with more sophisticated logic
        if "USDT" in symbol or "USD" in symbol:
            return "OKX"
        elif "BTC" in symbol and "-" in symbol:
            return "Deribit"
        else:
            return "OKX"  # Default to OKX

    async def _fetch_okx_historical(self, symbol: str, days: int) -> pd.DataFrame:
        """Fetch historical data from OKX."""
        try:
            # For demo purposes, we'll simulate historical data
            # In production, this would call OKX's historical data API
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Generate simulated historical data
            dates = pd.date_range(start=start_date, end=end_date, freq="1H")
            base_price = 50000  # Base BTC price

            data = []
            for i, date in enumerate(dates):
                # Simulate price movement with some randomness
                price_change = (i * 0.001) + (hash(str(date)) % 1000 - 500) / 10000
                price = base_price * (1 + price_change)

                data.append(
                    {
                        "timestamp": date,
                        "open": price * 0.999,
                        "high": price * 1.002,
                        "low": price * 0.998,
                        "close": price,
                        "volume": 1000 + (hash(str(date)) % 500),
                    }
                )

            df = pd.DataFrame(data)
            df.set_index("timestamp", inplace=True)
            return df

        except Exception as e:
            logger.error(f"Error fetching OKX historical data for {symbol}: {e}")
            raise

    async def _fetch_deribit_historical(self, symbol: str, days: int) -> pd.DataFrame:
        """Fetch historical data from Deribit."""
        try:
            # For demo purposes, we'll simulate historical data
            # In production, this would call Deribit's historical data API
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Generate simulated historical data
            dates = pd.date_range(start=start_date, end=end_date, freq="1H")
            base_price = 50000  # Base BTC price

            data = []
            for i, date in enumerate(dates):
                # Simulate price movement with some randomness
                price_change = (i * 0.001) + (hash(str(date)) % 1000 - 500) / 10000
                price = base_price * (1 + price_change)

                data.append(
                    {
                        "timestamp": date,
                        "open": price * 0.999,
                        "high": price * 1.002,
                        "low": price * 0.998,
                        "close": price,
                        "volume": 1000 + (hash(str(date)) % 500),
                    }
                )

            df = pd.DataFrame(data)
            df.set_index("timestamp", inplace=True)
            return df

        except Exception as e:
            logger.error(f"Error fetching Deribit historical data for {symbol}: {e}")
            raise

    def calculate_returns(self, df: pd.DataFrame) -> pd.Series:
        """Calculate daily returns from price data."""
        if df.empty:
            return pd.Series()

        # Use close prices to calculate returns
        returns = df["close"].pct_change().dropna()
        return returns

    def get_correlation_data(self, symbols: List[str], days: int = 30) -> pd.DataFrame:
        """Get returns data for correlation analysis.

        Args:
            symbols: List of symbols to analyze
            days: Number of days of data to use

        Returns:
            DataFrame with returns for all symbols
        """
        # This would be called asynchronously in practice
        # For now, we'll return a placeholder
        return pd.DataFrame()


# Global instance for easy access
historical_data_collector = HistoricalDataCollector()
