from typing import Dict, List, Any
from loguru import logger

from .greeks import calculate_portfolio_delta


def portfolio_delta(positions: List[Dict[str, Any]], prices: Dict[str, float]) -> float:
    """Calculate portfolio delta using current prices.

    Args:
        positions: List of position dictionaries
        prices: Dictionary of current prices by symbol

    Returns:
        Total portfolio delta
    """
    return calculate_portfolio_delta(positions, prices)


def calculate_position_risk(
    position: Dict[str, Any], current_price: float
) -> Dict[str, float]:
    """Calculate risk metrics for a single position.

    Args:
        position: Position dictionary
        current_price: Current market price

    Returns:
        Dictionary of risk metrics
    """
    qty = position.get("qty", 0.0)
    avg_px = position.get("avg_px", 0.0)

    # Unrealized P&L
    unrealized_pnl = qty * (current_price - avg_px)

    # Notional value
    notional = abs(qty * current_price)

    # Percentage return
    pct_return = (current_price - avg_px) / avg_px if avg_px > 0 else 0.0

    return {
        "unrealized_pnl": unrealized_pnl,
        "notional": notional,
        "pct_return": pct_return,
        "delta": qty,  # Simplified delta calculation
    }


def calculate_portfolio_risk(
    positions: List[Dict[str, Any]], prices: Dict[str, float]
) -> Dict[str, Any]:
    """Calculate comprehensive portfolio risk metrics.

    Args:
        positions: List of position dictionaries
        prices: Dictionary of current prices by symbol

    Returns:
        Dictionary of portfolio risk metrics
    """
    total_delta = portfolio_delta(positions, prices)
    total_notional = 0.0
    total_unrealized_pnl = 0.0
    position_risks = {}

    for position in positions:
        symbol = position.get("symbol", "")
        current_price = prices.get(symbol, 0.0)

        if current_price > 0:
            risk = calculate_position_risk(position, current_price)
            position_risks[symbol] = risk

            total_notional += risk["notional"]
            total_unrealized_pnl += risk["unrealized_pnl"]

    return {
        "total_delta": total_delta,
        "total_notional": total_notional,
        "total_unrealized_pnl": total_unrealized_pnl,
        "position_risks": position_risks,
        "num_positions": len(positions),
    }


def calculate_delta_exposure(
    positions: List[Dict[str, Any]], prices: Dict[str, float]
) -> Dict[str, float]:
    """Calculate delta exposure by instrument type.

    Args:
        positions: List of position dictionaries
        prices: Dictionary of current prices by symbol

    Returns:
        Dictionary of delta exposure by type
    """
    exposure = {"spot": 0.0, "perpetual": 0.0, "option": 0.0}

    for position in positions:
        instrument_type = position.get("instrument_type", "spot")
        qty = position.get("qty", 0.0)

        if instrument_type in exposure:
            exposure[instrument_type] += qty

    return exposure


def calculate_concentration_risk(
    positions: List[Dict[str, Any]], prices: Dict[str, float]
) -> Dict[str, float]:
    """Calculate concentration risk metrics.

    Args:
        positions: List of position dictionaries
        prices: Dictionary of current prices by symbol

    Returns:
        Dictionary of concentration risk metrics
    """
    if not positions:
        return {"largest_position_pct": 0.0, "top_3_concentration": 0.0}

    position_sizes = []
    total_notional = 0.0

    for position in positions:
        symbol = position.get("symbol", "")
        current_price = prices.get(symbol, 0.0)
        qty = position.get("qty", 0.0)

        if current_price > 0:
            notional = abs(qty * current_price)
            position_sizes.append((symbol, notional))
            total_notional += notional

    if total_notional == 0:
        return {"largest_position_pct": 0.0, "top_3_concentration": 0.0}

    # Sort by notional size
    position_sizes.sort(key=lambda x: x[1], reverse=True)

    # Largest position percentage
    largest_position_pct = (
        (position_sizes[0][1] / total_notional) * 100 if position_sizes else 0.0
    )

    # Top 3 concentration
    top_3_notional = sum(size for _, size in position_sizes[:3])
    top_3_concentration = (top_3_notional / total_notional) * 100

    return {
        "largest_position_pct": largest_position_pct,
        "top_3_concentration": top_3_concentration,
    }


def generate_risk_report(
    positions: List[Dict[str, Any]], prices: Dict[str, float]
) -> str:
    """Generate a human-readable risk report.

    Args:
        positions: List of position dictionaries
        prices: Dictionary of current prices by symbol

    Returns:
        Formatted risk report string
    """
    if not positions:
        return "No positions - no risk to report."

    risk_metrics = calculate_portfolio_risk(positions, prices)
    delta_exposure = calculate_delta_exposure(positions, prices)
    concentration = calculate_concentration_risk(positions, prices)

    lines = [
        "=== PORTFOLIO RISK REPORT ===",
        f"Total Delta: {risk_metrics['total_delta']:+.4f} BTC",
        f"Total Notional: ${risk_metrics['total_notional']:,.2f}",
        f"Unrealized P&L: ${risk_metrics['total_unrealized_pnl']:+,.2f}",
        f"Number of Positions: {risk_metrics['num_positions']}",
        "",
        "Delta Exposure by Type:",
        f"  Spot: {delta_exposure['spot']:+.4f} BTC",
        f"  Perpetual: {delta_exposure['perpetual']:+.4f} BTC",
        f"  Options: {delta_exposure['option']:+.4f} BTC",
        "",
        "Concentration Risk:",
        f"  Largest Position: {concentration['largest_position_pct']:.1f}%",
        f"  Top 3 Concentration: {concentration['top_3_concentration']:.1f}%",
    ]

    return "\n".join(lines)
