# GoQuant Codebase Walkthrough – Narration Script (Intro to Part 9)

---

## INTRO

**Show:** `README.md` (title and overview section), project structure in file explorer  
**Say:**  
“This is GoQuant, an advanced crypto trading bot with hedging and analytics. The README gives a high-level overview of the project, its features, and the architecture. As you can see in the folder structure, the project is organized into modules for the bot, portfolio, exchanges, analytics, risk, and more. We’ll walk through each of these step by step.”

---

## PART 1: PROJECT OVERVIEW & ARCHITECTURE

**Show:** `main.py`  
**Say:**  
“Let’s start at the entry point. The `main.py` file is very simple—it just imports the main bot function and runs it asynchronously. This is where the application starts.”

**Show:** `src/__init__.py` and file explorer  
**Say:**  
“Here’s the `src` directory, which contains all the main code. You can see subfolders for the bot, portfolio, exchanges, analytics, risk, and more. This modular structure keeps the codebase organized and maintainable.”

**Show:** `requirements.txt`  
**Say:**  
“The `requirements.txt` file lists all the dependencies, including libraries for async programming, Telegram integration, data analysis, and visualization.”

---

## PART 2: CORE BOT IMPLEMENTATION

**Show:** `src/bot/__init__.py` (lines 1-100)  
**Say:**  
“This is the main bot class. It initializes the portfolio, sets up exchange connections, and configures risk management. This is where the core state of the bot is managed.”

**Show:** `src/bot/__init__.py` (lines 97-147)  
**Say:**  
“Here are the lifecycle methods for starting and stopping the bot, as well as the risk watcher that monitors portfolio risk in the background.”

**Show:** `src/bot/__init__.py` (lines 238-401)  
**Say:**  
“These are the command handlers. They process user commands from Telegram, such as starting the bot, generating reports, and handling callbacks for user interactions.”

**Show:** `src/bot/keyboards.py` (lines 1-50)  
**Say:**  
“This file defines the Telegram inline keyboards and menu layouts. It also handles encoding and decoding callback data, which is essential for managing complex user flows in the Telegram interface.”

---

## PART 3: PORTFOLIO MANAGEMENT

**Show:** `src/portfolio/state.py` (lines 1-50)  
**Say:**  
“Portfolio management is handled here. The `Position` and `Transaction` dataclasses define how positions and trades are stored.”

**Show:** `src/portfolio/state.py` (lines 51-150)  
**Say:**  
“These methods add, update, and remove positions, and keep track of all trades in the transaction history.”

**Show:** `src/portfolio/state.py` (lines 151-250)  
**Say:**  
“This section calculates real-time P&L, delta, and risk metrics for the portfolio, providing the analytics needed for risk management and reporting.”

---

## PART 4: EXCHANGE INTEGRATIONS

**Show:** `src/exchanges/okx.py` (lines 1-50)  
**Say:**  
“This file implements the OKX exchange integration, with async methods for fetching tickers and order books for spot and perpetual trading.”

**Show:** `src/exchanges/deribit.py` (lines 1-50)  
**Say:**  
“This is the base integration for Deribit, handling authentication and basic data fetching.”

**Show:** `src/exchanges/deribit_options.py` (lines 1-50)  
**Say:**  
“This file extends the Deribit integration to support options-specific data, such as fetching the option chain and option tickers.”

**Show:** `src/exchanges/types.py`  
**Say:**  
“This file defines common data types used across exchange integrations, ensuring consistency in how market data is represented.”

---

## PART 5: OPTIONS STRATEGIES

**Show:** `src/options/strategies.py` (lines 1-50)  
**Say:**  
“This file contains the base classes and data structures for options strategies, including the `OptionLeg` dataclass.”

**Show:** `src/options/strategies.py` (lines 51-150)  
**Say:**  
“Here are the implementations for individual strategies. Each strategy is a static method that returns the option legs and payoff profile for that strategy.”

**Show:** 2-3 specific strategies (e.g., straddle, butterfly)  
**Say:**  
“Let’s look at a couple of strategies in detail. For example, the straddle and butterfly strategies show how the system constructs multi-leg options positions and calculates their risk and reward profiles.”

---

## PART 6: SERVICES LAYER

**Show:** `src/services/costing.py` (lines 1-50)  
**Say:**  
“This service calculates trading fees and slippage for each trade, which is important for accurate P&L and cost analysis.”

**Show:** `src/services/hedge.py` (lines 1-50)  
**Say:**  
“This file contains the logic for optimizing hedge selection and calculating hedge effectiveness.”

**Show:** `src/services/options_pricing.py` (lines 1-50)  
**Say:**  
“This service implements advanced options pricing models, supporting the analytics and risk modules.”

---

## PART 7: ADVANCED ANALYTICS

**Show:** `src/analytics/historical_data.py` (lines 1-50)  
**Say:**  
“This module collects historical price data from multiple exchanges and caches it for performance. It’s used for analytics and risk calculations.”

**Show:** `src/analytics/correlation.py` (lines 1-50)  
**Say:**  
“This file analyzes correlations between portfolio positions and hedges, helping to optimize diversification and risk management.”

**Show:** `src/analytics/charts.py` (lines 1-50)  
**Say:**  
“This module generates professional charts and visualizations, such as correlation heatmaps and P&L time series, using matplotlib and seaborn.”

**Show:** `src/analytics/stress_testing.py` (lines 1-50)  
**Say:**  
“This file implements scenario-based stress testing, allowing you to see how the portfolio would perform under different market shocks.”

---

## PART 8: RISK MANAGEMENT

**Show:** `src/risk/greeks.py` (lines 1-50)  
**Say:**  
“This module implements the Black-Scholes model and calculates Greeks like delta, gamma, theta, and vega for options.”

**Show:** `src/risk/greeks.py` (lines 51-100)  
**Say:**  
“Here are the functions for calculating portfolio-level Greeks, aggregating risk across all positions.”

**Show:** `src/risk/metrics.py` (lines 1-50)  
**Say:**  
“This file calculates risk metrics for individual positions and the overall portfolio, including delta exposure and concentration risk.”

**Show:** `src/risk/metrics.py` (lines 51-100)  
**Say:**  
“Here’s where the system generates human-readable risk reports, summarizing the portfolio’s risk profile.”

---

## PART 9: MARKET DATA BUS

**Show:** `src/market_bus.py`  
**Say:**  
“The market data bus aggregates real-time price data from all connected exchanges and normalizes it for use throughout the system.” 