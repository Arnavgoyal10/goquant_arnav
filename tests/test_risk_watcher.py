import asyncio
import types

# Import the SpotHedgerBot class from your bot module
from src.bot.__init__ import SpotHedgerBot


class DummyPortfolio:
    def get_total_delta(self):
        return 2.0  # Breach delta threshold

    def get_var_95(self):
        return 5000.0  # Breach VaR threshold

    def get_max_drawdown(self):
        return 0.25  # Breach drawdown threshold


class DummyBot:
    async def send_message(self, chat_id, text, parse_mode=None):
        print(f"[ALERT to {chat_id}] {text}")


async def test_risk_watcher():
    bot = SpotHedgerBot()
    # Set dummy portfolio
    bot.portfolio = DummyPortfolio()
    # Set very low thresholds to force alerts
    bot.risk_config = {
        "abs_delta": 1.0,
        "var_95": 1000.0,
        "max_drawdown": 0.10,
    }

    # Set up dummy Telegram bot and user id
    class DummyApp:
        bot_data = {"main_user_id": 12345}
        bot = DummyBot()

    bot.application = DummyApp()
    bot.last_user_id = 12345
    # Run the risk check
    await bot.check_risk_metrics_and_alert()


if __name__ == "__main__":
    asyncio.run(test_risk_watcher())
