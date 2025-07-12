import asyncio
from src.portfolio.state import Portfolio, Transaction
from datetime import datetime


async def test_transactions():
    """Test transaction recording and display."""
    print("🧪 Testing Transactions Functionality")
    print("=" * 50)

    # Create portfolio
    portfolio = Portfolio()

    # Add some test transactions
    portfolio.record_transaction(
        symbol="BTC-USDT-SPOT",
        qty=5.0,
        price=108000.0,
        instrument_type="spot",
        exchange="OKX",
        transaction_type="add",
        notes="Test position addition",
    )

    portfolio.record_transaction(
        symbol="BTC-USDT-PERP",
        qty=-2.0,
        price=107950.0,
        instrument_type="perpetual",
        exchange="OKX",
        transaction_type="hedge",
        notes="Test hedge execution",
    )

    portfolio.record_transaction(
        symbol="BTC-11JUL25-113000-P",
        qty=1.0,
        price=2500.0,
        instrument_type="option",
        exchange="Deribit",
        transaction_type="hedge",
        notes="Test protective put",
    )

    # Get transaction history
    transactions = portfolio.get_transaction_history()
    summary = portfolio.get_transaction_summary()

    print(f"📊 Transaction Summary:")
    print(f"• Total Transactions: {summary['total_transactions']}")
    print(f"• Total Volume: ${summary['total_volume']:,.2f}")
    print(f"• Total P&L: ${summary['total_pnl']:+,.2f}")

    print(f"\n📝 Recent Transactions:")
    for i, tx in enumerate(transactions[:5], 1):
        timestamp = tx.timestamp.strftime("%m/%d %H:%M")
        qty_str = f"{tx.qty:+.4f}" if abs(tx.qty) >= 0.0001 else f"{tx.qty:+.6f}"
        price_str = f"${tx.price:.2f}"

        type_emoji = {
            "buy": "🟢",
            "sell": "🔴",
            "add": "➕",
            "remove": "➖",
            "hedge": "🛡️",
        }.get(tx.transaction_type, "📊")

        pnl_str = ""
        if tx.pnl is not None:
            pnl_color = "🟢" if tx.pnl >= 0 else "🔴"
            pnl_str = f" | P&L: {pnl_color}${tx.pnl:+,.2f}"

        print(f"{i}. {type_emoji} {tx.symbol} {qty_str} @ {price_str}{pnl_str}")
        print(f"   {timestamp} | {tx.transaction_type.title()}")
        if tx.notes:
            print(f"   Note: {tx.notes}")
        print()

    print("✅ Transaction functionality test completed!")


if __name__ == "__main__":
    asyncio.run(test_transactions())
