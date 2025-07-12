"""Costing service for fee and slippage estimates."""

from typing import Dict, Any
from loguru import logger
import numpy as np


class CostingService:
    """Service for calculating trading costs."""

    def __init__(self):
        # Fee rates by exchange and instrument type
        self.fee_rates = {
            "OKX": {
                "spot": 0.001,  # 0.1% for spot
                "perpetual": 0.0005,  # 0.05% for perpetuals
                "option": 0.0003,  # 0.03% for options
            },
            "Deribit": {
                "spot": 0.0005,  # 0.05% for spot
                "perpetual": 0.0002,  # 0.02% for perpetuals
                "option": 0.0001,  # 0.01% for options
            },
        }

        # Slippage estimates (percentage of mid price)
        self.slippage_rates = {
            "spot": 0.0001,  # 0.01% for spot
            "perpetual": 0.0002,  # 0.02% for perpetuals
            "option": 0.001,  # 0.1% for options
        }

    def calculate_fee(
        self, notional: float, exchange: str, instrument_type: str
    ) -> float:
        """Calculate trading fee.

        Args:
            notional: Notional value of the trade
            exchange: Exchange name
            instrument_type: Type of instrument

        Returns:
            Fee amount
        """
        try:
            fee_rate = self.fee_rates[exchange][instrument_type]
            return notional * fee_rate
        except KeyError:
            logger.warning(f"Unknown fee rate for {exchange} {instrument_type}")
            return notional * 0.001  # Default 0.1%

    def calculate_slippage(self, notional: float, instrument_type: str) -> float:
        """Calculate estimated slippage.

        Args:
            notional: Notional value of the trade
            instrument_type: Type of instrument

        Returns:
            Slippage amount
        """
        try:
            slippage_rate = self.slippage_rates[instrument_type]
            return notional * slippage_rate
        except KeyError:
            logger.warning(f"Unknown slippage rate for {instrument_type}")
            return notional * 0.0001  # Default 0.01%

    def advanced_slippage(
        self,
        qty: float,
        price: float,
        instrument_type: str,
        volatility: float = 0.02,
        order_book_depth: float = 1000000,
    ) -> dict:
        """Advanced slippage model: VWAP, market impact, volatility/randomness."""
        notional = abs(qty * price)
        # VWAP: assume price impact increases with order size relative to depth
        vwap_impact = min(
            0.001 + 0.01 * (notional / order_book_depth), 0.03
        )  # up to 3%
        # Market impact: nonlinear for large orders
        market_impact = 0.0005 * (notional / order_book_depth) ** 1.2
        # Volatility/randomness
        random_component = np.random.normal(0, volatility * 0.1)
        # Spread: higher for options, lower for spot
        spread = (
            0.0002
            if instrument_type == "spot"
            else (0.0005 if instrument_type == "perpetual" else 0.001)
        )
        # Total slippage rate
        slippage_rate = vwap_impact + market_impact + spread + random_component
        slippage_rate = max(slippage_rate, 0.0)
        slippage = notional * slippage_rate
        # VWAP price
        vwap_price = price * (1 + slippage_rate if qty > 0 else 1 - slippage_rate)
        return {
            "slippage": slippage,
            "slippage_rate": slippage_rate,
            "vwap_price": vwap_price,
            "market_impact": market_impact * notional,
            "spread": spread * notional,
            "random_component": random_component * notional,
        }

    def calculate_total_cost(
        self,
        qty: float,
        price: float,
        exchange: str,
        instrument_type: str,
        volatility: float = 0.02,
        order_book_depth: float = 1000000,
    ) -> Dict[str, float]:
        """Calculate total trading costs with advanced slippage."""
        notional = abs(qty * price)
        fee = self.calculate_fee(notional, exchange, instrument_type)
        adv = self.advanced_slippage(
            qty, price, instrument_type, volatility, order_book_depth
        )
        slippage = adv["slippage"]
        total_cost = fee + slippage
        return {
            "notional": notional,
            "fee": fee,
            "slippage": slippage,
            "total_cost": total_cost,
            "total_cost_pct": (total_cost / notional) * 100 if notional > 0 else 0,
            "vwap_price": adv["vwap_price"],
            "slippage_rate": adv["slippage_rate"],
            "market_impact": adv["market_impact"],
            "spread": adv["spread"],
            "random_component": adv["random_component"],
        }

    def estimate_fill_price(
        self, mid_price: float, qty: float, instrument_type: str
    ) -> float:
        """Estimate fill price including slippage.

        Args:
            mid_price: Mid price
            qty: Quantity (positive for buy, negative for sell)
            instrument_type: Type of instrument

        Returns:
            Estimated fill price
        """
        slippage_rate = self.slippage_rates.get(instrument_type, 0.0001)

        if qty > 0:  # Buy
            return mid_price * (1 + slippage_rate)
        else:  # Sell
            return mid_price * (1 - slippage_rate)

    def get_cost_summary(
        self,
        qty: float,
        price: float,
        exchange: str,
        instrument_type: str,
        volatility: float = 0.02,
        order_book_depth: float = 1000000,
    ) -> str:
        """Get a human-readable cost summary with advanced metrics."""
        costs = self.calculate_total_cost(
            qty, price, exchange, instrument_type, volatility, order_book_depth
        )
        slippage_pct = costs["slippage_rate"] * 100
        return (
            f"💰 *Cost Breakdown (Advanced)*\n\n"
            f"Notional: ${costs['notional']:,.2f}\n"
            f"Fee: ${costs['fee']:.2f}\n"
            f"Slippage: ${costs['slippage']:.2f} ({slippage_pct:.3f}%)\n"
            f"Market Impact: ${costs['market_impact']:.2f}\n"
            f"Spread Component: ${costs['spread']:.2f}\n"
            f"Random/Volatility: ${costs['random_component']:.2f}\n"
            f"VWAP Price: ${costs['vwap_price']:.2f}\n"
            f"Total Cost: ${costs['total_cost']:.2f}\n"
            f"Cost %: {costs['total_cost_pct']:.3f}%"
        )


# Global instance
costing_service = CostingService()
