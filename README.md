# GoQuant - Advanced Crypto Trading Bot with Hedging

A sophisticated Telegram-based cryptocurrency trading bot designed for spot exposure hedging with live OKX and Deribit connectivity. The bot provides comprehensive portfolio management, advanced hedging strategies, real-time analytics, and automated risk monitoring.

## 🚀 Features

### Core Functionality
- **Real-time Portfolio Management**: Add/remove spot and perpetual positions with live price feeds
- **Advanced Hedging Strategies**: 8 different hedging strategies with automatic and manual selection
- **Live Market Data**: Real-time connectivity to OKX and Deribit exchanges
- **Risk Management**: Automated risk monitoring with configurable thresholds
- **Transaction Tracking**: Complete transaction history with P&L attribution
- **Performance Analytics**: Detailed attribution and cost-benefit analysis

### Hedging Strategies

#### 1. **Perpetual Delta-Neutral Hedge**
- Automatically calculates required perpetual position to neutralize portfolio delta
- Real-time delta calculation and position sizing
- Cost-effective hedging with minimal slippage

#### 2. **Protective Put Strategy**
- **Automatic Mode**: Bot selects optimal ATM put options based on current price
- **Manual Mode**: User selects expiry and strike from live Deribit data
- Provides downside protection while maintaining upside potential
- Features:
  - 10 closest puts to ATM selection
  - Real-time pricing and Greeks calculation
  - Cost estimation with fallback pricing

#### 3. **Covered Call Strategy**
- **Automatic Mode**: Bot selects OTM call options for premium income
- **Manual Mode**: User selects expiry and strike from live options chain
- Generates income while capping upside potential
- Features:
  - OTM call selection for optimal premium
  - Greeks calculation and risk assessment
  - Premium income vs. upside limitation analysis

#### 4. **Collar Strategy**
- **Automatic Mode**: Bot selects ATM put and OTM call for cost-neutral hedge
- **Manual Mode**: Two-step selection process for both legs
- Combines protective put with covered call for cost-effective protection
- Features:
  - Two-step strike selection (put then call)
  - Combined summary with net cost calculation
  - Risk reduction analysis with Greeks display

#### 5. **Dynamic Hedge Strategy**
- **Automatic Mode Only**: Smart option selection with multi-criteria optimization
- Advanced algorithm for optimal hedge selection
- Features:
  - Multi-criteria optimization (delta, cost, liquidity)
  - Real-time market analysis
  - Adaptive strategy based on market conditions

#### 6. **Straddle Strategy**
- **Automatic Mode**: Bot selects ATM strike for maximum volatility exposure
- **Manual Mode**: User selects expiry and strike
- Profits from significant price movements in either direction
- Features:
  - Volatility-based profit potential
  - Defined risk with unlimited upside
  - Greeks calculation for both legs

#### 7. **Butterfly Strategy**
- **Automatic Mode**: Bot constructs call or put butterfly spread
- **Manual Mode**: User selects three strikes for the spread
- Limited risk, limited reward strategy
- Features:
  - Three-leg option spread
  - Defined risk and reward
  - Neutral delta profile

#### 8. **Iron Condor Strategy**
- **Automatic Mode**: Bot selects optimal strikes for maximum premium
- **Manual Mode**: User selects four strikes for the spread
- Income generation with defined risk
- Features:
  - Four-leg option spread
  - Premium income strategy
  - Wide profit range with defined risk

### Portfolio Management

#### Position Management
- **Add Spot Position**: Add BTC spot positions with real-time pricing
- **Remove Spot Position**: Close spot positions with P&L calculation
- **Add Future Position**: Add perpetual positions with direction selection
- **Remove Future Position**: Close perpetual positions with cost analysis

#### Real-time Features
- Live price feeds from OKX and Deribit
- Real-time P&L calculation
- Position sizing with cost estimation
- Transaction history tracking

### Analytics & Reporting

#### Portfolio Analytics
- **Real-time P&L**: Realized and unrealized profit/loss tracking
- **Delta Analysis**: Portfolio delta calculation with hedge attribution
- **Risk Metrics**: VaR (95%), maximum drawdown calculation
- **Greeks Summary**: Delta, gamma, theta, vega for option positions

#### Performance Attribution
- **Hedge Effectiveness**: Percentage of portfolio risk hedged
- **Cost Analysis**: Breakdown of hedge costs vs. benefits
- **P&L Attribution**: Detailed breakdown by position and hedge type
- **Performance Metrics**: Risk-adjusted returns and efficiency ratios

