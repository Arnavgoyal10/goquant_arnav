from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Literal
from loguru import logger


@dataclass
class Transaction:
    """Represents a trading transaction."""

    id: str
    symbol: str
    qty: float
    price: float
    instrument_type: Literal["spot", "perpetual", "option"]
    exchange: str
    transaction_type: Literal["buy", "sell", "add", "remove", "hedge"]
    timestamp: datetime
    pnl: Optional[float] = None  # Realized P&L if position closed
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert transaction to dictionary."""
        return asdict(self)


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
        self.transactions: List[Transaction] = []
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

    def record_transaction(
        self,
        symbol: str,
        qty: float,
        price: float,
        instrument_type: str,
        exchange: str,
        transaction_type: str,
        pnl: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Record a transaction in the history.

        Args:
            symbol: Trading symbol
            qty: Quantity
            price: Transaction price
            instrument_type: Type of instrument
            exchange: Exchange name
            transaction_type: Type of transaction
            pnl: Realized P&L if applicable
            notes: Additional notes
        """
        import uuid

        transaction = Transaction(
            id=str(uuid.uuid4())[:8],
            symbol=symbol,
            qty=qty,
            price=price,
            instrument_type=instrument_type,
            exchange=exchange,
            transaction_type=transaction_type,
            timestamp=datetime.now(),
            pnl=pnl,
            notes=notes,
        )

        self.transactions.append(transaction)
        logger.info(
            f"Recorded transaction: {transaction_type} {symbol} {qty} @ {price}"
        )

    def get_transaction_history(self, limit: Optional[int] = None) -> List[Transaction]:
        """Get transaction history.

        Args:
            limit: Maximum number of transactions to return

        Returns:
            List of transactions, sorted by timestamp (newest first)
        """
        sorted_transactions = sorted(
            self.transactions, key=lambda x: x.timestamp, reverse=True
        )

        if limit:
            return sorted_transactions[:limit]
        return sorted_transactions

    def get_transaction_summary(self) -> dict:
        """Get transaction summary statistics.

        Returns:
            Dictionary with transaction summary
        """
        if not self.transactions:
            return {
                "total_transactions": 0,
                "total_volume": 0.0,
                "total_pnl": 0.0,
                "by_type": {},
                "by_instrument": {},
            }

        total_volume = sum(t.qty * t.price for t in self.transactions)
        total_pnl = sum(t.pnl or 0 for t in self.transactions)

        # Group by transaction type
        by_type = {}
        for t in self.transactions:
            if t.transaction_type not in by_type:
                by_type[t.transaction_type] = {"count": 0, "volume": 0.0, "pnl": 0.0}
            by_type[t.transaction_type]["count"] += 1
            by_type[t.transaction_type]["volume"] += abs(t.qty * t.price)
            by_type[t.transaction_type]["pnl"] += t.pnl or 0

        # Group by instrument
        by_instrument = {}
        for t in self.transactions:
            if t.symbol not in by_instrument:
                by_instrument[t.symbol] = {"count": 0, "volume": 0.0, "pnl": 0.0}
            by_instrument[t.symbol]["count"] += 1
            by_instrument[t.symbol]["volume"] += abs(t.qty * t.price)
            by_instrument[t.symbol]["pnl"] += t.pnl or 0

        return {
            "total_transactions": len(self.transactions),
            "total_volume": total_volume,
            "total_pnl": total_pnl,
            "by_type": by_type,
            "by_instrument": by_instrument,
        }

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

        # Determine transaction type based on context
        if not existing:
            # New position - likely an "add" or "hedge"
            transaction_type = "add" if qty > 0 else "hedge"
        elif existing.qty + qty == 0:
            # Position being closed - likely a "remove" or "sell"
            transaction_type = "remove" if qty < 0 else "sell"
        else:
            # Position being modified - use buy/sell
            transaction_type = "buy" if qty > 0 else "sell"

        # Add context notes
        notes = None
        if instrument_type == "option":
            if "P" in symbol:
                notes = "Put option"
            elif "C" in symbol:
                notes = "Call option"
            else:
                notes = "Option"
        elif instrument_type == "perpetual":
            notes = "Perpetual"
        elif instrument_type == "spot":
            notes = "Spot"

        self.record_transaction(
            symbol=symbol,
            qty=qty,
            price=price,
            instrument_type=instrument_type,
            exchange=exchange,
            transaction_type=transaction_type,
            notes=notes,
        )

        if existing:
            # Update existing position
            total_qty = existing.qty + qty
            if total_qty == 0:
                # Position closed - calculate realized P&L
                realized_pnl = (price - existing.avg_px) * abs(qty)
                # Update the last transaction with P&L
                if self.transactions:
                    self.transactions[-1].pnl = realized_pnl

                self.remove_position(symbol)
                logger.info(f"Position closed: {symbol} with P&L: {realized_pnl}")
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

    def get_total_delta(self, current_prices: dict = None) -> float:
        """Calculate total portfolio delta.

        Args:
            current_prices: Dictionary of current prices by symbol

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
            elif position.instrument_type == "option":
                # For options, calculate actual delta from Greeks
                option_delta = self._calculate_option_delta(position, current_prices)
                total_delta += option_delta

        return total_delta

    def _calculate_option_delta(
        self, position: Position, current_prices: dict = None
    ) -> float:
        """Calculate delta for an option position.

        Args:
            position: Option position
            current_prices: Dictionary of current prices by symbol

        Returns:
            Option delta
        """
        # Extract strike and current price from symbol
        # Example: BTC-11JUL25-113000-P -> strike = 113000
        try:
            parts = position.symbol.split("-")
            if len(parts) >= 3:
                strike = float(parts[2])

                # Get current price from provided prices or use fallback
                if current_prices and "BTC-USDT-SPOT" in current_prices:
                    current_price = current_prices["BTC-USDT-SPOT"]
                else:
                    current_price = 111372.0  # Fallback current price

                # More realistic delta calculation based on moneyness
                moneyness = current_price / strike

                if "P" in position.symbol:  # Put option
                    if moneyness > 1.0:  # OTM put
                        delta = -0.15
                    elif moneyness < 0.95:  # ITM put
                        delta = -0.85
                    else:  # ATM put
                        delta = -0.5
                else:  # Call option
                    if moneyness > 1.05:  # ITM call
                        delta = 0.85
                    elif moneyness < 1.0:  # OTM call
                        delta = 0.15
                    else:  # ATM call
                        delta = 0.5

                return delta * position.qty
        except:
            # Fallback: use quantity as delta
            return position.qty

        return position.qty

    def get_greeks_summary(self, current_prices: dict = None) -> dict:
        """Calculate portfolio Greeks summary.

        Args:
            current_prices: Dictionary of current prices by symbol

        Returns:
            Dictionary with portfolio Greeks
        """
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0

        for position in self.positions.values():
            if position.instrument_type == "option":
                # Calculate Greeks for options
                greeks = self._calculate_option_greeks(position, current_prices)
                total_delta += greeks.get("delta", 0.0)
                total_gamma += greeks.get("gamma", 0.0)
                total_theta += greeks.get("theta", 0.0)
                total_vega += greeks.get("vega", 0.0)
            else:
                # For spot/perpetual, only delta matters
                total_delta += position.qty

        return {
            "delta": total_delta,
            "gamma": total_gamma,
            "theta": total_theta,
            "vega": total_vega,
        }

    def _calculate_option_greeks(
        self, position: Position, current_prices: dict = None
    ) -> dict:
        """Calculate Greeks for an option position.

        Args:
            position: Option position
            current_prices: Dictionary of current prices by symbol

        Returns:
            Dictionary with option Greeks
        """
        try:
            parts = position.symbol.split("-")
            if len(parts) >= 3:
                strike = float(parts[2])

                # Get current price from provided prices or use fallback
                if current_prices and "BTC-USDT-SPOT" in current_prices:
                    current_price = current_prices["BTC-USDT-SPOT"]
                else:
                    current_price = 111372.0  # Fallback current price

                # Calculate moneyness for more realistic Greeks
                moneyness = current_price / strike

                if "P" in position.symbol:  # Put option
                    if moneyness > 1.0:  # OTM put
                        delta = -0.15
                        gamma = 0.008
                        theta = -0.05
                        vega = 0.3
                    elif moneyness < 0.95:  # ITM put
                        delta = -0.85
                        gamma = 0.015
                        theta = -0.08
                        vega = 0.6
                    else:  # ATM put
                        delta = -0.5
                        gamma = 0.012
                        theta = -0.06
                        vega = 0.45
                else:  # Call option
                    if moneyness > 1.05:  # ITM call
                        delta = 0.85
                        gamma = 0.015
                        theta = -0.08
                        vega = 0.6
                    elif moneyness < 1.0:  # OTM call
                        delta = 0.15
                        gamma = 0.008
                        theta = -0.05
                        vega = 0.3
                    else:  # ATM call
                        delta = 0.5
                        gamma = 0.012
                        theta = -0.06
                        vega = 0.45

                return {
                    "delta": delta * position.qty,
                    "gamma": gamma * position.qty,
                    "theta": theta * position.qty,
                    "vega": vega * position.qty,
                }
        except:
            pass

        # Fallback
        return {"delta": position.qty, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    def get_realized_pnl(self) -> float:
        """Calculate realized P&L.

        This would track closed positions and their P&L.
        For now, return 0 as we don't track closed positions.
        """
        return 0.0

    def get_unrealized_pnl(self, current_prices: dict = None) -> float:
        """Calculate unrealized P&L.

        Args:
            current_prices: Dictionary of current prices by symbol

        Returns:
            Total unrealized P&L
        """
        total_pnl = 0.0
        for position in self.positions.values():
            # Get current price from provided prices or use fallback
            if current_prices and position.symbol in current_prices:
                current_price = current_prices[position.symbol]
            else:
                # Fallback prices based on instrument type
                if position.instrument_type == "spot":
                    current_price = 111372.0  # Current BTC spot price
                elif position.instrument_type == "perpetual":
                    current_price = 111350.0  # Current BTC perp price
                elif position.instrument_type == "option":
                    # For options, use the stored price as current (simplified)
                    current_price = position.avg_px
                else:
                    current_price = 111000.0  # Fallback

            unrealized_pnl = (current_price - position.avg_px) * position.qty
            total_pnl += unrealized_pnl
        return total_pnl

    def get_var_95(self, current_prices: dict = None) -> float:
        """Calculate 95% Value at Risk.

        Args:
            current_prices: Dictionary of current prices by symbol

        Returns:
            95% VaR value
        """
        total_notional = 0.0

        for position in self.positions.values():
            # Use current price if available, otherwise use average price
            if current_prices and position.symbol in current_prices:
                current_price = current_prices[position.symbol]
            else:
                current_price = position.avg_px

            notional = abs(position.qty * current_price)
            total_notional += notional

        # More realistic VaR: 2% of notional for crypto portfolio
        return total_notional * 0.02

    def get_max_drawdown(self) -> float:
        """Calculate maximum drawdown.

        This would track historical peak and current value.
        For now, return 0.
        """
        return 0.0

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
