import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional, List
from dataclasses import dataclass
from loguru import logger

from .types import Instrument, Ticker


@dataclass
class OptionContract:
    """Represents an options contract."""

    symbol: str
    strike: float
    expiry: datetime
    option_type: str  # "call" or "put"
    underlying: str
    exchange: str
    delta: float
    gamma: float
    theta: float
    vega: float
    implied_volatility: float
    last_price: float
    bid: float
    ask: float
    volume_24h: float

    @property
    def mid_price(self) -> float:
        """Return the mid price (average of bid and ask)."""
        return (self.bid + self.ask) / 2


class DeribitOptionsExchange:
    """Deribit options exchange client."""

    BASE_URL = "https://www.deribit.com"

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self.instruments = {}

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def get_instruments(self) -> List[Instrument]:
        """Get available options instruments.

        Returns:
            List of available options instruments
        """
        if not self.session:
            logger.error("Session not initialized")
            return []

        try:
            url = f"{self.BASE_URL}/api/v2/public/get_instruments"
            params = {"currency": "BTC", "kind": "option"}

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Deribit API error: {response.status}")
                    return []

                data = await response.json()
                if data.get("error"):
                    logger.error(f"Deribit API error: {data['error']}")
                    return []

                instruments = []
                for item in data["result"]:
                    instrument = Instrument(
                        symbol=item["instrument_name"],
                        exchange="Deribit",
                        instrument_type="option",
                        base_asset="BTC",
                        quote_asset="USD",
                        min_size=0.001,
                        tick_size=0.5,
                        price_precision=1,
                    )
                    instruments.append(instrument)
                    self.instruments[item["instrument_name"]] = instrument

                return instruments

        except Exception as e:
            logger.error(f"Error fetching Deribit instruments: {e}")
            return []

    async def get_instruments_by_expiry(self, expiry: str) -> List[Instrument]:
        """Get instruments filtered by expiry date.

        Args:
            expiry: Expiry date string (e.g., '11JUL25')

        Returns:
            List of instruments for the specified expiry
        """
        if not self.session:
            logger.error("Session not initialized")
            return []

        try:
            url = f"{self.BASE_URL}/api/v2/public/get_instruments"
            params = {"currency": "BTC", "kind": "option"}

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Deribit API error: {response.status}")
                    return []

                data = await response.json()
                if data.get("error"):
                    logger.error(f"Deribit API error: {data['error']}")
                    return []

                instruments = []
                for item in data["result"]:
                    # Check if this instrument matches the expiry
                    instrument_name = item["instrument_name"]
                    if expiry in instrument_name:
                        instrument = Instrument(
                            symbol=item["instrument_name"],
                            exchange="Deribit",
                            instrument_type="option",
                            base_asset="BTC",
                            quote_asset="USD",
                            min_size=0.001,
                            tick_size=0.5,
                            price_precision=1,
                        )
                        # Add strike and option type for easier filtering
                        parts = instrument_name.split("-")
                        if len(parts) >= 4:
                            instrument.strike = float(parts[2])
                            instrument.option_type = parts[3].lower()
                        instruments.append(instrument)

                return instruments

        except Exception as e:
            logger.error(f"Error fetching Deribit instruments by expiry: {e}")
            return []

    async def get_option_ticker(self, symbol: str) -> Optional[OptionContract]:
        """Get options ticker data.

        Args:
            symbol: Options symbol (e.g., 'BTC-30JUN23-50000-C')

        Returns:
            OptionContract object or None if failed
        """
        if not self.session:
            logger.error("Session not initialized")
            return None

        try:
            url = f"{self.BASE_URL}/api/v2/public/ticker"
            params = {"instrument_name": symbol}

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Deribit API error: {response.status}")
                    return None

                data = await response.json()
                if data.get("error"):
                    logger.error(f"Deribit API error: {data['error']}")
                    return None

                ticker_data = data["result"]

                # Parse option details from symbol
                # Format: BTC-30JUN23-50000-C
                parts = symbol.split("-")
                if len(parts) != 4:
                    logger.error(f"Invalid option symbol format: {symbol}")
                    return None

                underlying = parts[0]
                expiry_str = parts[1]
                strike = float(parts[2])
                option_type = parts[3].lower()

                # Parse expiry date
                expiry = datetime.strptime(expiry_str, "%d%b%y")

                # Calculate Greeks (simplified)
                current_price = float(ticker_data["last_price"] or 0.0)
                underlying_price = 107000  # TODO: Get from spot price
                time_to_expiry = (expiry - datetime.now()).days / 365

                # If no last_price, use a fallback based on strike
                if current_price <= 0:
                    if option_type == "put":
                        current_price = strike * 0.05  # 5% of strike for puts
                    else:
                        current_price = strike * 0.03  # 3% of strike for calls

                # Simplified Black-Scholes Greeks
                delta = self._calculate_delta(
                    option_type, underlying_price, strike, time_to_expiry, 0.5
                )
                gamma = self._calculate_gamma(
                    underlying_price, strike, time_to_expiry, 0.5
                )
                theta = self._calculate_theta(
                    option_type, underlying_price, strike, time_to_expiry, 0.5
                )
                vega = self._calculate_vega(
                    underlying_price, strike, time_to_expiry, 0.5
                )

                # Handle None for bid/ask/volume
                bid = ticker_data.get("best_bid_price")
                ask = ticker_data.get("best_ask_price")
                bid = float(bid) if bid is not None else 0.0
                ask = float(ask) if ask is not None else 0.0
                volume_24h = ticker_data.get("stats", {}).get("volume")
                volume_24h = float(volume_24h) if volume_24h is not None else 0.0

                return OptionContract(
                    symbol=symbol,
                    strike=strike,
                    expiry=expiry,
                    option_type=option_type,
                    underlying=underlying,
                    exchange="Deribit",
                    delta=delta,
                    gamma=gamma,
                    theta=theta,
                    vega=vega,
                    implied_volatility=0.5,  # TODO: Calculate from market
                    last_price=current_price,
                    bid=bid,
                    ask=ask,
                    volume_24h=volume_24h,
                )

        except Exception as e:
            logger.error(f"Error fetching Deribit option ticker for {symbol}: {e}")
            return None

    def _calculate_delta(
        self, option_type: str, S: float, K: float, T: float, sigma: float
    ) -> float:
        """Calculate option delta (simplified)."""
        if option_type == "call":
            return 0.6 if S > K else 0.4  # Simplified
        else:  # put
            return -0.4 if S > K else -0.6  # Simplified

    def _calculate_gamma(self, S: float, K: float, T: float, sigma: float) -> float:
        """Calculate option gamma (simplified)."""
        return 0.01  # Simplified

    def _calculate_theta(
        self, option_type: str, S: float, K: float, T: float, sigma: float
    ) -> float:
        """Calculate option theta (simplified)."""
        return -0.1 if option_type == "call" else -0.08  # Simplified

    def _calculate_vega(self, S: float, K: float, T: float, sigma: float) -> float:
        """Calculate option vega (simplified)."""
        return 0.5  # Simplified

    async def get_option_chain(
        self, underlying: str = "BTC", expiry_days: int = 30
    ) -> List[OptionContract]:
        """Get option chain for underlying.

        Args:
            underlying: Underlying asset
            expiry_days: Days to expiry filter

        Returns:
            List of option contracts
        """
        instruments = await self.get_instruments()

        # Filter by underlying and expiry
        target_expiry = datetime.now() + timedelta(days=expiry_days)

        option_chain = []
        for instrument in instruments:
            if not instrument.symbol.startswith(underlying):
                continue

            # Parse expiry from symbol
            parts = instrument.symbol.split("-")
            if len(parts) != 4:
                continue

            try:
                expiry = datetime.strptime(parts[1], "%d%b%y")
                if expiry <= target_expiry:
                    ticker = await self.get_option_ticker(instrument.symbol)
                    if ticker:
                        option_chain.append(ticker)
            except ValueError:
                continue

        return option_chain

    async def stream_options(
        self,
    ) -> AsyncGenerator[tuple[datetime, str, OptionContract], None]:
        """Stream options data for active contracts.

        Yields:
            Tuple of (timestamp, symbol, option_contract)
        """
        while True:
            try:
                # Get current option chain
                option_chain = await self.get_option_chain()

                for contract in option_chain:
                    yield (datetime.now(), contract.symbol, contract)
                    logger.debug(f"Deribit {contract.symbol}: {contract.last_price}")

                # Wait 30 seconds before next poll (options less liquid)
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in options stream: {e}")
                await asyncio.sleep(60)


# Global instance
deribit_options = DeribitOptionsExchange()