#### Cost-Benefit Analysis
- **Total Hedge Cost**: Aggregated costs across all hedges
- **Benefit Calculation**: P&L improvement and risk reduction
- **Net Benefit**: Cost vs. benefit analysis
- **ROI Metrics**: Return on hedge investment

### Risk Management

#### Risk Watcher (Phase 8.2)
- **Background Monitoring**: Continuous risk metric monitoring
- **Configurable Thresholds**: 
  - Absolute Delta: 5 BTC default
  - 95% VaR: $10,000 default
  - Max Drawdown: 15% default
- **Automated Alerts**: Telegram notifications when thresholds breached
- **Real-time Updates**: 20-second monitoring intervals

#### Risk Configuration
- **Editable Thresholds**: Modify risk parameters via Telegram interface
- **Real-time Validation**: Input validation and confirmation
- **Persistent Settings**: In-memory configuration management

### Transaction Management

#### Transaction History
- **Complete Tracking**: All trades, hedges, and position changes
- **P&L Attribution**: Realized and unrealized profit/loss
- **Volume Analysis**: Total trading volume and frequency
- **Type Classification**: Buy, sell, add, remove, hedge transactions

#### Transaction Summary
- **Total Transactions**: Count and volume statistics
- **P&L Summary**: Aggregate profit/loss across all transactions
- **Type Breakdown**: Analysis by transaction type
- **Instrument Analysis**: Performance by instrument type

## 🏗️ Technical Architecture

### Core Components

#### 1. **Bot Core** (`src/bot/__init__.py`)
- Main bot application with 5,000+ lines of functionality
- Telegram interface with inline keyboards
- Callback handling for complex user flows
- Real-time market data integration

#### 2. **Portfolio Management** (`src/portfolio/state.py`)
- Position tracking with dataclass-based structure
- Transaction history with P&L calculation
- Real-time delta and Greeks calculation
- Risk metrics (VaR, drawdown) computation

#### 3. **Exchange Integration**
- **OKX Exchange** (`src/exchanges/okx.py`): Spot and perpetual trading
- **Deribit Exchange** (`src/exchanges/deribit.py`): Options trading
- **Deribit Options** (`src/exchanges/deribit_options.py`): Advanced options data

#### 4. **Option Strategies** (`src/options/strategies.py`)
- 8 advanced option strategies implementation
- Greeks calculation for all strategies
- Payoff profile analysis
- Risk/reward optimization

#### 5. **Services Layer**
- **Costing Service** (`src/services/costing.py`): Fee and slippage calculation
- **Hedge Service** (`src/services/hedge.py`): Hedge strategy implementation
- **Options Pricing** (`src/services/options_pricing.py`): Advanced pricing models

#### 6. **Market Data Bus** (`src/market_bus.py`)
- Real-time market data aggregation
- Price feed management
- Data normalization across exchanges

## 🧭 Code Navigation Guide

This section helps new developers understand the codebase structure and navigate through the different components.

### 📁 Project Structure Overview

```
goquant/
├── main.py                          # Entry point - starts the bot
├── requirements.txt                 # Python dependencies
├── README.md                       # This documentation
├── src/                            # Main source code
│   ├── bot/                        # Telegram bot implementation
│   │   ├── __init__.py            # Main bot class (5,000+ lines)
│   │   └── keyboards.py           # Inline keyboard layouts
│   ├── portfolio/                  # Portfolio management
│   │   └── state.py               # Position & transaction tracking
│   ├── exchanges/                  # Exchange integrations
│   │   ├── okx.py                 # OKX spot/perpetual trading
│   │   ├── deribit.py             # Deribit base functionality
│   │   ├── deribit_options.py     # Options-specific functionality
│   │   └── types.py               # Common data types
│   ├── options/                    # Options strategies
│   │   └── strategies.py          # 8 option strategies implementation
│   ├── services/                   # Business logic services
│   │   ├── costing.py             # Fee & slippage calculations
│   │   ├── hedge.py               # Hedge strategy logic
│   │   └── options_pricing.py     # Options pricing models
│   ├── risk/                       # Risk management
│   ├── util/                       # Utilities
│   └── market_bus.py              # Market data aggregation
├── tests/                          # Test files
├── configs/                        # Configuration files
├── docs/                           # Documentation
└── notebooks/                      # Jupyter notebooks
```

