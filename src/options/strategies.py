from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from loguru import logger


@dataclass
class OptionLeg:
    """Represents a single option leg in a strategy."""

    symbol: str
    qty: float  # Positive for long, negative for short
    strike: float
    expiry: str
    option_type: str  # "call" or "put"
    price: float
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0


@dataclass
class StrategyPayoff:
    """Represents the payoff profile of an option strategy."""

    max_profit: float
    max_loss: float
    breakeven_points: List[float]
    payoff_at_expiry: Dict[float, float]  # price -> payoff
    current_pnl: float
    margin_required: float


class OptionStrategies:
    """Collection of option strategies with payoff and greek calculations."""

    @staticmethod
    def straddle(
        strike: float,
        call_price: float,
        put_price: float,
        current_price: float,
        call_delta: float = 0.5,
        put_delta: float = -0.5,
        call_gamma: float = 0.02,
        put_gamma: float = 0.02,
        call_theta: float = -0.1,
        put_theta: float = -0.1,
        call_vega: float = 0.8,
        put_vega: float = 0.8,
    ) -> Tuple[List[OptionLeg], StrategyPayoff]:
        """
        Create a straddle strategy: long 1 put + 1 call at same strike.

        Args:
            strike: Strike price for both options
            call_price: Call option price
            put_price: Put option price
            current_price: Current underlying price
            call_delta, put_delta: Option deltas
            call_gamma, put_gamma: Option gammas
            call_theta, put_theta: Option thetas
            call_vega, put_vega: Option vegas

        Returns:
            Tuple of (legs, payoff_profile)
        """
        # Create option legs
        call_leg = OptionLeg(
            symbol=f"BTC-{strike}-C",
            qty=1.0,
            strike=strike,
            expiry="25JUL25",
            option_type="call",
            price=call_price,
            delta=call_delta,
            gamma=call_gamma,
            theta=call_theta,
            vega=call_vega,
        )

        put_leg = OptionLeg(
            symbol=f"BTC-{strike}-P",
            qty=1.0,
            strike=strike,
            expiry="25JUL25",
            option_type="put",
            price=put_price,
            delta=put_delta,
            gamma=put_gamma,
            theta=put_theta,
            vega=put_vega,
        )

        legs = [call_leg, put_leg]

        # Calculate payoff profile
        total_cost = call_price + put_price
        max_loss = -total_cost  # Maximum loss is the premium paid

        # Breakeven points
        breakeven_high = strike + total_cost
        breakeven_low = strike - total_cost

        # Calculate payoff at different price levels
        payoff_at_expiry = {}
        for price in range(int(strike * 0.7), int(strike * 1.3) + 1, 1000):
            call_payoff = max(0, price - strike)
            put_payoff = max(0, strike - price)
            total_payoff = call_payoff + put_payoff - total_cost
            payoff_at_expiry[price] = total_payoff

        # Current P&L
        current_call_value = max(0, current_price - strike)
        current_put_value = max(0, strike - current_price)
        current_pnl = current_call_value + current_put_value - total_cost

        payoff = StrategyPayoff(
            max_profit=float("inf"),  # Unlimited upside
            max_loss=max_loss,
            breakeven_points=[breakeven_low, breakeven_high],
            payoff_at_expiry=payoff_at_expiry,
            current_pnl=current_pnl,
            margin_required=total_cost,
        )

        return legs, payoff

    @staticmethod
    def butterfly(
        lower_strike: float,
        middle_strike: float,
        upper_strike: float,
        lower_call_price: float,
        middle_call_price: float,
        upper_call_price: float,
        current_price: float,
        is_call_butterfly: bool = True,
    ) -> Tuple[List[OptionLeg], StrategyPayoff]:
        """
        Create a butterfly strategy.

        Call Butterfly: long 1 ITM call, short 2 ATM calls, long 1 OTM call
        Put Butterfly: long 1 ITM put, short 2 ATM puts, long 1 OTM put

        Args:
            lower_strike: Lower strike price
            middle_strike: Middle strike price (should be ATM)
            upper_strike: Upper strike price
            lower_call_price: Lower strike option price
            middle_call_price: Middle strike option price
            upper_call_price: Upper strike option price
            current_price: Current underlying price
            is_call_butterfly: True for call butterfly, False for put butterfly

        Returns:
            Tuple of (legs, payoff_profile)
        """
        option_type = "call" if is_call_butterfly else "put"

        # Create option legs
        lower_leg = OptionLeg(
            symbol=f"BTC-{lower_strike}-{option_type.upper()[0]}",
            qty=1.0,
            strike=lower_strike,
            expiry="25JUL25",
            option_type=option_type,
            price=lower_call_price,
        )

        middle_leg = OptionLeg(
            symbol=f"BTC-{middle_strike}-{option_type.upper()[0]}",
            qty=-2.0,  # Short 2 contracts
            strike=middle_strike,
            expiry="25JUL25",
            option_type=option_type,
            price=middle_call_price,
        )

        upper_leg = OptionLeg(
            symbol=f"BTC-{upper_strike}-{option_type.upper()[0]}",
            qty=1.0,
            strike=upper_strike,
            expiry="25JUL25",
            option_type=option_type,
            price=upper_call_price,
        )

        legs = [lower_leg, middle_leg, upper_leg]

        # Calculate payoff profile
        total_cost = lower_call_price - 2 * middle_call_price + upper_call_price
        max_profit = middle_strike - lower_strike - total_cost
        max_loss = total_cost

        # Breakeven points
        breakeven_low = lower_strike + total_cost
        breakeven_high = upper_strike - total_cost

        # Calculate payoff at different price levels
        payoff_at_expiry = {}
        for price in range(int(lower_strike * 0.8), int(upper_strike * 1.2) + 1, 1000):
            if is_call_butterfly:
                lower_payoff = max(0, price - lower_strike)
                middle_payoff = -2 * max(0, price - middle_strike)
                upper_payoff = max(0, price - upper_strike)
            else:
                lower_payoff = max(0, lower_strike - price)
                middle_payoff = -2 * max(0, middle_strike - price)
                upper_payoff = max(0, upper_strike - price)

            total_payoff = lower_payoff + middle_payoff + upper_payoff - total_cost
            payoff_at_expiry[price] = total_payoff

        # Current P&L
        if is_call_butterfly:
            current_lower_value = max(0, current_price - lower_strike)
            current_middle_value = -2 * max(0, current_price - middle_strike)
            current_upper_value = max(0, current_price - upper_strike)
        else:
            current_lower_value = max(0, lower_strike - current_price)
            current_middle_value = -2 * max(0, middle_strike - current_price)
            current_upper_value = max(0, upper_strike - current_price)

        current_pnl = (
            current_lower_value
            + current_middle_value
            + current_upper_value
            - total_cost
        )

        payoff = StrategyPayoff(
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven_points=[breakeven_low, breakeven_high],
            payoff_at_expiry=payoff_at_expiry,
            current_pnl=current_pnl,
            margin_required=total_cost,
        )

        return legs, payoff

    @staticmethod
    def iron_condor(
        put_lower_strike: float,
        put_upper_strike: float,
        call_lower_strike: float,
        call_upper_strike: float,
        put_lower_price: float,
        put_upper_price: float,
        call_lower_price: float,
        call_upper_price: float,
        current_price: float,
    ) -> Tuple[List[OptionLeg], StrategyPayoff]:
        """
        Create an iron condor strategy.

        Short 1 lower-strike put, long 1 further-OTM put;
        Short 1 lower-strike call, long 1 further-OTM call.

        Args:
            put_lower_strike: Lower put strike (short)
            put_upper_strike: Upper put strike (long)
            call_lower_strike: Lower call strike (short)
            call_upper_strike: Upper call strike (long)
            put_lower_price: Lower put price
            put_upper_price: Upper put price
            call_lower_price: Lower call price
            call_upper_price: Upper call price
            current_price: Current underlying price

        Returns:
            Tuple of (legs, payoff_profile)
        """
        # Create option legs
        put_lower_leg = OptionLeg(
            symbol=f"BTC-{put_lower_strike}-P",
            qty=-1.0,  # Short
            strike=put_lower_strike,
            expiry="25JUL25",
            option_type="put",
            price=put_lower_price,
        )

        put_upper_leg = OptionLeg(
            symbol=f"BTC-{put_upper_strike}-P",
            qty=1.0,  # Long
            strike=put_upper_strike,
            expiry="25JUL25",
            option_type="put",
            price=put_upper_price,
        )

        call_lower_leg = OptionLeg(
            symbol=f"BTC-{call_lower_strike}-C",
            qty=-1.0,  # Short
            strike=call_lower_strike,
            expiry="25JUL25",
            option_type="call",
            price=call_lower_price,
        )

        call_upper_leg = OptionLeg(
            symbol=f"BTC-{call_upper_strike}-C",
            qty=1.0,  # Long
            strike=call_upper_strike,
            expiry="25JUL25",
            option_type="call",
            price=call_upper_price,
        )

        legs = [put_lower_leg, put_upper_leg, call_lower_leg, call_upper_leg]

        # Calculate payoff profile
        net_credit = (
            put_lower_price - put_upper_price + call_lower_price - call_upper_price
        )
        max_profit = net_credit
        max_loss_put_side = put_upper_strike - put_lower_strike - net_credit
        max_loss_call_side = call_upper_strike - call_lower_strike - net_credit
        max_loss = max(max_loss_put_side, max_loss_call_side)

        # Breakeven points
        breakeven_low = put_lower_strike + net_credit
        breakeven_high = call_lower_strike - net_credit

        # Calculate payoff at different price levels
        payoff_at_expiry = {}
        for price in range(
            int(put_lower_strike * 0.8), int(call_upper_strike * 1.2) + 1, 1000
        ):
            # Put side payoff
            put_lower_payoff = -max(0, put_lower_strike - price)
            put_upper_payoff = max(0, put_upper_strike - price)

            # Call side payoff
            call_lower_payoff = -max(0, price - call_lower_strike)
            call_upper_payoff = max(0, price - call_upper_strike)

            total_payoff = (
                put_lower_payoff
                + put_upper_payoff
                + call_lower_payoff
                + call_upper_payoff
                + net_credit
            )
            payoff_at_expiry[price] = total_payoff

        # Current P&L
        current_put_lower_value = -max(0, put_lower_strike - current_price)
        current_put_upper_value = max(0, put_upper_strike - current_price)
        current_call_lower_value = -max(0, current_price - call_lower_strike)
        current_call_upper_value = max(0, current_price - call_upper_strike)

        current_pnl = (
            current_put_lower_value
            + current_put_upper_value
            + current_call_lower_value
            + current_call_upper_value
            + net_credit
        )

        payoff = StrategyPayoff(
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven_points=[breakeven_low, breakeven_high],
            payoff_at_expiry=payoff_at_expiry,
            current_pnl=current_pnl,
            margin_required=net_credit,
        )

        return legs, payoff

    @staticmethod
    def calculate_strategy_greeks(legs: List[OptionLeg]) -> Dict[str, float]:
        """Calculate aggregate Greeks for a strategy."""
        total_delta = sum(leg.delta * leg.qty for leg in legs)
        total_gamma = sum(leg.gamma * leg.qty for leg in legs)
        total_theta = sum(leg.theta * leg.qty for leg in legs)
        total_vega = sum(leg.vega * leg.qty for leg in legs)

        return {
            "delta": total_delta,
            "gamma": total_gamma,
            "theta": total_theta,
            "vega": total_vega,
        }

    @staticmethod
    def get_strategy_description(strategy_name: str) -> str:
        """Get description of a strategy."""
        descriptions = {
            "straddle": "Long 1 put + 1 call at same strike. Unlimited profit potential, limited risk.",
            "butterfly": "Long 1 ITM, short 2 ATM, long 1 OTM. Limited profit and loss.",
            "iron_condor": "Short put spread + short call spread. Defined risk and reward.",
        }
        return descriptions.get(strategy_name, "Unknown strategy")


