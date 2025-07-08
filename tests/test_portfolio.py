"""Unit tests for portfolio management."""

import pytest
from datetime import datetime

from src.portfolio.state import Portfolio, Position, create_test_portfolio


def test_position_notional():
    """Test that position notional is computed correctly."""
    # Long position
    long_pos = Position(
        symbol="BTC-USDT-SPOT",
        qty=5.0,
        avg_px=108000.0,
        instrument_type="spot",
        exchange="OKX",
        timestamp=datetime.now(),
    )
    assert long_pos.notional == 540000.0  # 5 * 108000

    # Short position
    short_pos = Position(
        symbol="BTC-USDT-PERP",
        qty=-3.0,
        avg_px=107000.0,
        instrument_type="perpetual",
        exchange="Deribit",
        timestamp=datetime.now(),
    )
    assert short_pos.notional == 321000.0  # abs(-3 * 107000)


def test_portfolio_snapshot():
    """Test portfolio snapshot functionality."""
    portfolio = create_test_portfolio()
    snapshot = portfolio.snapshot()

    assert snapshot["total_positions"] == 1
    assert snapshot["total_notional"] == 540000.0  # 5 BTC * 108000
    assert len(snapshot["all_positions"]) == 1
    assert snapshot["all_positions"][0]["symbol"] == "BTC-USDT-SPOT"


def test_portfolio_delta_calculation():
    """Test that portfolio delta is computed correctly."""
    portfolio = create_test_portfolio()

    # Test portfolio should have +5 BTC delta
    assert portfolio.get_total_delta() == 5.0

    # Add a short perpetual position
    portfolio.update_fill("BTC-USDT-PERP", -2.0, 107000.0, "perpetual", "OKX")

    # Now delta should be +3 BTC (5 spot - 2 perp)
    assert portfolio.get_total_delta() == 3.0


def test_position_update_fill():
    """Test position updates with fills."""
    portfolio = Portfolio()

    # Add initial position
    portfolio.update_fill("BTC-USDT-SPOT", 5.0, 108000.0, "spot", "OKX")
    assert portfolio.get_total_delta() == 5.0

    # Add more to the same position
    portfolio.update_fill("BTC-USDT-SPOT", 3.0, 109000.0, "spot", "OKX")
    position = portfolio.get_position("BTC-USDT-SPOT")
    assert position is not None
    assert position.qty == 8.0
    # Average price should be weighted average
    expected_avg = (5 * 108000 + 3 * 109000) / 8
    assert abs(position.avg_px - expected_avg) < 0.01

    # Close the position
    portfolio.update_fill("BTC-USDT-SPOT", -8.0, 110000.0, "spot", "OKX")
    assert portfolio.get_position("BTC-USDT-SPOT") is None
    assert portfolio.get_total_delta() == 0.0


def test_portfolio_summary():
    """Test portfolio summary formatting."""
    portfolio = create_test_portfolio()
    summary = portfolio.get_positions_summary()

    assert "Portfolio Positions:" in summary
    assert "BTC-USDT-SPOT" in summary
    assert "LONG" in summary
    assert "Total Delta: +5.0000 BTC" in summary


if __name__ == "__main__":
    pytest.main([__file__])
