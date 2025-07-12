import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from loguru import logger

from src.analytics.historical_data import HistoricalDataCollector
from src.analytics.correlation import CorrelationAnalyzer


class StressTesting:
    """Implements stress testing scenarios for portfolio analysis."""

    def __init__(self):
        self.data_collector = HistoricalDataCollector()
        self.correlation_analyzer = CorrelationAnalyzer()

        # Predefined stress scenarios
        self.scenarios = {
            "market_crash_20": {
                "name": "Market Crash (-20%)",
                "description": "Simulates a 20% market decline across all assets",
                "price_shock": -0.20,
                "volatility_multiplier": 2.0,
                "correlation_shift": 0.3,
            },
            "market_crash_50": {
                "name": "Severe Market Crash (-50%)",
                "description": "Simulates a 50% market decline across all assets",
                "price_shock": -0.50,
                "volatility_multiplier": 3.0,
                "correlation_shift": 0.5,
            },
            "volatility_spike": {
                "name": "Volatility Spike",
                "description": "Simulates a sudden increase in market volatility",
                "price_shock": 0.0,
                "volatility_multiplier": 4.0,
                "correlation_shift": 0.2,
            },
            "flash_crash": {
                "name": "Flash Crash",
                "description": "Simulates a rapid 10% decline followed by recovery",
                "price_shock": -0.10,
                "volatility_multiplier": 5.0,
                "correlation_shift": 0.4,
            },
        }

    async def run_stress_test(
        self,
        portfolio_positions: Dict,
        hedge_positions: List[Dict] = None,
        scenario_name: str = "market_crash_20",
        days: int = 30,
    ) -> Dict:
        """Run a stress test scenario on the portfolio.

        Args:
            portfolio_positions: Dictionary of portfolio positions
            hedge_positions: List of hedge positions
            scenario_name: Name of the stress scenario to run
            days: Number of days for historical data

        Returns:
            Dictionary containing stress test results
        """
        try:
            if scenario_name not in self.scenarios:
                raise ValueError(f"Unknown scenario: {scenario_name}")

            scenario = self.scenarios[scenario_name]

            # Get current portfolio state
            current_prices = await self._get_current_prices(portfolio_positions)
            current_pnl = self._calculate_portfolio_pnl(
                portfolio_positions, current_prices
            )
            current_var = self._calculate_portfolio_var(
                portfolio_positions, current_prices
            )

            # Apply stress scenario
            stressed_prices = self._apply_stress_scenario(current_prices, scenario)

            # Calculate stressed metrics
            stressed_pnl = self._calculate_portfolio_pnl(
                portfolio_positions, stressed_prices
            )
            stressed_var = self._calculate_portfolio_var(
                portfolio_positions, stressed_prices
            )

            # Calculate hedge effectiveness under stress
            hedge_impact = self._calculate_hedge_impact(
                portfolio_positions, hedge_positions, current_prices, stressed_prices
            )

            # Calculate risk metrics changes
            risk_changes = self._calculate_risk_changes(
                current_pnl, stressed_pnl, current_var, stressed_var
            )

            return {
                "scenario": scenario,
                "current_metrics": {
                    "pnl": current_pnl,
                    "var": current_var,
                    "prices": current_prices,
                },
                "stressed_metrics": {
                    "pnl": stressed_pnl,
                    "var": stressed_var,
                    "prices": stressed_prices,
                },
                "hedge_impact": hedge_impact,
                "risk_changes": risk_changes,
                "timestamp": datetime.now(),
            }

        except Exception as e:
            logger.error(f"Error running stress test: {e}")
            return {}

    async def _get_current_prices(self, portfolio_positions: Dict) -> Dict[str, float]:
        """Get current prices for all portfolio positions."""
        prices = {}

        for symbol, position in portfolio_positions.items():
            try:
                # For demo purposes, use simulated prices
                if "BTC" in symbol:
                    base_price = 50000
                elif "ETH" in symbol:
                    base_price = 3000
                else:
                    base_price = 100

                # Add some randomness to simulate real prices
                price_variation = (hash(symbol) % 1000 - 500) / 10000
                prices[symbol] = base_price * (1 + price_variation)

            except Exception as e:
                logger.error(f"Error getting price for {symbol}: {e}")
                prices[symbol] = 0.0

        return prices

    def _calculate_portfolio_pnl(
        self, portfolio_positions: Dict, prices: Dict[str, float]
    ) -> float:
        """Calculate portfolio P&L."""
        total_pnl = 0.0

        for symbol, position in portfolio_positions.items():
            if symbol in prices:
                current_price = prices[symbol]
                position_value = position.get("qty", 0) * current_price
                avg_price = position.get("avg_px", 0)
                position_pnl = position.get("qty", 0) * (current_price - avg_price)
                total_pnl += position_pnl

        return total_pnl

    def _calculate_portfolio_var(
        self,
        portfolio_positions: Dict,
        prices: Dict[str, float],
        confidence: float = 0.95,
    ) -> float:
        """Calculate portfolio Value at Risk."""
        # Simplified VaR calculation
        portfolio_value = sum(
            abs(position.get("qty", 0) * prices.get(symbol, 0))
            for symbol, position in portfolio_positions.items()
        )

        # Assume 20% annual volatility for VaR calculation
        daily_volatility = 0.20 / np.sqrt(252)
        var_multiplier = 1.645  # 95% confidence level

        return portfolio_value * daily_volatility * var_multiplier

    def _apply_stress_scenario(
        self, current_prices: Dict[str, float], scenario: Dict
    ) -> Dict[str, float]:
        """Apply stress scenario to current prices."""
        stressed_prices = {}

        price_shock = scenario["price_shock"]
        volatility_multiplier = scenario["volatility_multiplier"]

        for symbol, price in current_prices.items():
            # Apply price shock
            shocked_price = price * (1 + price_shock)

            # Add volatility-based random component
            volatility_component = np.random.normal(0, 0.02 * volatility_multiplier)
            stressed_prices[symbol] = shocked_price * (1 + volatility_component)

        return stressed_prices

    def _calculate_hedge_impact(
        self,
        portfolio_positions: Dict,
        hedge_positions: List[Dict],
        current_prices: Dict[str, float],
        stressed_prices: Dict[str, float],
    ) -> Dict:
        """Calculate hedge effectiveness under stress."""
        if not hedge_positions:
            return {"hedge_effectiveness": 0.0, "hedge_pnl": 0.0}

        # Calculate portfolio P&L without hedges
        portfolio_pnl_current = self._calculate_portfolio_pnl(
            portfolio_positions, current_prices
        )
        portfolio_pnl_stressed = self._calculate_portfolio_pnl(
            portfolio_positions, stressed_prices
        )
        portfolio_pnl_change = portfolio_pnl_stressed - portfolio_pnl_current

        # Calculate hedge P&L
        hedge_pnl = 0.0
        for hedge in hedge_positions:
            symbol = hedge.get("symbol", "")
            if symbol in stressed_prices:
                hedge_qty = hedge.get("qty", 0)
                hedge_avg_price = hedge.get("avg_px", 0)
                current_price = stressed_prices[symbol]
                hedge_pnl += hedge_qty * (current_price - hedge_avg_price)

        # Calculate hedge effectiveness
        total_pnl_change = portfolio_pnl_change + hedge_pnl
        hedge_effectiveness = (
            (hedge_pnl / abs(portfolio_pnl_change) * 100)
            if portfolio_pnl_change != 0
            else 0.0
        )

        return {
            "hedge_effectiveness": hedge_effectiveness,
            "hedge_pnl": hedge_pnl,
            "portfolio_pnl_change": portfolio_pnl_change,
            "total_pnl_change": total_pnl_change,
        }

    def _calculate_risk_changes(
        self,
        current_pnl: float,
        stressed_pnl: float,
        current_var: float,
        stressed_var: float,
    ) -> Dict:
        """Calculate changes in risk metrics."""
        pnl_change = stressed_pnl - current_pnl
        pnl_change_pct = (
            (pnl_change / abs(current_pnl) * 100) if current_pnl != 0 else 0.0
        )

        var_change = stressed_var - current_var
        var_change_pct = (var_change / current_var * 100) if current_var != 0 else 0.0

        return {
            "pnl_change": pnl_change,
            "pnl_change_pct": pnl_change_pct,
            "var_change": var_change,
            "var_change_pct": var_change_pct,
        }

    def format_stress_test_results(self, results: Dict) -> str:
        """Format stress test results for Telegram display."""
        if not results:
            return "❌ No stress test results available"

        try:
            scenario = results["scenario"]
            current = results["current_metrics"]
            stressed = results["stressed_metrics"]
            hedge_impact = results["hedge_impact"]
            risk_changes = results["risk_changes"]

            lines = [
                f"🧪 *Stress Test Results*",
                f"",
                f"*Scenario:* {scenario['name']}",
                f"*Description:* {scenario['description']}",
                f"",
                f"*Current Metrics:*",
                f"• Portfolio P&L: `${current['pnl']:,.2f}`",
                f"• 95% VaR: `${current['var']:,.2f}`",
                f"",
                f"*Stressed Metrics:*",
                f"• Portfolio P&L: `${stressed['pnl']:,.2f}`",
                f"• 95% VaR: `${stressed['var']:,.2f}`",
                f"",
                f"*Risk Changes:*",
                f"• P&L Change: `${risk_changes['pnl_change']:,.2f}` ({risk_changes['pnl_change_pct']:+.1f}%)",
                f"• VaR Change: `${risk_changes['var_change']:,.2f}` ({risk_changes['var_change_pct']:+.1f}%)",
                f"",
                f"*Hedge Impact:*",
                f"• Hedge P&L: `${hedge_impact['hedge_pnl']:,.2f}`",
                f"• Hedge Effectiveness: `{hedge_impact['hedge_effectiveness']:.1f}%`",
                f"• Total P&L Change: `${hedge_impact['total_pnl_change']:,.2f}`",
            ]

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Error formatting stress test results: {e}")
            return "❌ Error formatting stress test results"

    def get_available_scenarios(self) -> List[Dict]:
        """Get list of available stress test scenarios."""
        return [
            {
                "id": scenario_id,
                "name": scenario["name"],
                "description": scenario["description"],
            }
            for scenario_id, scenario in self.scenarios.items()
        ]


# Global instance for easy access
stress_testing = StressTesting()
