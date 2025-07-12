import math
from typing import Dict, Any
from loguru import logger


def normal_cdf(x: float) -> float:
    """Calculate the cumulative distribution function of the standard normal distribution.

    Args:
        x: Input value

    Returns:
        CDF value
    """
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def normal_pdf(x: float) -> float:
    """Calculate the probability density function of the standard normal distribution.

    Args:
        x: Input value

    Returns:
        PDF value
    """
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def black_scholes_delta(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> float:
    """Calculate Black-Scholes delta for options.

    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free rate
        sigma: Volatility
        option_type: "call" or "put"

    Returns:
        Delta value
    """
    if T <= 0:
        return 1.0 if option_type == "call" else -1.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))

    if option_type == "call":
        return normal_cdf(d1)
    else:  # put
        return normal_cdf(d1) - 1


def black_scholes_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate Black-Scholes gamma for options.

    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free rate
        sigma: Volatility

    Returns:
        Gamma value
    """
    if T <= 0:
        return 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    return normal_pdf(d1) / (S * sigma * math.sqrt(T))


def black_scholes_theta(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> float:
    """Calculate Black-Scholes theta for options.

    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free rate
        sigma: Volatility
        option_type: "call" or "put"

    Returns:
        Theta value (per year)
    """
    if T <= 0:
        return 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "call":
        return -S * normal_pdf(d1) * sigma / (2 * math.sqrt(T)) - r * K * math.exp(
            -r * T
        ) * normal_cdf(d2)
    else:  # put
        return -S * normal_pdf(d1) * sigma / (2 * math.sqrt(T)) + r * K * math.exp(
            -r * T
        ) * normal_cdf(-d2)


def spot_delta(qty: float) -> float:
    """Calculate delta for spot positions.

    Args:
        qty: Position quantity

    Returns:
        Delta value (1:1 for spot)
    """
    return qty


def perpetual_delta(qty: float) -> float:
    """Calculate delta for perpetual futures positions.

    Args:
        qty: Position quantity

    Returns:
        Delta value (1:1 for perpetuals)
    """
    return qty


def option_delta(qty: float, option_delta: float) -> float:
    """Calculate delta for option positions.

    Args:
        qty: Number of contracts
        option_delta: Per-contract delta

    Returns:
        Total delta
    """
    return qty * option_delta


def calculate_position_delta(position: Dict[str, Any], current_price: float) -> float:
    """Calculate delta for a single position.

    Args:
        position: Position dictionary
        current_price: Current market price

    Returns:
        Position delta
    """
    instrument_type = position.get("instrument_type", "spot")
    qty = position.get("qty", 0.0)

    if instrument_type == "spot":
        return spot_delta(qty)
    elif instrument_type == "perpetual":
        return perpetual_delta(qty)
    elif instrument_type == "option":
        # For options, we'd need more data like strike, expiry, etc.
        # For now, assume 1:1 delta (simplified)
        return option_delta(qty, 1.0)
    else:
        logger.warning(f"Unknown instrument type: {instrument_type}")
        return 0.0


def calculate_portfolio_delta(positions: list, prices: Dict[str, float]) -> float:
    """Calculate total portfolio delta.

    Args:
        positions: List of position dictionaries
        prices: Dictionary of current prices by symbol

    Returns:
        Total portfolio delta
    """
    total_delta = 0.0

    for position in positions:
        symbol = position.get("symbol", "")
        current_price = prices.get(symbol, 0.0)

        if current_price > 0:
            position_delta = calculate_position_delta(position, current_price)
            total_delta += position_delta
            logger.debug(f"Position {symbol}: delta = {position_delta}")

    return total_delta