### 🔍 Detailed Component Breakdown

#### **1. Entry Point (`main.py`)**
```python
# Simple entry point that starts the bot
import asyncio
from src.bot import main as bot_main

if __name__ == "__main__":
    asyncio.run(bot_main())
```
**What it does**: Initializes and runs the Telegram bot
**For new developers**: Start here to understand how the bot is launched

#### **2. Bot Core (`src/bot/__init__.py`)**
This is the heart of the application with 5,000+ lines. Here's how to navigate it:

**Class Structure**:
```python
class SpotHedgerBot:
    def __init__(self):
        # Initialize portfolio, exchanges, risk config
        self.portfolio = Portfolio()
        self.active_hedges = []
        self.risk_config = {...}
```

**Key Sections** (in order of appearance):

1. **Initialization (Lines 41-72)**
   - Sets up portfolio, exchanges, risk configuration
   - Initializes active hedges tracking
   - Configures risk watcher settings

2. **Market Data Methods (Lines 72-97)**
   - `get_current_price()`: Fetches live prices from exchanges
   - Handles different instrument types (spot, perpetual, options)

3. **Bot Lifecycle (Lines 97-147)**
   - `start()`: Initializes bot, handlers, risk watcher
   - `stop()`: Clean shutdown of all components
   - `risk_watcher()`: Background risk monitoring

4. **Command Handlers (Lines 238-401)**
   - `/start`: Main menu display
   - `/report`: Transaction report generation
   - `handle_callback()`: Main callback router

5. **Portfolio Management (Lines 449-810)**
   - Add/remove spot and future positions
   - Position confirmation flows
   - Portfolio display and updates

6. **Analytics System (Lines 868-1101)**
   - Portfolio analytics with real-time data
   - Performance attribution
   - Cost-benefit analysis
   - Transaction history

7. **Hedging Strategies (Lines 1425-4420)**
   - 8 different hedging strategies
   - Each strategy has: auto flow, manual selection, confirmation
   - Complex callback handling for multi-step flows

8. **Risk Management (Lines 147-238)**
   - Background risk monitoring
   - Configurable thresholds
   - Automated alerts

**For new developers**: 
- Start with the `__init__()` method to understand the bot's structure
- Look at `handle_callback()` to understand how user interactions are routed
- Each hedging strategy follows a similar pattern: start → auto/manual → confirm

#### **3. Portfolio Management (`src/portfolio/state.py`)**

**Key Classes**:
```python
@dataclass
class Position:
    symbol: str
    qty: float
    avg_px: float
    instrument_type: str
    exchange: str
    timestamp: datetime

@dataclass  
class Transaction:
    id: str
    symbol: str
    qty: float
    price: float
    # ... other fields

class Portfolio:
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.transactions: List[Transaction] = []
```

**Key Methods**:
- `add_position()`: Add new position
- `update_fill()`: Update position with new trade
- `get_total_delta()`: Calculate portfolio delta
- `get_unrealized_pnl()`: Calculate P&L
- `get_var_95()`: Calculate Value at Risk

**For new developers**: 
- This is where all position and transaction data is stored
- Understand the `Position` and `Transaction` dataclasses first
- The `Portfolio` class manages all trading state

#### **4. Exchange Integrations (`src/exchanges/`)**

**OKX Integration (`okx.py`)**:
```python
class OKXExchange:
    async def get_ticker(self, symbol: str) -> Ticker
    async def get_orderbook(self, symbol: str) -> OrderBook
```
**What it does**: Handles spot and perpetual trading on OKX
**For new developers**: Look at the `get_ticker()` method to understand how market data is fetched

**Deribit Integration (`deribit.py` & `deribit_options.py`)**:
```python
class DeribitExchange:
    async def get_ticker(self, symbol: str) -> Ticker
    
class DeribitOptions:
    async def get_option_chain(self, expiry: str) -> List[Instrument]
    async def get_option_ticker(self, symbol: str) -> Ticker
```
**What it does**: Handles options trading and data from Deribit
**For new developers**: The options integration is more complex - start with `get_option_chain()` to understand how options data is structured

#### **5. Options Strategies (`src/options/strategies.py`)**

