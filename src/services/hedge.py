"""Hedge service for calculating hedge recommendations and risk metrics."""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from .options_pricing import options_pricing_service
from ..exchanges.deribit_options import OptionContract


@dataclass
class HedgeRecommendation:
    """A hedge recommendation."""

    hedge_type: str
    symbol: str
    quantity: float
    direction: str  # "long" or "short"
    target_delta: float
    estimated_cost: float
    risk_reduction: float
    description: str
    option_contract: Optional[OptionContract] = None  # For options hedges


@dataclass
class HedgeMetrics:
    """Hedge performance metrics."""

    current_delta: float
    target_delta: float
    hedge_required: float
    cost_of_hedge: float
    risk_reduction: float
    hedge_effectiveness: float


class HedgeService:
    """Service for hedge calculations and recommendations."""

    def __init__(self):
        # Hedge effectiveness factors
        self.hedge_effectiveness = {
            "perp_delta_neutral": 0.99,  # 99% effective for delta-neutral
            "protective_put": 0.85,  # 85% effective for protective puts
            "covered_call": 0.80,  # 80% effective for covered calls
            "collar": 0.90,  # 90% effective for collars
            "dynamic_hedge": 0.95,  # 95% effective for dynamic hedging
        }

    async def calculate_hedge_recommendations(
        self,
        portfolio_delta: float,
        positions: Dict,
        option_chain: List[OptionContract] = None,
    ) -> List[HedgeRecommendation]:
        """Calculate hedge recommendations based on portfolio delta.

        Args:
            portfolio_delta: Current portfolio delta
            positions: Current portfolio positions
            option_chain: Available options for hedging

        Returns:
            List of hedge recommendations
        """
        recommendations = []

        # Skip if already delta-neutral
        if abs(portfolio_delta) < 0.01:
            return recommendations

        # Perpetual Delta-Neutral Hedge
        if abs(portfolio_delta) >= 0.01:
            hedge_qty = -portfolio_delta
            direction = "short" if hedge_qty < 0 else "long"

            recommendations.append(
                HedgeRecommendation(
                    hedge_type="perp_delta_neutral",
                    symbol="BTC-USDT-PERP",
                    quantity=abs(hedge_qty),
                    direction=direction,
                    target_delta=0.0,
                    estimated_cost=abs(hedge_qty)
                    * 107000
                    * 0.0005,  # Rough cost estimate
                    risk_reduction=abs(portfolio_delta)
                    * 107000
                    * 0.1,  # 10% volatility
                    description=f"Perpetual {direction.upper()} to achieve delta-neutral portfolio",
                )
            )

        # Options-based hedges if option chain is available
        if option_chain and portfolio_delta > 0.01:
            # Find optimal protective put
            put_options = [opt for opt in option_chain if opt.option_type == "put"]
            if put_options:
                # Find ATM or slightly OTM put
                current_price = 107000  # TODO: Get from market data
                best_put = min(put_options, key=lambda x: abs(x.strike - current_price))

                # Calculate required quantity for 50% delta reduction
                target_delta = portfolio_delta * 0.5
                hedge_delta = portfolio_delta - target_delta
                put_quantity = hedge_delta / abs(best_put.delta)

                recommendations.append(
                    HedgeRecommendation(
                        hedge_type="protective_put",
                        symbol=best_put.symbol,
                        quantity=put_quantity,
                        direction="buy",
                        target_delta=target_delta,
                        estimated_cost=put_quantity * best_put.mid_price,
                        risk_reduction=hedge_delta * current_price * 0.15,
                        description=f"Protective put at {best_put.strike} strike",
                        option_contract=best_put,
                    )
                )

            # Find optimal covered call
            call_options = [opt for opt in option_chain if opt.option_type == "call"]
            if call_options:
                # Find slightly OTM call for income
                current_price = 107000
                otm_calls = [
                    opt for opt in call_options if opt.strike > current_price * 1.05
                ]
                if otm_calls:
                    best_call = min(otm_calls, key=lambda x: x.strike)

                    # Calculate quantity for 30% delta reduction
                    target_delta = portfolio_delta * 0.7
                    hedge_delta = portfolio_delta - target_delta
                    call_quantity = hedge_delta / best_call.delta

                    recommendations.append(
                        HedgeRecommendation(
                            hedge_type="covered_call",
                            symbol=best_call.symbol,
                            quantity=call_quantity,
                            direction="sell",
                            target_delta=target_delta,
                            estimated_cost=-call_quantity
                            * best_call.mid_price,  # Negative (income)
                            risk_reduction=hedge_delta * current_price * 0.08,
                            description=f"Covered call at {best_call.strike} strike",
                            option_contract=best_call,
                        )
                    )

            # Collar strategy (protective put + covered call)
            if put_options and call_options:
                current_price = 107000
                best_put = min(
                    put_options, key=lambda x: abs(x.strike - current_price * 0.95)
                )
                otm_calls = [
                    opt for opt in call_options if opt.strike > current_price * 1.10
                ]

                if otm_calls:
                    best_call = min(otm_calls, key=lambda x: x.strike)

                    # Calculate collar quantities
                    put_quantity = portfolio_delta / abs(best_put.delta)
                    call_quantity = portfolio_delta / best_call.delta

                    # Net cost (put cost - call premium)
                    net_cost = (put_quantity * best_put.mid_price) - (
                        call_quantity * best_call.mid_price
                    )

                    recommendations.append(
                        HedgeRecommendation(
                            hedge_type="collar",
                            symbol=f"{best_put.symbol} + {best_call.symbol}",
                            quantity=min(put_quantity, call_quantity),
                            direction="buy_put_sell_call",
                            target_delta=portfolio_delta * 0.3,  # Significant reduction
                            estimated_cost=net_cost,
                            risk_reduction=portfolio_delta * current_price * 0.20,
                            description=f"Collar: {best_put.strike} put + {best_call.strike} call",
                            option_contract=best_put,  # Store put as primary
                        )
                    )

        return recommendations

    def calculate_hedge_metrics(
        self,
        portfolio_delta: float,
        hedge_qty: float,
        hedge_type: str,
        option_contract: OptionContract = None,
    ) -> HedgeMetrics:
        """Calculate hedge performance metrics.

        Args:
            portfolio_delta: Current portfolio delta
            hedge_qty: Hedge quantity
            hedge_type: Type of hedge
            option_contract: Option contract for options hedges

        Returns:
            Hedge metrics
        """
        effectiveness = self.hedge_effectiveness.get(hedge_type, 0.8)

        # Calculate new delta after hedge
        if hedge_type == "perp_delta_neutral":
            new_delta = portfolio_delta + hedge_qty
        elif option_contract:
            # Use actual option delta
            option_delta = option_contract.delta
            if hedge_type == "covered_call":
                option_delta = -option_delta  # Selling calls reduces delta
            new_delta = portfolio_delta + (hedge_qty * option_delta)
        else:
            # For options, delta impact depends on option delta
            option_delta = 0.5  # Rough estimate
            new_delta = portfolio_delta + (hedge_qty * option_delta)

        # Calculate risk reduction
        risk_reduction = (
            abs(portfolio_delta - new_delta) * 107000 * 0.1
        )  # 10% volatility

        # Calculate hedge effectiveness
        hedge_effectiveness = (
            effectiveness * (1 - abs(new_delta) / abs(portfolio_delta))
            if portfolio_delta != 0
            else 1.0
        )

        return HedgeMetrics(
            current_delta=portfolio_delta,
            target_delta=new_delta,
            hedge_required=abs(hedge_qty),
            cost_of_hedge=abs(hedge_qty) * 107000 * 0.0005,  # Rough cost
            risk_reduction=risk_reduction,
            hedge_effectiveness=hedge_effectiveness,
        )

    def get_hedge_summary(
        self, portfolio_delta: float, recommendations: List[HedgeRecommendation]
    ) -> str:
        """Get a human-readable hedge summary.

        Args:
            portfolio_delta: Current portfolio delta
            recommendations: List of hedge recommendations

        Returns:
            Formatted hedge summary
        """
        if not recommendations:
            return "✅ Portfolio is already optimally hedged."

        summary = f"🛡️ *Hedge Recommendations*\n\nCurrent Delta: {portfolio_delta:+.4f} BTC\n\n"

        for i, rec in enumerate(recommendations, 1):
            direction_emoji = "📉" if rec.direction in ["short", "sell"] else "📈"

            # Add option details if available
            option_details = ""
            if rec.option_contract:
                option_details = f"\n   Strike: ${rec.option_contract.strike:,.0f}"
                option_details += (
                    f" | Expiry: {rec.option_contract.expiry.strftime('%Y-%m-%d')}"
                )
                option_details += f" | IV: {rec.option_contract.implied_volatility:.1%}"

            summary += (
                f"{i}. {direction_emoji} *{rec.hedge_type.replace('_', ' ').title()}*\n"
                f"   {rec.symbol}: {rec.quantity:.4f} {rec.direction.upper()}\n"
                f"   Cost: ${rec.estimated_cost:.2f}\n"
                f"   Risk Reduction: ${rec.risk_reduction:.2f}\n"
                f"   {rec.description}{option_details}\n\n"
            )

        return summary

    def validate_hedge(
        self,
        portfolio_delta: float,
        hedge_qty: float,
        hedge_type: str,
        option_contract: OptionContract = None,
    ) -> Tuple[bool, str]:
        """Validate a hedge proposal.

        Args:
            portfolio_delta: Current portfolio delta
            hedge_qty: Proposed hedge quantity
            hedge_type: Type of hedge
            option_contract: Option contract for options hedges

        Returns:
            Tuple of (is_valid, error_message)
        """
        if hedge_type == "perp_delta_neutral":
            # For delta-neutral, hedge should be opposite of current delta
            expected_hedge = -portfolio_delta
            if abs(hedge_qty - abs(expected_hedge)) > 0.01:
                return (
                    False,
                    f"Hedge quantity should be {abs(expected_hedge):.4f} for delta-neutral",
                )

        if hedge_qty <= 0:
            return False, "Hedge quantity must be positive"

        if abs(portfolio_delta) < 0.01 and hedge_type == "perp_delta_neutral":
            return False, "Portfolio is already delta-neutral"

        # Validate options hedges
        if option_contract and hedge_type in [
            "protective_put",
            "covered_call",
            "collar",
        ]:
            if hedge_type == "protective_put" and option_contract.option_type != "put":
                return False, "Protective put requires a put option"
            if hedge_type == "covered_call" and option_contract.option_type != "call":
                return False, "Covered call requires a call option"

        return True, ""

    async def get_dynamic_hedge_recommendation(
        self,
        portfolio_delta: float,
        option_chain: List[OptionContract],
        target_delta: float = 0.0,
        max_cost: float = None,
    ) -> List[HedgeRecommendation]:
        """Get dynamic hedge recommendations using options pricing service.

        Args:
            portfolio_delta: Current portfolio delta
            option_chain: Available options
            target_delta: Target portfolio delta
            max_cost: Maximum hedge cost

        Returns:
            List of dynamic hedge recommendations
        """
        if not option_chain:
            return []

        current_price = 107000  # TODO: Get from market data

        # Use options pricing service to find optimal hedge
        recommendations_data = options_pricing_service.find_optimal_hedge(
            portfolio_delta, current_price, option_chain, target_delta, max_cost
        )

        recommendations = []
        for rec_data in recommendations_data:
            option = rec_data["option"]
            quantity = rec_data["quantity"]
            cost = rec_data["cost"]
            effectiveness = rec_data["effectiveness"]

            # Determine hedge type based on option
            if option.option_type == "put":
                hedge_type = "protective_put"
                direction = "buy"
            else:
                hedge_type = "covered_call"
                direction = "sell"

            recommendations.append(
                HedgeRecommendation(
                    hedge_type=hedge_type,
                    symbol=option.symbol,
                    quantity=abs(quantity),
                    direction=direction,
                    target_delta=target_delta,
                    estimated_cost=cost,
                    risk_reduction=abs(quantity * option.delta) * current_price * 0.1,
                    description=f"Dynamic {hedge_type} with {effectiveness:.1%} effectiveness",
                    option_contract=option,
                )
            )

        return recommendations


# Global instance
hedge_service = HedgeService()
