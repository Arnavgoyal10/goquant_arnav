import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.options.strategies import (
    OptionStrategies,
    create_straddle_strategy,
    create_butterfly_strategy,
    create_iron_condor_strategy,
)


async def test_strategies():
    """Test the new option strategies."""
    print("🦋 Testing Option Strategies\n")

    # Test parameters
    current_price = 50000.0
    strike = 50000.0

    print(f"Current Price: ${current_price:,.2f}")
    print(f"Strike: ${strike:,.2f}\n")

    # Test Straddle
    print("=== Straddle Strategy ===")
    legs, payoff = create_straddle_strategy(strike, current_price)
    print(f"Legs: {len(legs)}")
    for leg in legs:
        print(f"  {leg.symbol}: {leg.qty:+.1f} @ ${leg.price:.2f}")
    print(f"Max Loss: ${payoff.max_loss:.2f}")
    print(f"Breakeven Points: {payoff.breakeven_points}")
    print(f"Current P&L: ${payoff.current_pnl:.2f}\n")

    # Test Butterfly
    print("=== Butterfly Strategy ===")
    lower_strike = strike - 2000
    middle_strike = strike
    upper_strike = strike + 2000
    legs, payoff = create_butterfly_strategy(
        lower_strike, middle_strike, upper_strike, current_price
    )
    print(f"Legs: {len(legs)}")
    for leg in legs:
        print(f"  {leg.symbol}: {leg.qty:+.1f} @ ${leg.price:.2f}")
    print(f"Max Profit: ${payoff.max_profit:.2f}")
    print(f"Max Loss: ${payoff.max_loss:.2f}")
    print(f"Breakeven Points: {payoff.breakeven_points}")
    print(f"Current P&L: ${payoff.current_pnl:.2f}\n")

    # Test Iron Condor
    print("=== Iron Condor Strategy ===")
    put_lower = strike - 3000
    put_upper = strike - 1000
    call_lower = strike + 1000
    call_upper = strike + 3000
    legs, payoff = create_iron_condor_strategy(
        put_lower, put_upper, call_lower, call_upper, current_price
    )
    print(f"Legs: {len(legs)}")
    for leg in legs:
        print(f"  {leg.symbol}: {leg.qty:+.1f} @ ${leg.price:.2f}")
    print(f"Max Profit: ${payoff.max_profit:.2f}")
    print(f"Max Loss: ${payoff.max_loss:.2f}")
    print(f"Breakeven Points: {payoff.breakeven_points}")
    print(f"Current P&L: ${payoff.current_pnl:.2f}\n")

    # Test Greeks calculation
    print("=== Greeks Calculation ===")
    greeks = OptionStrategies.calculate_strategy_greeks(legs)
    print(f"Delta: {greeks['delta']:.4f}")
    print(f"Gamma: {greeks['gamma']:.4f}")
    print(f"Theta: {greeks['theta']:.4f}")
    print(f"Vega: {greeks['vega']:.4f}\n")

    # Test strategy descriptions
    print("=== Strategy Descriptions ===")
    for strategy in ["straddle", "butterfly", "iron_condor"]:
        desc = OptionStrategies.get_strategy_description(strategy)
        print(f"{strategy.title()}: {desc}")


if __name__ == "__main__":
    asyncio.run(test_strategies())
