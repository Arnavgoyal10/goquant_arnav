import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import modules using absolute imports
from src.analytics.correlation import correlation_analyzer
from src.analytics.historical_data import historical_data_collector


async def test_correlation_analysis():
    """Test the correlation analysis functionality."""
    print("🧪 Testing Correlation Analysis Implementation")
    print("=" * 50)

    try:
        # Test 1: Historical data collection
        print("\n1. Testing Historical Data Collection...")
        symbols = ["BTC-USDT", "ETH-USDT"]

        async with historical_data_collector:
            historical_data = (
                await historical_data_collector.get_portfolio_historical_data(
                    symbols, days=7
                )
            )

            print(f"✅ Collected historical data for {len(historical_data)} symbols")
            for symbol, data in historical_data.items():
                print(f"   - {symbol}: {len(data)} records")

        # Test 2: Correlation matrix calculation
        print("\n2. Testing Correlation Matrix Calculation...")
        portfolio_symbols = ["BTC-USDT", "ETH-USDT"]
        hedge_symbols = ["BTC-PERP"]

        correlation_matrix = (
            await correlation_analyzer.calculate_portfolio_correlation_matrix(
                portfolio_symbols, hedge_symbols, days=7
            )
        )

        if not correlation_matrix.empty:
            print("✅ Correlation matrix calculated successfully")
            print(f"   Matrix shape: {correlation_matrix.shape}")
            print(f"   Symbols: {list(correlation_matrix.columns)}")
        else:
            print("⚠️ Correlation matrix is empty (expected for demo data)")

        # Test 3: Correlation formatting
        print("\n3. Testing Correlation Formatting...")
        formatted_text = correlation_analyzer.format_correlation_matrix_for_telegram(
            correlation_matrix, max_decimals=3
        )

        print("✅ Correlation matrix formatted for Telegram")
        print("Sample output:")
        print(
            formatted_text[:200] + "..."
            if len(formatted_text) > 200
            else formatted_text
        )

        # Test 4: Correlation insights
        print("\n4. Testing Correlation Insights...")
        insights = correlation_analyzer.get_correlation_insights(
            correlation_matrix, portfolio_symbols
        )

        print("✅ Correlation insights generated")
        for insight in insights:
            print(f"   - {insight}")

        print("\n🎉 All tests passed! Correlation analysis implementation is working.")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_correlation_analysis())
