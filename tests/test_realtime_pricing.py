#!/usr/bin/env python3
"""Test real-time pricing functionality."""

import asyncio
from src.exchanges.okx import OKXExchange
from src.exchanges.deribit import DeribitExchange


async def test_realtime_pricing():
    """Test real-time pricing from exchanges."""
    print("🧪 Testing Real-time Pricing")
    print("=" * 50)

    # Test OKX pricing
    print("\n1. Testing OKX pricing...")
    async with OKXExchange() as okx:
        # Test spot pricing
        spot_ticker = await okx.get_ticker("BTC-USDT-SPOT")
        if spot_ticker:
            print(f"   BTC-USDT-SPOT: ${spot_ticker.last_price:.2f}")
        else:
            print("   ❌ Failed to get spot price")

        # Test perpetual pricing
        perp_ticker = await okx.get_ticker("BTC-USDT-PERP")
        if perp_ticker:
            print(f"   BTC-USDT-PERP: ${perp_ticker.last_price:.2f}")
        else:
            print("   ❌ Failed to get perpetual price")

    # Test Deribit pricing
    print("\n2. Testing Deribit pricing...")
    async with DeribitExchange() as deribit:
        perp_ticker = await deribit.get_ticker("BTC-PERP")
        if perp_ticker:
            print(f"   BTC-PERP: ${perp_ticker.last_price:.2f}")
        else:
            print("   ❌ Failed to get Deribit perpetual price")

    print("\n✅ Real-time pricing test completed!")


if __name__ == "__main__":
    asyncio.run(test_realtime_pricing())
