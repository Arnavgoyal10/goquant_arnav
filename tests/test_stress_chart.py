import sys
import os

sys.path.append(".")

import asyncio
from src.analytics.stress_testing import stress_testing
from src.analytics.charts import chart_generator


async def test_stress_chart():
    """Test stress test chart generation."""
    try:
        # Test data
        portfolio_positions = {
            "BTC-SPOT": {"qty": 1.0, "avg_px": 50000.0, "instrument_type": "spot"}
        }

        # Run stress test
        print("Running stress test...")
        result = await stress_testing.run_stress_test(
            portfolio_positions=portfolio_positions,
            hedge_positions=[],
            scenario_name="market_crash_20",
        )

        print(f"Result type: {type(result)}")
        print(
            f"Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}"
        )

        if (
            isinstance(result, dict)
            and "scenario" in result
            and "risk_changes" in result
        ):
            scenario_name = result["scenario"]["name"]
            pnl_change = result["risk_changes"]["pnl_change"]

            print(f"Scenario: {scenario_name}")
            print(f"P&L Change: {pnl_change}")

            # Generate chart
            print("Generating chart...")
            chart_path = await chart_generator.generate_stress_test_chart(
                stress_results={scenario_name: pnl_change}
            )

            print(f"Chart path: {chart_path}")

            if chart_path and os.path.exists(chart_path):
                print("✅ Chart generated successfully!")
                print(f"File size: {os.path.getsize(chart_path)} bytes")
            else:
                print("❌ Chart generation failed!")
        else:
            print("❌ Invalid result structure")
            print(f"Result: {result}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_stress_chart())