**Key Classes**:
```python
@dataclass
class OptionLeg:
    symbol: str
    qty: float
    strike: float
    expiry: str
    option_type: str
    price: float
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0

class OptionStrategies:
    @staticmethod
    def straddle(...) -> Tuple[List[OptionLeg], StrategyPayoff]
    @staticmethod
    def butterfly(...) -> Tuple[List[OptionLeg], StrategyPayoff]
    # ... 6 more strategies
```

**What it does**: Implements 8 different options strategies with Greeks calculation
**For new developers**: 
- Each strategy method returns option legs and payoff profile
- Start with `straddle()` as it's the simplest strategy
- Understand how Greeks are calculated for each leg

#### **6. Services Layer (`src/services/`)**

**Costing Service (`costing.py`)**:
```python
class CostingService:
    def calculate_total_cost(self, qty, price, exchange, instrument_type) -> Dict
    def get_cost_summary(self, qty, price, exchange, instrument_type) -> str
```
**What it does**: Calculates trading fees, slippage, and total costs
**For new developers**: Essential for understanding trading costs - used throughout the bot

**Hedge Service (`hedge.py`)**:
```python
class HedgeService:
    def calculate_hedge_effectiveness(self, portfolio_delta, hedge_delta) -> float
    def optimize_hedge_selection(self, options, criteria) -> List[Option]
```
**What it does**: Implements hedge strategy logic and optimization
**For new developers**: Core business logic for hedging decisions

#### **7. User Interface (`src/bot/keyboards.py`)**

**Key Functions**:
```python
def encode_callback_data(flow: str, step: str, data: Dict) -> str
def decode_callback_data(callback_data: str) -> tuple[str, str, dict]
def get_main_menu() -> InlineKeyboardMarkup
def get_hedge_menu() -> InlineKeyboardMarkup
```

**What it does**: Manages all Telegram inline keyboards and callback data encoding
**For new developers**: 
- Understand the callback data system first
- Each menu function returns a keyboard layout
- The encoding/decoding handles complex data passing through Telegram's limitations

### 🔄 Understanding the Flow

#### **Typical User Journey**:
1. **User starts bot** → `main.py` → `SpotHedgerBot.start()`
2. **User clicks menu** → `handle_callback()` → `show_main_menu()`
3. **User selects hedge** → `handle_hedge_callback()` → `start_protective_put_hedge()`
4. **User confirms hedge** → `confirm_hedge_action()` → Portfolio updated

#### **Data Flow**:
1. **Market Data**: Exchange APIs → `get_current_price()` → Portfolio calculations
2. **User Input**: Telegram → `handle_callback()` → Strategy logic → Portfolio update
3. **Risk Monitoring**: Background task → Risk metrics → Telegram alerts

### 🎯 Where to Start for New Developers

#### **If you're new to the codebase**:
1. **Start with `main.py`** - understand how the bot launches
2. **Read `src/bot/__init__.py` lines 41-97** - understand the bot's structure
3. **Look at `src/portfolio/state.py`** - understand how data is stored
4. **Study `src/bot/keyboards.py`** - understand the UI system
5. **Pick one hedge strategy** - follow the flow from start to confirmation

#### **If you want to add a new feature**:
1. **Identify the component** - which service/module handles this?
2. **Follow the pattern** - look at similar features for the structure
3. **Update the UI** - add keyboard buttons in `keyboards.py`
4. **Add handlers** - implement callback handlers in the bot
5. **Test the flow** - ensure the complete user journey works

#### **If you want to understand hedging**:
1. **Start with `src/options/strategies.py`** - understand option strategies
2. **Look at one hedge flow** - e.g., protective put in the bot
3. **Follow the data** - how does the strategy get applied to the portfolio?
4. **Check the analytics** - how is performance measured?

### 🔧 Common Patterns

#### **Callback Data Pattern**:
```python
# Encoding
callback_data = encode_callback_data("hedge", "protective_put_auto", {})

# Decoding  
flow, step, data = decode_callback_data(callback_data)
if step == "protective_put_auto":
    await self.protective_put_auto_flow(update, context)
```

#### **Hedge Strategy Pattern**:
```python
async def start_protective_put_hedge(self, update, context):
    # Show strategy options (Auto/Manual)
    
async def protective_put_auto_flow(self, update, context):
    # Automatic hedge selection
    
async def protective_put_select_expiry(self, update, context):
    # Manual expiry selection
    
async def protective_put_select_confirm(self, update, context, data):
    # Final confirmation
```

