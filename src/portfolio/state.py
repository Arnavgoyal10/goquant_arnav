"""Portfolio state management for position tracking."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Literal
from loguru import logger


@dataclass
class Position:
    """Represents a trading position."""

    symbol: str
    qty: float
    avg_px: float
    instrument_type: Literal["spot", "perpetual", "option"]
    exchange: str
    timestamp: datetime

    @property
    def notional(self) -> float:
        """Calculate the notional value of the position."""
        return abs(self.qty * self.avg_px)

    @property
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.qty > 0

    @property
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.qty < 0

    def to_dict(self) -> dict:
        """Convert position to dictionary."""
        return asdict(self)


class Portfolio:
    """Portfolio class for managing positions."""

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.created_at = datetime.now()

    def add_position(self, position: Position) -> None:
        """Add or update a position.

        Args:
            position: Position to add/update
        """
        self.positions[position.symbol] = position
        logger.info(
            f"Added position: {position.symbol} {position.qty} @ {position.avg_px}"
        )

    def remove_position(self, symbol: str) -> Optional[Position]:
        """Remove a position.

        Args:
            symbol: Symbol to remove

        Returns:
            Removed position or None if not found
        """
        position = self.positions.pop(symbol, None)
        if position:
            logger.info(f"Removed position: {symbol}")
        return position

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get a position by symbol.

        Args:
            symbol: Symbol to get

        Returns:
            Position or None if not found
        """
        return self.positions.get(symbol)

    def update_fill(
        self, symbol: str, qty: float, price: float, instrument_type: str, exchange: str
    ) -> None:
        """Update position with a new fill.

        Args:
            symbol: Trading symbol
            qty: Quantity (positive for buy, negative for sell)
            price: Fill price
            instrument_type: Type of instrument
            exchange: Exchange name
        """
        existing = self.positions.get(symbol)

        if existing:
            # Update existing position
            total_qty = existing.qty + qty
            if total_qty == 0:
                # Position closed
                self.remove_position(symbol)
                logger.info(f"Position closed: {symbol}")
            else:
                # Update average price
                total_cost = (existing.qty * existing.avg_px) + (qty * price)
                new_avg_px = total_cost / total_qty

                updated_position = Position(
                    symbol=symbol,
                    qty=total_qty,
                    avg_px=new_avg_px,
                    instrument_type=instrument_type,
                    exchange=exchange,
                    timestamp=datetime.now(),
                )
                self.add_position(updated_position)
        else:
            # New position
            new_position = Position(
                symbol=symbol,
                qty=qty,
                avg_px=price,
                instrument_type=instrument_type,
                exchange=exchange,
                timestamp=datetime.now(),
            )
            self.add_position(new_position)

    def snapshot(self) -> dict:
        """Get a snapshot of the portfolio.

        Returns:
            Dictionary with portfolio summary
        """
        total_notional = sum(pos.notional for pos in self.positions.values())
        total_positions = len(self.positions)

        # Group by instrument type
        by_type = {}
        for pos in self.positions.values():
            if pos.instrument_type not in by_type:
                by_type[pos.instrument_type] = []
            by_type[pos.instrument_type].append(pos)

        return {
            "total_positions": total_positions,
            "total_notional": total_notional,
            "positions_by_type": by_type,
            "all_positions": [pos.to_dict() for pos in self.positions.values()],
            "created_at": self.created_at.isoformat(),
            "last_updated": datetime.now().isoformat(),
        }

    def get_total_delta(self) -> float:
        """Calculate total portfolio delta.

        Returns:
            Total delta (positive for net long, negative for net short)
        """
        total_delta = 0.0

        for position in self.positions.values():
            if position.instrument_type == "spot":
                # Spot positions have 1:1 delta
                total_delta += position.qty
            elif position.instrument_type == "perpetual":
                # Perpetual positions have 1:1 delta
                total_delta += position.qty
            # Options would have different delta calculations

        return total_delta

    def get_positions_summary(self) -> str:
        """Get a human-readable summary of positions.

        Returns:
            Formatted string with position summary
        """
        if not self.positions:
            return "No positions"

        lines = ["Portfolio Positions:"]
        for symbol, pos in self.positions.items():
            direction = "LONG" if pos.is_long else "SHORT"
            lines.append(
                f"  {symbol}: {pos.qty:+.4f} @ ${pos.avg_px:.2f} ({direction})"
            )

        total_delta = self.get_total_delta()
        lines.append(f"\nTotal Delta: {total_delta:+.4f} BTC")

        return "\n".join(lines)


# Test data with +5 BTC spot position
def create_test_portfolio() -> Portfolio:
    """Create a test portfolio with +5 BTC spot position."""
    portfolio = Portfolio()

    # Add +5 BTC spot position
    test_position = Position(
        symbol="BTC-USDT-SPOT",
        qty=5.0,
        avg_px=108000.0,
        instrument_type="spot",
        exchange="OKX",
        timestamp=datetime.now(),
    )
    portfolio.add_position(test_position)

    return portfolio