# Strategy factory functions for easy creation
def create_straddle_strategy(
    strike: float, current_price: float
) -> Tuple[List[OptionLeg], StrategyPayoff]:
    """Create a straddle strategy with realistic prices."""
    call_price = max(0.01, (current_price - strike) * 0.1)  # Simplified pricing
    put_price = max(0.01, (strike - current_price) * 0.1)

    return OptionStrategies.straddle(
        strike=strike,
        call_price=call_price,
        put_price=put_price,
        current_price=current_price,
    )


def create_butterfly_strategy(
    lower_strike: float,
    middle_strike: float,
    upper_strike: float,
    current_price: float,
    is_call: bool = True,
) -> Tuple[List[OptionLeg], StrategyPayoff]:
    """Create a butterfly strategy with realistic prices."""
    # Simplified pricing
    lower_price = max(0.01, abs(current_price - lower_strike) * 0.1)
    middle_price = max(0.01, abs(current_price - middle_strike) * 0.1)
    upper_price = max(0.01, abs(current_price - upper_strike) * 0.1)

    return OptionStrategies.butterfly(
        lower_strike=lower_strike,
        middle_strike=middle_strike,
        upper_strike=upper_strike,
        lower_call_price=lower_price,
        middle_call_price=middle_price,
        upper_call_price=upper_price,
        current_price=current_price,
        is_call_butterfly=is_call,
    )


def create_iron_condor_strategy(
    put_lower: float,
    put_upper: float,
    call_lower: float,
    call_upper: float,
    current_price: float,
) -> Tuple[List[OptionLeg], StrategyPayoff]:
    """Create an iron condor strategy with realistic prices."""
    # Simplified pricing
    put_lower_price = max(0.01, (put_lower - current_price) * 0.1)
    put_upper_price = max(0.01, (put_upper - current_price) * 0.1)
    call_lower_price = max(0.01, (current_price - call_lower) * 0.1)
    call_upper_price = max(0.01, (current_price - call_upper) * 0.1)

    return OptionStrategies.iron_condor(
        put_lower_strike=put_lower,
        put_upper_strike=put_upper,
        call_lower_strike=call_lower,
        call_upper_strike=call_upper,
        put_lower_price=put_lower_price,
        put_upper_price=put_upper_price,
        call_lower_price=call_lower_price,
        call_upper_price=call_upper_price,
        current_price=current_price,
    )
