"""Chart generation for analytics and visualizations."""

import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend for server environments
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import pandas as pd
import numpy as np
import tempfile
import os
from typing import Optional, Dict, List
from loguru import logger

# Set style for better-looking charts
plt.style.use("default")
sns.set_palette("husl")


class ChartGenerator:
    """Generates charts and visualizations for analytics."""

    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.chart_counter = 0

    async def generate_correlation_heatmap(
        self, correlation_matrix: pd.DataFrame, figsize: tuple = (10, 8)
    ) -> Optional[str]:
        """Generate a correlation heatmap chart.

        Args:
            correlation_matrix: Correlation matrix DataFrame
            figsize: Figure size (width, height)

        Returns:
            Path to the generated chart image, or None if failed
        """
        try:
            if correlation_matrix.empty:
                logger.warning("Empty correlation matrix provided")
                return None

            # Create figure and axis
            fig, ax = plt.subplots(figsize=figsize)

            # Generate heatmap using seaborn
            mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
            sns.heatmap(
                correlation_matrix,
                mask=mask,
                annot=True,
                fmt=".3f",
                cmap="RdBu_r",
                center=0,
                square=True,
                linewidths=0.5,
                cbar_kws={"shrink": 0.8},
                ax=ax,
            )

            # Customize the plot
            ax.set_title(
                "Portfolio Correlation Matrix", fontsize=16, fontweight="bold", pad=20
            )
            ax.set_xlabel("Symbols", fontsize=12)
            ax.set_ylabel("Symbols", fontsize=12)

            # Rotate x-axis labels for better readability
            plt.xticks(rotation=45, ha="right")
            plt.yticks(rotation=0)

            # Adjust layout
            plt.tight_layout()

            # Save to temporary file
            chart_path = self._save_chart(fig, "correlation_heatmap")

            return chart_path

        except Exception as e:
            logger.error(f"Error generating correlation heatmap: {e}")
            return None

    async def generate_pnl_chart(
        self,
        pnl_data: Dict[str, List[float]],
        timestamps: List[str],
        figsize: tuple = (12, 6),
    ) -> Optional[str]:
        """Generate a P&L line chart.

        Args:
            pnl_data: Dictionary mapping symbols to P&L values
            timestamps: List of timestamp strings
            figsize: Figure size (width, height)

        Returns:
            Path to the generated chart image, or None if failed
        """
        try:
            if not pnl_data:
                logger.warning("No P&L data provided")
                return None

            # Create figure and axis
            fig, ax = plt.subplots(figsize=figsize)

            # Plot P&L for each symbol
            for symbol, pnl_values in pnl_data.items():
                ax.plot(
                    timestamps,
                    pnl_values,
                    label=symbol,
                    linewidth=2,
                    marker="o",
                    markersize=4,
                )

            # Customize the plot
            ax.set_title(
                "Portfolio P&L Over Time", fontsize=16, fontweight="bold", pad=20
            )
            ax.set_xlabel("Time", fontsize=12)
            ax.set_ylabel("P&L ($)", fontsize=12)
            ax.legend()
            ax.grid(True, alpha=0.3)

            # Rotate x-axis labels for better readability
            plt.xticks(rotation=45, ha="right")

            # Adjust layout
            plt.tight_layout()

            # Save to temporary file
            chart_path = self._save_chart(fig, "pnl_chart")

            return chart_path

        except Exception as e:
            logger.error(f"Error generating P&L chart: {e}")
            return None

    async def generate_stress_test_chart(
        self, stress_results: Dict[str, float], figsize: tuple = (10, 6)
    ) -> Optional[str]:
        """Generate a stress test results bar chart.

        Args:
            stress_results: Dictionary mapping scenarios to P&L impact
            figsize: Figure size (width, height)

        Returns:
            Path to the generated chart image, or None if failed
        """
        try:
            if not stress_results:
                logger.warning("No stress test results provided")
                return None

            # Create figure and axis
            fig, ax = plt.subplots(figsize=figsize)

            # Prepare data for plotting
            scenarios = list(stress_results.keys())
            impacts = list(stress_results.values())

            # Create bar chart
            bars = ax.bar(
                scenarios, impacts, color=["red" if x < 0 else "green" for x in impacts]
            )

            # Customize the plot
            ax.set_title("Stress Test Results", fontsize=16, fontweight="bold", pad=20)
            ax.set_xlabel("Stress Scenarios", fontsize=12)
            ax.set_ylabel("P&L Impact ($)", fontsize=12)

            # Add value labels on bars
            for bar, impact in zip(bars, impacts):
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"${impact:,.0f}",
                    ha="center",
                    va="bottom" if height >= 0 else "top",
                )

            # Rotate x-axis labels for better readability
            plt.xticks(rotation=45, ha="right")

            # Add horizontal line at zero
            ax.axhline(y=0, color="black", linestyle="-", alpha=0.3)

            # Adjust layout
            plt.tight_layout()

            # Save to temporary file
            chart_path = self._save_chart(fig, "stress_test_chart")

            return chart_path

        except Exception as e:
            logger.error(f"Error generating stress test chart: {e}")
            return None

    async def generate_risk_metrics_chart(
        self, risk_metrics: Dict[str, float], figsize: tuple = (10, 6)
    ) -> Optional[str]:
        """Generate a risk metrics radar chart.

        Args:
            risk_metrics: Dictionary mapping risk metrics to values
            figsize: Figure size (width, height)

        Returns:
            Path to the generated chart image, or None if failed
        """
        try:
            if not risk_metrics:
                logger.warning("No risk metrics provided")
                return None

            # Create figure and axis
            fig, ax = plt.subplots(figsize=figsize, subplot_kw=dict(projection="polar"))

            # Prepare data for radar chart
            categories = list(risk_metrics.keys())
            values = list(risk_metrics.values())

            # Number of variables
            N = len(categories)

            # Compute angle for each axis
            angles = [n / float(N) * 2 * np.pi for n in range(N)]
            angles += angles[:1]  # Complete the circle

            # Add the first value at the end to close the plot
            values += values[:1]

            # Draw the plot
            ax.plot(angles, values, "o-", linewidth=2, label="Current Risk")
            ax.fill(angles, values, alpha=0.25)

            # Fix axis to go in the right order and start at 12 o'clock
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)

            # Draw axis lines for each angle and label
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories)

            # Add legend
            ax.legend(loc="upper right", bbox_to_anchor=(0.1, 0.1))

            # Add title
            plt.title("Risk Metrics Overview", fontsize=16, fontweight="bold", pad=20)

            # Adjust layout
            plt.tight_layout()

            # Save to temporary file
            chart_path = self._save_chart(fig, "risk_metrics_chart")

            return chart_path

        except Exception as e:
            logger.error(f"Error generating risk metrics chart: {e}")
            return None

    async def generate_stress_test_comparison_chart(
        self, stress_results: List[Dict], figsize: tuple = (12, 8)
    ) -> Optional[str]:
        """Generate a comprehensive stress test comparison chart.

        Args:
            stress_results: List of stress test result dictionaries
            figsize: Figure size (width, height)

        Returns:
            Path to the generated chart image, or None if failed
        """
        try:
            if not stress_results:
                logger.warning("No stress test results provided")
                return None

            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)

            # Extract data
            scenarios = []
            pnl_changes = []
            var_changes = []
            hedge_effectiveness = []

            for result in stress_results:
                scenario_name = result["scenario"]["name"]
                pnl_change = result["risk_changes"]["pnl_change"]
                var_change = result["risk_changes"]["var_change"]
                hedge_eff = result["hedge_impact"]["hedge_effectiveness"]

                scenarios.append(scenario_name)
                pnl_changes.append(pnl_change)
                var_changes.append(var_change)
                hedge_effectiveness.append(hedge_eff)

            # Plot 1: P&L Impact
            colors = ["red" if x < 0 else "green" for x in pnl_changes]
            bars1 = ax1.bar(scenarios, pnl_changes, color=colors, alpha=0.7)
            ax1.set_title(
                "P&L Impact by Stress Scenario", fontsize=14, fontweight="bold"
            )
            ax1.set_ylabel("P&L Change ($)", fontsize=12)
            ax1.axhline(y=0, color="black", linestyle="-", alpha=0.3)

            # Add value labels
            for bar, value in zip(bars1, pnl_changes):
                height = bar.get_height()
                ax1.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"${value:,.0f}",
                    ha="center",
                    va="bottom" if height >= 0 else "top",
                    fontsize=10,
                )

            # Plot 2: VaR and Hedge Effectiveness
            x = np.arange(len(scenarios))
            width = 0.35

            bars2 = ax2.bar(
                x - width / 2, var_changes, width, label="VaR Change", alpha=0.7
            )
            bars3 = ax2.bar(
                x + width / 2,
                hedge_effectiveness,
                width,
                label="Hedge Effectiveness (%)",
                alpha=0.7,
            )

            ax2.set_title(
                "Risk Metrics by Stress Scenario", fontsize=14, fontweight="bold"
            )
            ax2.set_ylabel("Value", fontsize=12)
            ax2.set_xticks(x)
            ax2.set_xticklabels(scenarios, rotation=45, ha="right")
            ax2.legend()

            # Add value labels
            for bar, value in zip(bars2, var_changes):
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"${value:,.0f}",
                    ha="center",
                    va="bottom" if height >= 0 else "top",
                    fontsize=8,
                )

            for bar, value in zip(bars3, hedge_effectiveness):
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{value:.1f}%",
                    ha="center",
                    va="bottom" if height >= 0 else "top",
                    fontsize=8,
                )

            plt.tight_layout()
            chart_path = self._save_chart(fig, "stress_test_comparison")
            return chart_path

        except Exception as e:
            logger.error(f"Error generating stress test comparison chart: {e}")
            return None

    async def generate_portfolio_performance_chart(
        self,
        portfolio_data: Dict[str, List[float]],
        timestamps: List[str],
        figsize: tuple = (12, 8),
    ) -> Optional[str]:
        """Generate a comprehensive portfolio performance chart.

        Args:
            portfolio_data: Dictionary with performance metrics over time
            timestamps: List of timestamp strings
            figsize: Figure size (width, height)

        Returns:
            Path to the generated chart image, or None if failed
        """
        try:
            if not portfolio_data:
                logger.warning("No portfolio data provided")
                return None

            # Create figure with subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=figsize)

            # Plot 1: Portfolio Value
            if "portfolio_value" in portfolio_data:
                ax1.plot(
                    timestamps,
                    portfolio_data["portfolio_value"],
                    linewidth=2,
                    color="blue",
                    marker="o",
                    markersize=4,
                )
                ax1.set_title("Portfolio Value", fontsize=12, fontweight="bold")
                ax1.set_ylabel("Value ($)", fontsize=10)
                ax1.grid(True, alpha=0.3)

            # Plot 2: P&L
            if "pnl" in portfolio_data:
                colors = ["green" if x >= 0 else "red" for x in portfolio_data["pnl"]]
                ax2.bar(
                    range(len(timestamps)),
                    portfolio_data["pnl"],
                    color=colors,
                    alpha=0.7,
                )
                ax2.set_title("P&L", fontsize=12, fontweight="bold")
                ax2.set_ylabel("P&L ($)", fontsize=10)
                ax2.axhline(y=0, color="black", linestyle="-", alpha=0.3)

            # Plot 3: VaR
            if "var" in portfolio_data:
                ax3.plot(
                    timestamps,
                    portfolio_data["var"],
                    linewidth=2,
                    color="orange",
                    marker="s",
                    markersize=4,
                )
                ax3.set_title("Value at Risk (95%)", fontsize=12, fontweight="bold")
                ax3.set_ylabel("VaR ($)", fontsize=10)
                ax3.grid(True, alpha=0.3)

            # Plot 4: Drawdown
            if "drawdown" in portfolio_data:
                ax4.fill_between(
                    timestamps, portfolio_data["drawdown"], 0, color="red", alpha=0.3
                )
                ax4.plot(
                    timestamps, portfolio_data["drawdown"], linewidth=2, color="red"
                )
                ax4.set_title("Drawdown", fontsize=12, fontweight="bold")
                ax4.set_ylabel("Drawdown (%)", fontsize=10)
                ax4.grid(True, alpha=0.3)

            # Rotate x-axis labels
            for ax in [ax1, ax2, ax3, ax4]:
                ax.tick_params(axis="x", rotation=45)

            plt.tight_layout()
            chart_path = self._save_chart(fig, "portfolio_performance")
            return chart_path

        except Exception as e:
            logger.error(f"Error generating portfolio performance chart: {e}")
            return None

    async def generate_hedge_effectiveness_chart(
        self, hedge_data: Dict[str, List[float]], figsize: tuple = (10, 6)
    ) -> Optional[str]:
        """Generate a hedge effectiveness analysis chart.

        Args:
            hedge_data: Dictionary with hedge effectiveness metrics
            figsize: Figure size (width, height)

        Returns:
            Path to the generated chart image, or None if failed
        """
        try:
            if not hedge_data:
                logger.warning("No hedge data provided")
                return None

            # Create figure and axis
            fig, ax = plt.subplots(figsize=figsize)

            # Prepare data
            hedge_types = list(hedge_data.keys())
            effectiveness = list(hedge_data.values())

            # Create horizontal bar chart
            bars = ax.barh(
                hedge_types,
                effectiveness,
                color=[
                    "green" if x > 50 else "orange" if x > 20 else "red"
                    for x in effectiveness
                ],
            )

            # Customize the plot
            ax.set_title(
                "Hedge Effectiveness Analysis", fontsize=16, fontweight="bold", pad=20
            )
            ax.set_xlabel("Effectiveness (%)", fontsize=12)
            ax.set_xlim(0, 100)

            # Add value labels
            for bar, eff in zip(bars, effectiveness):
                width = bar.get_width()
                ax.text(
                    width + 1,
                    bar.get_y() + bar.get_height() / 2,
                    f"{eff:.1f}%",
                    ha="left",
                    va="center",
                    fontweight="bold",
                )

            # Add effectiveness zones
            ax.axvline(
                x=20, color="red", linestyle="--", alpha=0.5, label="Poor (<20%)"
            )
            ax.axvline(
                x=50, color="orange", linestyle="--", alpha=0.5, label="Fair (20-50%)"
            )
            ax.axvline(
                x=80, color="green", linestyle="--", alpha=0.5, label="Good (>80%)"
            )

            ax.legend()

            plt.tight_layout()
            chart_path = self._save_chart(fig, "hedge_effectiveness")
            return chart_path

        except Exception as e:
            logger.error(f"Error generating hedge effectiveness chart: {e}")
            return None

    def _save_chart(self, fig: plt.Figure, chart_type: str) -> str:
        """Save a matplotlib figure to a temporary file.

        Args:
            fig: Matplotlib figure to save
            chart_type: Type of chart for filename

        Returns:
            Path to the saved chart file
        """
        try:
            # Generate unique filename
            self.chart_counter += 1
            filename = f"goquant_{chart_type}_{self.chart_counter}.png"
            filepath = os.path.join(self.temp_dir, filename)

            # Save the figure
            fig.savefig(filepath, dpi=300, bbox_inches="tight")
            plt.close(fig)  # Close the figure to free memory

            logger.info(f"Chart saved to: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving chart: {e}")
            return ""

    def cleanup_temp_files(self):
        """Clean up temporary chart files."""
        try:
            for filename in os.listdir(self.temp_dir):
                if filename.startswith("goquant_") and filename.endswith(".png"):
                    filepath = os.path.join(self.temp_dir, filename)
                    os.remove(filepath)
                    logger.info(f"Cleaned up: {filepath}")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")


# Global instance for easy access
chart_generator = ChartGenerator()
