import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from loguru import logger


@dataclass
class OptionGreeks:
    """Option Greeks calculated using Black-Scholes."""

    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


@dataclass
class OptionPricing:
    """Option pricing result."""

    theoretical_price: float
    implied_volatility: float
    greeks: OptionGreeks
    bid: float
    ask: float
    mid_price: float


class OptionsPricingService:
    """Service for options pricing and Greeks calculations."""

    def __init__(self):
        self.risk_free_rate = 0.05  # 5% risk-free rate
        self.volatility_surface = {}  # Cache for volatility surface

    def black_scholes_call(
        self, S: float, K: float, T: float, r: float, sigma: float
    ) -> float:
        """Calculate call option price using Black-Scholes.

        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiry (years)
            r: Risk-free rate
            sigma: Volatility

        Returns:
            Call option price
        """
        if T <= 0:
            return max(S - K, 0)

        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        call_price = S * self._normal_cdf(d1) - K * math.exp(-r * T) * self._normal_cdf(
            d2
        )
        return call_price

    def black_scholes_put(
        self, S: float, K: float, T: float, r: float, sigma: float
    ) -> float:
        """Calculate put option price using Black-Scholes.

        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiry (years)
            r: Risk-free rate
            sigma: Volatility

        Returns:
            Put option price
        """
        if T <= 0:
            return max(K - S, 0)

        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        put_price = K * math.exp(-r * T) * self._normal_cdf(-d2) - S * self._normal_cdf(
            -d1
        )
        return put_price

    def calculate_greeks(
        self, S: float, K: float, T: float, r: float, sigma: float, option_type: str
    ) -> OptionGreeks:
        """Calculate option Greeks.

        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiry (years)
            r: Risk-free rate
            sigma: Volatility
            option_type: "call" or "put"

        Returns:
            OptionGreeks object
        """
        if T <= 0:
            # At expiry, Greeks are simplified
            if option_type == "call":
                delta = 1.0 if S > K else 0.0
                gamma = 0.0
                theta = 0.0
                vega = 0.0
                rho = 0.0
            else:  # put
                delta = -1.0 if S < K else 0.0
                gamma = 0.0
                theta = 0.0
                vega = 0.0
                rho = 0.0
        else:
            d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)

            # Delta
            if option_type == "call":
                delta = self._normal_cdf(d1)
            else:  # put
                delta = self._normal_cdf(d1) - 1

            # Gamma (same for calls and puts)
            gamma = self._normal_pdf(d1) / (S * sigma * math.sqrt(T))

            # Theta
            if option_type == "call":
                theta = (
                    -S * self._normal_pdf(d1) * sigma / (2 * math.sqrt(T))
                    - r * K * math.exp(-r * T) * self._normal_cdf(d2)
                ) / 365
            else:  # put
                theta = (
                    -S * self._normal_pdf(d1) * sigma / (2 * math.sqrt(T))
                    + r * K * math.exp(-r * T) * self._normal_cdf(-d2)
                ) / 365

            # Vega (same for calls and puts)
            vega = S * math.sqrt(T) * self._normal_pdf(d1) / 100  # Per 1% vol change

            # Rho
            if option_type == "call":
                rho = (
                    K * T * math.exp(-r * T) * self._normal_cdf(d2) / 100
                )  # Per 1% rate change
            else:  # put
                rho = (
                    -K * T * math.exp(-r * T) * self._normal_cdf(-d2) / 100
                )  # Per 1% rate change

        return OptionGreeks(delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho)

    def calculate_implied_volatility(
        self,
        market_price: float,
        S: float,
        K: float,
        T: float,
        r: float,
        option_type: str,
    ) -> float:
        """Calculate implied volatility using Newton-Raphson method.

        Args:
            market_price: Market price of the option
            S: Current stock price
            K: Strike price
            T: Time to expiry (years)
            r: Risk-free rate
            option_type: "call" or "put"

        Returns:
            Implied volatility
        """
        if T <= 0:
            return 0.0

        # Initial guess
        sigma = 0.5

        for _ in range(100):  # Max 100 iterations
            if option_type == "call":
                price = self.black_scholes_call(S, K, T, r, sigma)
            else:
                price = self.black_scholes_put(S, K, T, r, sigma)

            # Calculate vega for Newton-Raphson
            greeks = self.calculate_greeks(S, K, T, r, sigma, option_type)
            vega = greeks.vega * 100  # Convert back to per 1 vol change

            if abs(vega) < 1e-10:
                break

            # Newton-Raphson update
            diff = market_price - price
            sigma_new = sigma + diff / vega

            # Bounds check
            sigma_new = max(0.01, min(5.0, sigma_new))

            if abs(sigma_new - sigma) < 1e-6:
                sigma = sigma_new
                break

            sigma = sigma_new

        return sigma

    def price_option(
        self,
        S: float,
        K: float,
        T: float,
        sigma: float,
        option_type: str,
        bid: float = None,
        ask: float = None,
    ) -> OptionPricing:
        """Price an option with full Greeks.

        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiry (years)
            sigma: Volatility
            option_type: "call" or "put"
            bid: Market bid price (optional)
            ask: Market ask price (optional)

        Returns:
            OptionPricing object
        """
        r = self.risk_free_rate

        # Calculate theoretical price
        if option_type == "call":
            theoretical_price = self.black_scholes_call(S, K, T, r, sigma)
        else:
            theoretical_price = self.black_scholes_put(S, K, T, r, sigma)

        # Calculate Greeks
        greeks = self.calculate_greeks(S, K, T, r, sigma, option_type)

        # Calculate implied volatility from market prices if available
        implied_vol = sigma
        if bid is not None and ask is not None:
            mid_price = (bid + ask) / 2
            implied_vol = self.calculate_implied_volatility(
                mid_price, S, K, T, r, option_type
            )

        return OptionPricing(
            theoretical_price=theoretical_price,
            implied_volatility=implied_vol,
            greeks=greeks,
            bid=bid or theoretical_price * 0.99,
            ask=ask or theoretical_price * 1.01,
            mid_price=(bid + ask) / 2 if bid and ask else theoretical_price,
        )

    def find_optimal_hedge(
        self,
        portfolio_delta: float,
        S: float,
        option_chain: List,
        target_delta: float = 0.0,
        max_cost: float = None,
    ) -> List[Dict]:
        """Find optimal hedge using options.

        Args:
            portfolio_delta: Current portfolio delta
            S: Current underlying price
            option_chain: Available options
            target_delta: Target portfolio delta
            max_cost: Maximum hedge cost

        Returns:
            List of hedge recommendations
        """
        hedge_required = target_delta - portfolio_delta

        if abs(hedge_required) < 0.01:
            return []

        recommendations = []

        # Find suitable options for hedging
        for option in option_chain:
            if option.option_type not in ["call", "put"]:
                continue

            # Calculate required quantity to achieve target delta
            option_delta = option.delta
            if option.option_type == "put":
                option_delta = -abs(option_delta)  # Put deltas are negative

            # Quantity needed = hedge_required / option_delta
            quantity = hedge_required / option_delta

            # Check if this option can help
            if abs(quantity) < 0.001:  # Too small
                continue

            # Calculate cost
            cost = abs(quantity) * option.mid_price

            if max_cost and cost > max_cost:
                continue

            # Calculate effectiveness
            effectiveness = min(1.0, abs(quantity * option_delta) / abs(hedge_required))

            recommendations.append(
                {
                    "option": option,
                    "quantity": quantity,
                    "cost": cost,
                    "effectiveness": effectiveness,
                    "remaining_delta": hedge_required - (quantity * option_delta),
                }
            )

        # Sort by effectiveness and cost
        recommendations.sort(key=lambda x: (-x["effectiveness"], x["cost"]))

        return recommendations[:5]  # Return top 5 recommendations

    def _normal_cdf(self, x: float) -> float:
        """Calculate cumulative distribution function of standard normal."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _normal_pdf(self, x: float) -> float:
        """Calculate probability density function of standard normal."""
        return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)


# Global instance
options_pricing_service = OptionsPricingService()
