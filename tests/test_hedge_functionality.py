#!/usr/bin/env python3
"""Test hedge functionality."""

import asyncio
from src.portfolio.state import Portfolio
from src.services.hedge import hedge_service


async def test_hedge_functionality():
    """Test hedge calculations and recommendations."""
    print("🧪 Testing Hedge Functionality")
    print("=" * 50)

    # Initialize portfolio
    portfolio = Portfolio()

    # Test 1: Empty portfolio (delta-neutral)
    print("\n1. Testing empty portfolio...")
    total_delta = portfolio.get_total_delta()
    recommendations = hedge_service.calculate_hedge_recommendations(
        total_delta, portfolio.positions
    )
    print(f"   Delta: {total_delta:+.4f} BTC")
    print(f"   Recommendations: {len(recommendations)}")

    # Test 2: Long portfolio
    print("\n2. Testing long portfolio...")
    portfolio.update_fill("BTC-USDT-SPOT", 5.0, 107000.0, "spot", "OKX")
    total_delta = portfolio.get_total_delta()
    recommendations = hedge_service.calculate_hedge_recommendations(
        total_delta, portfolio.positions
    )
    print(f"   Delta: {total_delta:+.4f} BTC")
    print(f"   Recommendations: {len(recommendations)}")

    for i, rec in enumerate(recommendations, 1):
        print(
            f"   {i}. {rec.hedge_type}: {rec.quantity:.4f} {rec.direction} {rec.symbol}"
        )

    # Test 3: Short portfolio
    print("\n3. Testing short portfolio...")
    portfolio.update_fill("BTC-USDT-PERP", -3.0, 107000.0, "perpetual", "OKX")
    total_delta = portfolio.get_total_delta()
    recommendations = hedge_service.calculate_hedge_recommendations(
        total_delta, portfolio.positions
    )
    print(f"   Delta: {total_delta:+.4f} BTC")
    print(f"   Recommendations: {len(recommendations)}")

    for i, rec in enumerate(recommendations, 1):
        print(
            f"   {i}. {rec.hedge_type}: {rec.quantity:.4f} {rec.direction} {rec.symbol}"
        )

    # Test 4: Hedge metrics
    print("\n4. Testing hedge metrics...")
    metrics = hedge_service.calculate_hedge_metrics(
        total_delta, 2.0, "perp_delta_neutral"
    )
    print(f"   Current Delta: {metrics.current_delta:+.4f}")
    print(f"   Target Delta: {metrics.target_delta:+.4f}")
    print(f"   Risk Reduction: ${metrics.risk_reduction:.2f}")
    print(f"   Effectiveness: {metrics.hedge_effectiveness:.1%}")

    # Test 5: Hedge validation
    print("\n5. Testing hedge validation...")
    is_valid, error = hedge_service.validate_hedge(
        total_delta, 2.0, "perp_delta_neutral"
    )
    print(f"   Valid: {is_valid}")
    if not is_valid:
        print(f"   Error: {error}")

    print("\n✅ Hedge functionality test completed!")


if __name__ == "__main__":
    asyncio.run(test_hedge_functionality())
