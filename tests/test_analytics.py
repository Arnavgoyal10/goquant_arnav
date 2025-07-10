#!/usr/bin/env python3
"""Test script to verify analytics calculations."""

import asyncio
from src.portfolio.state import Portfolio, Position
from datetime import datetime


async def test_analytics():
    """Test analytics calculations."""
    print("🧪 Testing Analytics Calculations")
    print("=" * 50)

    # Create portfolio with realistic positions
    portfolio = Portfolio()

    # Add a spot position (like the user has)
    spot_position = Position(
        symbol="BTC-USDT-SPOT",
        qty=32.0,
        avg_px=111372.10,
        instrument_type="spot",
        exchange="OKX",
        timestamp=datetime.now(),
    )
    portfolio.add_position(spot_position)

    # Add an option position
    option_position = Position(
        symbol="BTC-25JUL25-109000-P",
        qty=26.6667,
        avg_px=0.02,
        instrument_type="option",
        exchange="Deribit",
        timestamp=datetime.now(),
    )
    portfolio.add_position(option_position)

    # Test analytics calculations
    pnl_realized = portfolio.get_realized_pnl()
    pnl_unrealized = portfolio.get_unrealized_pnl()
    delta = portfolio.get_total_delta()
    var_95 = portfolio.get_var_95()
    drawdown = portfolio.get_max_drawdown()
    greeks = portfolio.get_greeks_summary()

    print(f"📊 Analytics Results:")
    print(f"• Realized P&L: ${pnl_realized:,.2f}")
    print(f"• Unrealized P&L: ${pnl_unrealized:,.2f}")
    print(f"• Current Delta: {delta:+.4f} BTC")
    print(f"• 95% VaR: ${var_95:,.2f}")
    print(f"• Max Drawdown: {drawdown:.2%}")

    print(f"\n📈 Greeks Summary:")
    for greek, value in greeks.items():
        print(f"• {greek.capitalize()}: {value:+.4f}")

    print(f"\n📋 Portfolio Summary:")
    snapshot = portfolio.snapshot()
    print(f"• Total Positions: {snapshot['total_positions']}")
    print(f"• Total Notional: ${snapshot['total_notional']:,.2f}")

    print("✅ Analytics test completed!")


if __name__ == "__main__":
    asyncio.run(test_analytics())
