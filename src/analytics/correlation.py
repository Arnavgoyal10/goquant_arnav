import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from loguru import logger

from src.analytics.historical_data import HistoricalDataCollector


class CorrelationAnalyzer:
    """Analyzes correlations between portfolio positions and hedging instruments."""

    def __init__(self):
        self.data_collector = HistoricalDataCollector()
        self.correlation_cache: Dict[str, pd.DataFrame] = {}
        self.cache_duration = 3600  # 1 hour cache

    async def calculate_portfolio_correlation_matrix(
        self,
        portfolio_symbols: List[str],
        hedge_symbols: List[str] = None,
        days: int = 30,
    ) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """Calculate correlation matrix for portfolio symbols and report missing data.

        Returns:
            (correlation_matrix, missing_data_dict)
        """
        try:
            # Combine portfolio and hedge symbols
            all_symbols = portfolio_symbols.copy()
            if hedge_symbols:
                all_symbols.extend(hedge_symbols)

            # Get historical data for all symbols
            historical_data = await self.data_collector.get_portfolio_historical_data(
                all_symbols, days
            )

            # Calculate returns for each symbol
            returns_data = {}
            insufficient_data = {}
            for symbol in all_symbols:
                if symbol in historical_data and not historical_data[symbol].empty:
                    returns = self.data_collector.calculate_returns(
                        historical_data[symbol]
                    )
                    if not returns.empty and len(returns) >= 10:
                        returns_data[symbol] = returns
                    else:
                        insufficient_data[symbol] = len(returns)
                else:
                    insufficient_data[symbol] = 0

            if len(returns_data) < 2:
                logger.warning("Insufficient data for correlation analysis")
                return pd.DataFrame(), insufficient_data

            # Create returns DataFrame
            returns_df = pd.DataFrame(returns_data)

            # Calculate correlation matrix
            correlation_matrix = returns_df.corr()

            # Cache the result
            cache_key = f"{'_'.join(sorted(all_symbols))}_{days}"
            self.correlation_cache[cache_key] = correlation_matrix

            logger.info(f"Calculated correlation matrix for {len(all_symbols)} symbols")
            return correlation_matrix, insufficient_data

        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return pd.DataFrame(), {}

    async def calculate_portfolio_hedge_correlation(
        self, portfolio_symbols: List[str], hedge_symbols: List[str], days: int = 30
    ) -> Dict[str, float]:
        """Calculate correlations between portfolio positions and hedge instruments.

        Args:
            portfolio_symbols: List of portfolio symbols
            hedge_symbols: List of hedge symbols
            days: Number of days for analysis

        Returns:
            Dictionary mapping portfolio-hedge pairs to correlation values
        """
        try:
            # Get correlation matrix
            correlation_matrix = await self.calculate_portfolio_correlation_matrix(
                portfolio_symbols, hedge_symbols, days
            )

            if correlation_matrix.empty:
                return {}

            # Extract portfolio-hedge correlations
            correlations = {}
            for portfolio_symbol in portfolio_symbols:
                for hedge_symbol in hedge_symbols:
                    if (
                        portfolio_symbol in correlation_matrix.index
                        and hedge_symbol in correlation_matrix.columns
                    ):
                        corr_value = correlation_matrix.loc[
                            portfolio_symbol, hedge_symbol
                        ]
                        if not pd.isna(corr_value):
                            key = f"{portfolio_symbol}_vs_{hedge_symbol}"
                            correlations[key] = corr_value

            logger.info(f"Calculated {len(correlations)} portfolio-hedge correlations")
            return correlations

        except Exception as e:
            logger.error(f"Error calculating portfolio-hedge correlations: {e}")
            return {}

    def get_correlation_summary(
        self,
        correlation_matrix: pd.DataFrame,
        portfolio_symbols: List[str] = None,
        hedge_symbols: List[str] = None,
    ) -> Dict[str, any]:
        """Generate summary statistics from correlation matrix.

        Args:
            correlation_matrix: Correlation matrix DataFrame
            portfolio_symbols: List of portfolio symbols
            hedge_symbols: List of hedge symbols

        Returns:
            Dictionary with correlation summary statistics
        """
        if correlation_matrix.empty:
            return {}

        try:
            summary = {
                "total_correlations": len(correlation_matrix.values.flatten()),
                "mean_correlation": float(correlation_matrix.values.flatten().mean()),
                "std_correlation": float(correlation_matrix.values.flatten().std()),
                "min_correlation": float(correlation_matrix.values.flatten().min()),
                "max_correlation": float(correlation_matrix.values.flatten().max()),
            }

            # Portfolio-specific correlations
            if portfolio_symbols:
                portfolio_correlations = []
                for symbol in portfolio_symbols:
                    if symbol in correlation_matrix.index:
                        symbol_corrs = correlation_matrix.loc[symbol].drop(symbol)
                        portfolio_correlations.extend(symbol_corrs.values)

                if portfolio_correlations:
                    summary["portfolio_mean_correlation"] = float(
                        np.mean(portfolio_correlations)
                    )
                    summary["portfolio_std_correlation"] = float(
                        np.std(portfolio_correlations)
                    )

            # Hedge-specific correlations
            if hedge_symbols:
                hedge_correlations = []
                for symbol in hedge_symbols:
                    if symbol in correlation_matrix.columns:
                        symbol_corrs = correlation_matrix[symbol].drop(symbol)
                        hedge_correlations.extend(symbol_corrs.values)

                if hedge_correlations:
                    summary["hedge_mean_correlation"] = float(
                        np.mean(hedge_correlations)
                    )
                    summary["hedge_std_correlation"] = float(np.std(hedge_correlations))

            return summary

        except Exception as e:
            logger.error(f"Error generating correlation summary: {e}")
            return {}

    def format_correlation_matrix_for_telegram(
        self, correlation_matrix: pd.DataFrame, max_decimals: int = 3
    ) -> str:
        """Format correlation matrix for Telegram display.

        Args:
            correlation_matrix: Correlation matrix DataFrame
            max_decimals: Maximum decimal places to show

        Returns:
            Formatted string for Telegram
        """
        if correlation_matrix.empty:
            return "❌ No correlation data available"

        try:
            # Check if we have meaningful correlations (not just diagonal)
            meaningful_correlations = 0
            total_correlations = 0
            for i in range(len(correlation_matrix.index)):
                for j in range(len(correlation_matrix.columns)):
                    if i != j:  # Skip diagonal
                        total_correlations += 1
                        if not pd.isna(correlation_matrix.iloc[i, j]):
                            meaningful_correlations += 1

            # Round correlation values
            rounded_matrix = correlation_matrix.round(max_decimals)

            # Create formatted output
            lines = ["📊 *Correlation Matrix*"]
            lines.append("")

            # Add column headers
            header = "Symbol"
            for col in rounded_matrix.columns:
                header += f" | {col}"
            lines.append(header)
            lines.append("-" * len(header))

            # Add rows
            for idx, row in rounded_matrix.iterrows():
                row_line = f"{idx}"
                for col in rounded_matrix.columns:
                    value = row[col]
                    if pd.isna(value):
                        row_line += " | N/A"
                    else:
                        row_line += f" | {value:.{max_decimals}f}"
                lines.append(row_line)

            # Add summary statistics
            summary = self.get_correlation_summary(correlation_matrix)
            if summary:
                lines.append("")
                lines.append("*Summary Statistics:*")
                if meaningful_correlations == 0:
                    lines.append("⚠️ No meaningful correlations found")
                    lines.append("   (All symbols have diagonal-only correlations)")
                else:
                    lines.append(
                        f"Mean Correlation: {summary.get('mean_correlation', 0):.3f}"
                    )
                    lines.append(
                        f"Std Correlation: {summary.get('std_correlation', 0):.3f}"
                    )
                    lines.append(
                        f"Range: {summary.get('min_correlation', 0):.3f} to {summary.get('max_correlation', 0):.3f}"
                    )

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Error formatting correlation matrix: {e}")
            return "❌ Error formatting correlation data"

    def get_high_correlation_pairs(
        self, correlation_matrix: pd.DataFrame, threshold: float = 0.7
    ) -> List[Tuple[str, str, float]]:
        """Get pairs of symbols with high correlation.

        Args:
            correlation_matrix: Correlation matrix DataFrame
            threshold: Correlation threshold (default 0.7)

        Returns:
            List of tuples (symbol1, symbol2, correlation)
        """
        if correlation_matrix.empty:
            return []

        try:
            high_corr_pairs = []

            # Get upper triangle of correlation matrix (excluding diagonal)
            for i in range(len(correlation_matrix.index)):
                for j in range(i + 1, len(correlation_matrix.columns)):
                    symbol1 = correlation_matrix.index[i]
                    symbol2 = correlation_matrix.columns[j]
                    corr_value = correlation_matrix.iloc[i, j]

                    if not pd.isna(corr_value) and abs(corr_value) >= threshold:
                        high_corr_pairs.append((symbol1, symbol2, corr_value))

            # Sort by absolute correlation value
            high_corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

            return high_corr_pairs

        except Exception as e:
            logger.error(f"Error finding high correlation pairs: {e}")
            return []

    def get_correlation_insights(
        self, correlation_matrix: pd.DataFrame, portfolio_symbols: List[str] = None
    ) -> List[str]:
        """Generate insights from correlation analysis.

        Args:
            correlation_matrix: Correlation matrix DataFrame
            portfolio_symbols: List of portfolio symbols

        Returns:
            List of insight strings
        """
        insights = []

        if correlation_matrix.empty:
            return ["No correlation data available"]

        try:
            # Check if we have meaningful correlations (not just diagonal)
            meaningful_correlations = 0
            total_correlations = 0
            for i in range(len(correlation_matrix.index)):
                for j in range(len(correlation_matrix.columns)):
                    if i != j:  # Skip diagonal
                        total_correlations += 1
                        if not pd.isna(correlation_matrix.iloc[i, j]):
                            meaningful_correlations += 1

            if meaningful_correlations == 0:
                insights.append("⚠️ No meaningful correlations found")
                insights.append("   • Symbols may not have overlapping time periods")
                insights.append("   • Consider adding more historical data")
                insights.append("   • Check if symbols have sufficient price history")
                return insights

            # High correlation pairs
            high_corr_pairs = self.get_high_correlation_pairs(correlation_matrix, 0.8)
            if high_corr_pairs:
                insights.append(
                    f"🔗 Found {len(high_corr_pairs)} highly correlated pairs (|r| ≥ 0.8)"
                )
                for symbol1, symbol2, corr in high_corr_pairs[:3]:  # Show top 3
                    insights.append(f"  • {symbol1} ↔ {symbol2}: {corr:.3f}")

            # Portfolio diversification
            if portfolio_symbols:
                portfolio_correlations = []
                for symbol in portfolio_symbols:
                    if symbol in correlation_matrix.index:
                        symbol_corrs = correlation_matrix.loc[symbol].drop(symbol)
                        portfolio_correlations.extend(symbol_corrs.values)

                if portfolio_correlations:
                    avg_portfolio_corr = np.mean(portfolio_correlations)
                    if avg_portfolio_corr > 0.5:
                        insights.append(
                            "⚠️ Portfolio shows high internal correlation - consider diversification"
                        )
                    elif avg_portfolio_corr < 0.2:
                        insights.append("✅ Portfolio shows good diversification")

            # Hedge effectiveness
            summary = self.get_correlation_summary(correlation_matrix)
            if summary.get("mean_correlation", 0) < 0.3:
                insights.append("✅ Low correlation suggests good hedge effectiveness")
            elif summary.get("mean_correlation", 0) > 0.7:
                insights.append("⚠️ High correlation may reduce hedge effectiveness")

            if not insights:
                insights.append(
                    "📊 Correlation analysis complete - no significant insights"
                )

            return insights

        except Exception as e:
            logger.error(f"Error generating correlation insights: {e}")
            return ["❌ Error generating insights"]


# Global instance for easy access
correlation_analyzer = CorrelationAnalyzer()
