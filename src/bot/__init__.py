"""Telegram bot core for the spot hedging bot."""

import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from loguru import logger

from .keyboards import get_main_menu, get_back_button
from ..util.env import get_telegram_token, validate_environment


class SpotHedgerBot:
    """Main bot application for spot hedging operations."""

    def __init__(self):
        self.application = None
        self.token = get_telegram_token()

        if not self.token:
            raise ValueError("Telegram token not found in environment")

    async def start(self):
        """Start the bot application."""
        logger.info("Starting Spot Hedger Bot...")

        # Create application
        self.application = Application.builder().token(self.token).build()

        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

        # Start the bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        logger.info("Bot started successfully!")

    async def stop(self):
        """Stop the bot application."""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Bot stopped.")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        logger.info(f"User {user.id} started the bot")

        welcome_text = (
            f"🤖 Welcome to Spot Hedger Bot, {user.first_name}!\n\n"
            "Manage your cryptocurrency positions and hedge your exposure.\n"
            "Select an option from the menu below:"
        )

        await update.message.reply_text(welcome_text, reply_markup=get_main_menu())

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()

        data = query.data
        logger.info(f"Callback received: {data}")

        # Parse callback data
        if data == "portfolio":
            await self.show_portfolio(update, context)
        elif data == "hedge":
            await self.show_hedge_menu(update, context)
        elif data == "analytics":
            await self.show_analytics(update, context)
        elif data == "risk_config":
            await self.show_risk_config(update, context)
        elif data == "back":
            await self.show_main_menu(update, context)
        else:
            await query.edit_message_text("Unknown option selected.")

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the main menu."""
        query = update.callback_query
        welcome_text = "🤖 Spot Hedger Bot\n\nSelect an option:"

        await query.edit_message_text(welcome_text, reply_markup=get_main_menu())

    async def show_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show portfolio overview."""
        query = update.callback_query

        # TODO: Implement portfolio overview
        portfolio_text = "📊 Portfolio Overview\n\nComing soon..."

        await query.edit_message_text(portfolio_text, reply_markup=get_back_button())

    async def show_hedge_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show hedge menu."""
        query = update.callback_query

        # TODO: Implement hedge menu
        hedge_text = "🛡️ Hedge Menu\n\nComing soon..."

        await query.edit_message_text(hedge_text, reply_markup=get_back_button())

    async def show_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show analytics menu."""
        query = update.callback_query

        # TODO: Implement analytics
        analytics_text = "📈 Analytics\n\nComing soon..."

        await query.edit_message_text(analytics_text, reply_markup=get_back_button())

    async def show_risk_config(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show risk configuration."""
        query = update.callback_query

        # TODO: Implement risk config
        risk_text = "⚙️ Risk Configuration\n\nComing soon..."

        await query.edit_message_text(risk_text, reply_markup=get_back_button())


async def main():
    """Main function to run the bot."""
    # Validate environment
    if not validate_environment():
        logger.error("Environment validation failed")
        return

    # Create and start bot
    bot = SpotHedgerBot()

    try:
        await bot.start()

        # Keep the bot running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down bot...")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
