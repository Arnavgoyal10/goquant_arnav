import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.analytics.stress_testing import stress_testing


async def test_stress_testing():
    """Test the stress testing functionality."""
    print("🧪 Testing Stress Testing Implementation")
    print("=" * 50)

    try:
        # Test 1: Get available scenarios
        print("\n1. Testing Available Scenarios...")
        scenarios = stress_testing.get_available_scenarios()
        print(f"Found {len(scenarios)} scenarios:")
        for scenario in scenarios:
            print(f"  • {scenario['name']}: {scenario['description']}")

        # Test 2: Run a stress test
        print("\n2. Testing Stress Test Execution...")
        portfolio_positions = {
            "BTC-USDT-SPOT": {"qty": 1.0, "avg_px": 50000.0, "instrument_type": "spot"},
            "ETH-USDT-PERP": {
                "qty": 10.0,
                "avg_px": 3000.0,
                "instrument_type": "perpetual",
            },
        }

        hedge_positions = [
            {"symbol": "BTC-45000-P-25JUL25", "qty": -1.0, "avg_px": 2000.0}
        ]

        results = await stress_testing.run_stress_test(
            portfolio_positions=portfolio_positions,
            hedge_positions=hedge_positions,
            scenario_name="market_crash_20",
        )

        if results:
            print("✅ Stress test completed successfully!")
            print("\nResults:")
            print(stress_testing.format_stress_test_results(results))
        else:
            print("❌ Stress test failed")

        # Test 3: Test all scenarios
        print("\n3. Testing All Scenarios...")
        for scenario in scenarios:
            print(f"\nRunning {scenario['name']}...")
            results = await stress_testing.run_stress_test(
                portfolio_positions=portfolio_positions,
                hedge_positions=hedge_positions,
                scenario_name=scenario["id"],
            )
            if results:
                print(f"✅ {scenario['name']} completed")
            else:
                print(f"❌ {scenario['name']} failed")

        print("\n🎉 All stress testing tests completed!")

    except Exception as e:
        print(f"❌ Error in stress testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_stress_testing())