#### **Portfolio Update Pattern**:
```python
# Update position
self.portfolio.update_fill(symbol, qty, price, instrument_type, exchange)

# Record transaction
self.portfolio.record_transaction(symbol, qty, price, ...)

# Add to active hedges
self.active_hedges.append(hedge_data)
```

### 🚨 Important Notes for New Developers

1. **Async/Await**: The entire bot is async - understand Python's async patterns
2. **Telegram Limits**: Callback data has 64-byte limit - use compact encoding
3. **Error Handling**: Always wrap exchange calls in try/catch
4. **State Management**: Portfolio state is in-memory - consider persistence
5. **Testing**: Use the test files to understand expected behavior

### 📚 Key Files to Study

**For understanding the bot**:
- `src/bot/__init__.py` (lines 1-500) - Bot structure and initialization
- `src/bot/keyboards.py` - UI system and callback handling

**For understanding trading**:
- `src/portfolio/state.py` - How positions and transactions work
- `src/exchanges/okx.py` - How market data is fetched

**For understanding hedging**:
- `src/options/strategies.py` - Option strategies implementation
- `src/bot/__init__.py` (lines 1600-3000) - Hedge strategy flows

**For understanding costs**:
- `src/services/costing.py` - Fee and cost calculations
- `src/services/hedge.py` - Hedge optimization logic

### Data Structures

#### Position Management
```python
@dataclass
class Position:
    symbol: str
    qty: float
    avg_px: float
    instrument_type: Literal["spot", "perpetual", "option"]
    exchange: str
    timestamp: datetime
```

#### Transaction Tracking
```python
@dataclass
class Transaction:
    id: str
    symbol: str
    qty: float
    price: float
    instrument_type: Literal["spot", "perpetual", "option"]
    exchange: str
    transaction_type: Literal["buy", "sell", "add", "remove", "hedge"]
    timestamp: datetime
    pnl: Optional[float] = None
    notes: Optional[str] = None
```

#### Option Strategies
```python
@dataclass
class OptionLeg:
    symbol: str
    qty: float
    strike: float
    expiry: str
    option_type: str
    price: float
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
```

### User Interface

#### Main Menu Structure
```
📊 Portfolio    🛡️ Hedge
📈 Analytics    📋 Transactions
⚙️ Risk Config
```

#### Portfolio Menu
```
➕ Add Spot     ➖ Remove Spot
➕ Add Future   ➖ Remove Future
🔄 Refresh      🔙 Back
```

#### Hedge Menu
```
⚖️ Perp Δ-Neutral    🛡️ Protective Put
📈 Covered Call       🔒 Collar
🦋 Straddle          🦋 Butterfly
🦅 Iron Condor       ♻️ Dynamic Hedge
📂 View Hedges       🗑️ Remove Hedge
```

#### Analytics Menu
```
📊 By Position    🛡️ By Hedge
📈 Performance    💰 Cost-Benefit
```

## 🔧 Installation & Setup

### Prerequisites
- Python 3.8+
- Telegram Bot Token
- OKX API credentials (optional)
- Deribit API credentials (optional)

### Dependencies
```bash
pip install -r requirements.txt
```

### Key Dependencies
- `python-telegram-bot==22.2`: Telegram bot framework
- `aiohttp==3.12.13`: Async HTTP client
- `loguru==0.7.3`: Advanced logging
- `pandas==2.3.1`: Data manipulation
- `numpy==2.3.1`: Numerical computing
- `websockets==15.0.1`: Real-time data feeds

### Environment Variables
```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OKX_API_KEY=your_okx_api_key
OKX_SECRET_KEY=your_okx_secret_key
DERIBIT_API_KEY=your_deribit_api_key
DERIBIT_SECRET_KEY=your_deribit_secret_key
```

### Running the Bot
```bash
python main.py
```

## 📊 Usage Examples

### Adding a Spot Position
1. Select "📊 Portfolio" from main menu
2. Choose "➕ Add Spot"
3. Enter quantity (e.g., "5.0" for 5 BTC)
4. Review cost breakdown and confirm

### Creating a Protective Put Hedge
1. Select "🛡️ Hedge" from main menu
2. Choose "🛡️ Protective Put"
3. Select "Automatic" or "Select" mode
4. For automatic: Bot selects optimal put
5. For manual: Choose expiry, then strike
6. Review summary and confirm hedge

