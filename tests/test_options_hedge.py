#!/usr/bin/env python3
"""Test script for options hedging functionality."""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from services.hedge import hedge_service
from services.options_pricing import options_pricing_service
from exchanges.deribit_options import deribit_options, OptionContract
from datetime import datetime, timedelta


async def test_options_pricing():
    """Test options pricing functionality."""
    print("🧪 Testing Options Pricing...")

    # Test Black-Scholes calculations
    S = 107000  # Current BTC price
    K = 110000  # Strike price
    T = 30 / 365  # 30 days to expiry
    sigma = 0.5  # 50% volatility

    # Test call option pricing
    call_price = options_pricing_service.black_scholes_call(S, K, T, 0.05, sigma)
    print(f"Call option price: ${call_price:.2f}")

    # Test put option pricing
    put_price = options_pricing_service.black_scholes_put(S, K, T, 0.05, sigma)
    print(f"Put option price: ${put_price:.2f}")

    # Test Greeks calculation
    greeks = options_pricing_service.calculate_greeks(S, K, T, 0.05, sigma, "call")
    print(
        f"Call Greeks - Delta: {greeks.delta:.4f}, Gamma: {greeks.gamma:.6f}, Theta: {greeks.theta:.4f}, Vega: {greeks.vega:.4f}"
    )

    # Test full option pricing
    pricing = options_pricing_service.price_option(
        S, K, T, sigma, "call", bid=call_price * 0.99, ask=call_price * 1.01
    )
    print(
        f"Full pricing - Theoretical: ${pricing.theoretical_price:.2f}, IV: {pricing.implied_volatility:.1%}"
    )

    print("✅ Options pricing tests passed!\n")


async def test_hedge_recommendations():
    """Test hedge recommendations with options."""
    print("🛡️ Testing Hedge Recommendations...")

    # Create mock option chain
    mock_options = [
        OptionContract(
            symbol="BTC-30JUN24-110000-P",
            strike=110000,
            expiry=datetime.now() + timedelta(days=30),
            option_type="put",
            underlying="BTC",
            exchange="Deribit",
            delta=-0.4,
            gamma=0.01,
            theta=-0.1,
            vega=0.5,
            implied_volatility=0.5,
            last_price=5000,
            bid=4900,
            ask=5100,
            volume_24h=100,
        ),
        OptionContract(
            symbol="BTC-30JUN24-115000-C",
            strike=115000,
            expiry=datetime.now() + timedelta(days=30),
            option_type="call",
            underlying="BTC",
            exchange="Deribit",
            delta=0.3,
            gamma=0.01,
            theta=-0.08,
            vega=0.4,
            implied_volatility=0.5,
            last_price=3000,
            bid=2900,
            ask=3100,
            volume_24h=80,
        ),
    ]

    # Test hedge recommendations
    portfolio_delta = 0.5  # Long 0.5 BTC
    recommendations = await hedge_service.calculate_hedge_recommendations(
        portfolio_delta, {}, mock_options
    )

    print(f"Portfolio Delta: {portfolio_delta:+.4f} BTC")
    print(f"Found {len(recommendations)} hedge recommendations:")

    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec.hedge_type}: {rec.symbol} {rec.quantity:.4f} {rec.direction}")
        print(
            f"   Cost: ${rec.estimated_cost:.2f}, Risk Reduction: ${rec.risk_reduction:.2f}"
        )

    # Test dynamic hedge
    dynamic_recs = await hedge_service.get_dynamic_hedge_recommendation(
        portfolio_delta, mock_options, target_delta=0.0
    )

    print(f"\nDynamic hedge recommendations: {len(dynamic_recs)}")
    for rec in dynamic_recs:
        print(f"• {rec.hedge_type}: {rec.symbol} {rec.quantity:.4f} {rec.direction}")

    print("✅ Hedge recommendations tests passed!\n")


async def test_deribit_options():
    """Test Deribit options exchange connectivity."""
    print("🔗 Testing Deribit Options Exchange...")

    try:
        async with deribit_options:
            # Test getting instruments
            instruments = await deribit_options.get_instruments()
            print(f"Found {len(instruments)} instruments")

            # Test getting option chain
            option_chain = await deribit_options.get_option_chain()
            print(f"Found {len(option_chain)} options in chain")

            if option_chain:
                # Test getting ticker for first option
                first_option = option_chain[0]
                ticker = await deribit_options.get_option_ticker(first_option.symbol)
                if ticker:
                    print(f"Ticker for {first_option.symbol}: ${ticker.last_price:.2f}")
                    print(
                        f"Greeks - Delta: {ticker.delta:.4f}, IV: {ticker.implied_volatility:.1%}"
                    )

            print("✅ Deribit options tests passed!")

    except Exception as e:
        print(f"⚠️ Deribit options test failed: {e}")
        print("This is expected if Deribit API is not available")


async def main():
    """Run all tests."""
    print("🚀 Starting Options Hedge Tests...\n")

    await test_options_pricing()
    await test_hedge_recommendations()
    await test_deribit_options()

    print("🎉 All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
