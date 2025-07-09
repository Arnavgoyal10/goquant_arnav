#!/usr/bin/env python3
"""Test portfolio CRUD operations."""

import asyncio
from src.portfolio.state import Portfolio
from src.services.costing import costing_service


async def test_portfolio_crud():
    """Test portfolio CRUD operations."""
    print("🧪 Testing Portfolio CRUD Operations")
    print("=" * 50)

    # Initialize portfolio
    portfolio = Portfolio()

    # Test 1: Add spot position
    print("\n1. Adding spot position...")
    portfolio.update_fill("BTC-USDT-SPOT", 5.0, 108000.0, "spot", "OKX")

    # Test 2: Add future position
    print("2. Adding future position...")
    portfolio.update_fill("BTC-USDT-PERP", -3.0, 107950.0, "perpetual", "OKX")

    # Test 3: Show portfolio
    print("3. Current portfolio:")
    snapshot = portfolio.snapshot()
    total_delta = portfolio.get_total_delta()
    print(f"   Total Delta: {total_delta:+.4f} BTC")
    print(f"   Total Notional: ${snapshot['total_notional']:,.2f}")
    print(f"   Total Positions: {snapshot['total_positions']}")

    # Test 4: Cost calculation
    print("\n4. Cost calculation example:")
    costs = costing_service.calculate_total_cost(2.0, 108000.0, "OKX", "spot")
    print(f"   Notional: ${costs['notional']:,.2f}")
    print(f"   Fee: ${costs['fee']:.2f}")
    print(f"   Slippage: ${costs['slippage']:.2f}")
    print(f"   Total Cost: ${costs['total_cost']:.2f}")

    # Test 5: Remove position
    print("\n5. Removing spot position...")
    portfolio.update_fill("BTC-USDT-SPOT", -5.0, 108500.0, "spot", "OKX")

    # Test 6: Show final portfolio
    print("6. Final portfolio:")
    snapshot = portfolio.snapshot()
    total_delta = portfolio.get_total_delta()
    print(f"   Total Delta: {total_delta:+.4f} BTC")
    print(f"   Total Notional: ${snapshot['total_notional']:,.2f}")
    print(f"   Total Positions: {snapshot['total_positions']}")

    print("\n✅ Portfolio CRUD operations test completed!")


if __name__ == "__main__":
    asyncio.run(test_portfolio_crud())
