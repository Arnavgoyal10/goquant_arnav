"""Costing service for fee and slippage estimates."""

from typing import Dict, Any
from loguru import logger


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

    def calculate_total_cost(
        self, qty: float, price: float, exchange: str, instrument_type: str
    ) -> Dict[str, float]:
        """Calculate total trading costs.

        Args:
            qty: Quantity
            price: Price per unit
            exchange: Exchange name
            instrument_type: Type of instrument

        Returns:
            Dictionary with cost breakdown
        """
        notional = abs(qty * price)
        fee = self.calculate_fee(notional, exchange, instrument_type)
        slippage = self.calculate_slippage(notional, instrument_type)
        total_cost = fee + slippage

        return {
            "notional": notional,
            "fee": fee,
            "slippage": slippage,
            "total_cost": total_cost,
            "total_cost_pct": (total_cost / notional) * 100 if notional > 0 else 0,
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
        self, qty: float, price: float, exchange: str, instrument_type: str
    ) -> str:
        """Get a human-readable cost summary.

        Args:
            qty: Quantity
            price: Price per unit
            exchange: Exchange name
            instrument_type: Type of instrument

        Returns:
            Formatted cost summary
        """
        costs = self.calculate_total_cost(qty, price, exchange, instrument_type)

        return (
            f"💰 *Cost Breakdown*\n\n"
            f"Notional: ${costs['notional']:,.2f}\n"
            f"Fee: ${costs['fee']:.2f}\n"
            f"Slippage: ${costs['slippage']:.2f}\n"
            f"Total Cost: ${costs['total_cost']:.2f}\n"
            f"Cost %: {costs['total_cost_pct']:.3f}%"
        )


# Global instance
costing_service = CostingService()
