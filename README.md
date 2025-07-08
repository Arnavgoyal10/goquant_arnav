# Spot Hedger Bot

A Telegram-based bot for hedging spot cryptocurrency exposures using perpetual futures and options.

## Features

- Real-time market data from OKX and Deribit
- Portfolio management and position tracking
- Risk metrics calculation (delta, gamma, theta, VaR)
- Automated hedging strategies
- Telegram-based user interface

## Development

This project uses Poetry for dependency management and requires Python 3.11-3.12.

### Setup

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Testing

```bash
poetry run pytest
```

## Project Structure

- `src/` - Main application code
- `tests/` - Test files
- `configs/` - Configuration files
- `docs/` - Documentation
- `notebooks/` - Jupyter notebooks for analysis 