### Viewing Analytics
1. Select "📈 Analytics" from main menu
2. Choose analysis type:
   - "📊 By Position": Individual position analysis
   - "🛡️ By Hedge": Hedge performance breakdown
   - "📈 Performance": Attribution analysis
   - "💰 Cost-Benefit": Cost vs. benefit analysis

### Risk Configuration
1. Select "⚙️ Risk Config" from main menu
2. Choose metric to edit (Delta, VaR, Drawdown)
3. Enter new threshold value
4. Confirm changes

## 🔄 Callback Data System

The bot uses a sophisticated callback data encoding system to handle complex user flows:

### Compact Format
- **Format**: `flow|step|data`
- **Example**: `hedge|protective_put_select_strike|25JUL25`
- **Benefits**: Handles Telegram's 64-byte limit efficiently

### JSON Format
- **Format**: `flow|step|{"key": "value"}`
- **Example**: `hedge|confirm|{"expiry": "25JUL25", "strike": "110000"}`
- **Benefits**: Rich data structure for complex flows

### Parsing Logic
```python
def decode_callback_data(callback_data: str) -> tuple[str, str, dict]:
    parts = callback_data.split("|", 3)
    if len(parts) == 4:
        flow, step, part1, part2 = parts
        data = f"{part1}|{part2}"
    elif len(parts) == 3:
        flow, step, json_data = parts
        data = json.loads(json_data)
    return flow, step, data
```

## 🛡️ Risk Management Features

### Real-time Risk Monitoring
- **Background Task**: Continuous monitoring every 20 seconds
- **Multi-threshold**: Delta, VaR, and drawdown monitoring
- **Alert System**: Telegram notifications for breaches
- **State Tracking**: Prevents duplicate alerts

### Risk Metrics Calculation
- **Delta**: Portfolio exposure to underlying price movements
- **VaR (95%)**: 2% of portfolio notional for crypto
- **Drawdown**: Historical peak to current value tracking
- **Greeks**: Delta, gamma, theta, vega for options

### Cost Analysis
- **Fee Calculation**: Exchange-specific fee rates
- **Slippage Estimation**: Market impact modeling
- **Total Cost**: Fee + slippage + execution costs
- **Cost Percentage**: Cost as percentage of notional

## 📈 Analytics & Performance

### Portfolio Analytics
- **Real-time P&L**: Realized and unrealized profit/loss
- **Position Analysis**: Individual position performance
- **Hedge Attribution**: Hedge effectiveness metrics
- **Risk Metrics**: VaR, drawdown, delta analysis

### Performance Attribution
- **Hedge Count**: Number of active hedges
- **Hedge P&L**: Aggregate hedge performance
- **Hedge Cost**: Total cost of hedging
- **Effectiveness**: Hedge P&L as percentage of portfolio P&L

### Cost-Benefit Analysis
- **Total Cost**: Aggregated hedge costs
- **Total Benefit**: P&L improvement from hedging
- **Net Benefit**: Cost vs. benefit analysis
- **ROI Metrics**: Return on hedge investment

## 🔧 Advanced Features

### Dynamic Hedge Optimization
- **Multi-criteria Selection**: Delta, cost, liquidity optimization
- **Real-time Analysis**: Live market data integration
- **Adaptive Strategy**: Market condition-based selection
- **Performance Scoring**: Effectiveness metrics

### Option Strategy Implementation
- **8 Strategies**: Straddle, butterfly, iron condor, etc.
- **Greeks Calculation**: Real-time option Greeks
- **Payoff Analysis**: Risk/reward profiles
- **Cost Estimation**: Premium and margin requirements

### Transaction Management
- **Complete History**: All trades and position changes
- **P&L Attribution**: Realized and unrealized profit/loss
- **Volume Analysis**: Trading volume and frequency
- **Type Classification**: Transaction categorization

## 🚀 Future Enhancements

### Planned Features
- **Multi-user Support**: Multiple user management
- **Advanced Analytics**: Machine learning-based insights
- **Backtesting**: Historical strategy performance
- **Mobile App**: Native mobile application
- **API Integration**: REST API for external access

### Technical Improvements
- **Database Integration**: Persistent data storage
- **WebSocket Optimization**: Enhanced real-time feeds
- **Performance Monitoring**: System health metrics
- **Error Recovery**: Robust error handling

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Contact the development team
- Check the documentation

---

**GoQuant** - Advanced crypto trading with intelligent hedging strategies.
