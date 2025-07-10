"""Telegram bot core for the spot hedging bot."""

import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from loguru import logger
from datetime import datetime
import json
import logging
import time

from .keyboards import (
    get_main_menu,
    get_back_button,
    get_portfolio_menu,
    get_confirmation_buttons,
    encode_callback_data,
    decode_callback_data,
    get_hedge_menu,
)
from ..portfolio.state import Portfolio
from ..util.env import get_telegram_token, validate_environment
from ..services.costing import costing_service
from ..services.hedge import hedge_service
from ..market_bus import MarketBus
from ..exchanges.okx import OKXExchange
from ..exchanges.deribit import DeribitExchange


class SpotHedgerBot:
    """Main bot application for spot hedging operations."""

    def __init__(self):
        self.application = None
        self.token = get_telegram_token()
        self.portfolio = Portfolio()  # Add portfolio instance
        self.market_bus = MarketBus()  # Add market data bus

        # Initialize market data fetchers
        self.okx_fetcher = OKXExchange()
        self.deribit_fetcher = DeribitExchange()

        # Track active hedges
        self.active_hedges = []

        # Add risk config state (in-memory for now)
        self.risk_config = {
            "abs_delta": 5,  # BTC
            "var_95": 10000.0,  # USD
            "max_drawdown": 0.15,  # 15%
        }

        self.risk_alert_state = {  # Track which alerts have been sent
            "abs_delta": False,
            "var_95": False,
            "max_drawdown": False,
        }
        self.risk_watcher_task = None
        self.risk_watcher_interval = 20  # seconds

        if not self.token:
            raise ValueError("Telegram token not found in environment")

    async def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol from market data."""
        try:
            # Map symbols to exchange and instrument
            if "SPOT" in symbol:
                # Use OKX for spot
                ticker = await self.okx_fetcher.get_ticker(symbol)
                return float(ticker.last_price) if ticker else 108000.0
            elif "PERP" in symbol:
                # Use OKX for perpetuals
                ticker = await self.okx_fetcher.get_ticker(symbol)
                return float(ticker.last_price) if ticker else 107950.0
            else:
                # Default fallback
                return 108000.0
        except Exception as e:
            logger.warning(f"Failed to get price for {symbol}: {e}")
            # Fallback prices
            if "SPOT" in symbol:
                return 108000.0
            elif "PERP" in symbol:
                return 107950.0
            else:
                return 108000.0

    async def start(self):
        """Start the bot application."""
        logger.info("Starting Spot Hedger Bot...")

        # Initialize exchange sessions
        await self.okx_fetcher.__aenter__()
        await self.deribit_fetcher.__aenter__()

        # Create application
        self.application = Application.builder().token(self.token).build()

        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        # Start the bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        logger.info("Bot started successfully!")

        # Start risk watcher
        self.risk_watcher_task = asyncio.create_task(self.risk_watcher())

    async def stop(self):
        """Stop the bot application."""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

            # Close exchange sessions
            await self.okx_fetcher.__aexit__(None, None, None)
            await self.deribit_fetcher.__aexit__(None, None, None)

            logger.info("Bot stopped.")

        # Stop risk watcher
        if self.risk_watcher_task:
            self.risk_watcher_task.cancel()
            try:
                await self.risk_watcher_task
            except asyncio.CancelledError:
                pass

    async def risk_watcher(self):
        """Background task: periodically check risk metrics and alert if breached."""
        while True:
            try:
                await asyncio.sleep(self.risk_watcher_interval)
                await self.check_risk_metrics_and_alert()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"[risk_watcher] Error: {e}")

    async def check_risk_metrics_and_alert(self):
        """Check risk metrics and send Telegram alerts if thresholds are breached."""
        # Only alert the main user (first user who started the bot)
        # You can expand this to multi-user if needed
        user_id = None
        if (
            hasattr(self, "application")
            and self.application
            and self.application.bot_data.get("main_user_id")
        ):
            user_id = self.application.bot_data["main_user_id"]
        elif hasattr(self, "last_user_id"):
            user_id = self.last_user_id
        # Fallback: try to get from portfolio or context
        if (
            not user_id
            and hasattr(self, "portfolio")
            and hasattr(self.portfolio, "user_id")
        ):
            user_id = self.portfolio.user_id
        if not user_id:
            return  # No user to alert

        # Get current risk metrics
        delta = (
            self.portfolio.get_total_delta()
            if hasattr(self.portfolio, "get_total_delta")
            else 0.0
        )
        var_95 = (
            self.portfolio.get_var_95()
            if hasattr(self.portfolio, "get_var_95")
            else 0.0
        )
        drawdown = (
            self.portfolio.get_max_drawdown()
            if hasattr(self.portfolio, "get_max_drawdown")
            else 0.0
        )
        cfg = self.risk_config
        alerts = []
        # Check delta
        if abs(delta) > cfg["abs_delta"]:
            if not self.risk_alert_state["abs_delta"]:
                alerts.append(
                    f"⚠️ *Delta Alert*: |Δ| = `{delta:.4f}` BTC exceeds threshold `{cfg['abs_delta']}` BTC."
                )
                self.risk_alert_state["abs_delta"] = True
        else:
            self.risk_alert_state["abs_delta"] = False
        # Check VaR
        if var_95 > cfg["var_95"]:
            if not self.risk_alert_state["var_95"]:
                alerts.append(
                    f"⚠️ *VaR Alert*: 95% VaR = `${var_95:,.2f}` exceeds threshold `${cfg['var_95']:,.2f}`."
                )
                self.risk_alert_state["var_95"] = True
        else:
            self.risk_alert_state["var_95"] = False
        # Check drawdown
        if drawdown > cfg["max_drawdown"]:
            if not self.risk_alert_state["max_drawdown"]:
                alerts.append(
                    f"⚠️ *Drawdown Alert*: Max Drawdown = `{drawdown:.2%}` exceeds threshold `{cfg['max_drawdown']:.2%}`."
                )
                self.risk_alert_state["max_drawdown"] = True
        else:
            self.risk_alert_state["max_drawdown"] = False
        # Send alerts
        if alerts:
            text = "\n".join(alerts)
            try:
                await self.application.bot.send_message(
                    chat_id=user_id, text=text, parse_mode="Markdown"
                )
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"[risk_watcher] Failed to send alert: {e}")

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

        if hasattr(self, "application") and self.application:
            self.application.bot_data["main_user_id"] = user.id
        self.last_user_id = user.id

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
        elif data == "transactions":
            await self.show_transactions(update, context)
        elif data == "risk_config":
            await self.show_risk_config(update, context)
        elif data == "back":
            await self.show_main_menu(update, context)
        else:
            # Handle encoded callback data
            flow, step, callback_data = decode_callback_data(data)
            await self.handle_encoded_callback(
                update, context, flow, step, callback_data
            )

    async def handle_encoded_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        flow: str,
        step: str,
        data: dict,
    ):
        """Handle encoded callback data."""
        if flow == "portfolio":
            await self.handle_portfolio_callback(update, context, step, data)
        elif flow == "hedge":
            await self.handle_hedge_callback(update, context, step, data)
        elif flow == "analytics":
            await self.handle_analytics_callback(update, context, step, data)
        elif flow == "risk_config":
            await self.handle_risk_config_callback(update, context, step, data)
        else:
            await update.callback_query.edit_message_text("Unknown flow.")

    async def handle_portfolio_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, step: str, data: dict
    ):
        """Handle portfolio-related callbacks."""
        if step == "add_spot":
            await self.start_add_spot_wizard(update, context)
        elif step == "remove_spot":
            # Check if we have data (specific position selected) or not (initial menu)
            if data.get("symbol"):
                await self.handle_remove_spot(update, context, data)
            else:
                await self.start_remove_spot_wizard(update, context)
        elif step == "add_future":
            await self.start_add_future_wizard(update, context)
        elif step == "remove_future":
            # Check if we have data (specific position selected) or not (initial menu)
            if data.get("symbol"):
                await self.handle_remove_future(update, context, data)
            else:
                await self.start_remove_future_wizard(update, context)
        elif step == "refresh":
            await self.show_portfolio(update, context)
        elif step == "confirm":
            await self.confirm_portfolio_action(update, context, data)
        elif step == "cancel":
            await self.show_portfolio(update, context)
        elif step == "direction":
            await self.handle_future_direction(update, context, data)
        else:
            await update.callback_query.edit_message_text("Unknown portfolio action.")

    async def start_add_spot_wizard(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start the Add Spot wizard."""
        query = update.callback_query

        # Store wizard state
        context.user_data["wizard"] = {
            "type": "add_spot",
            "step": "quantity",
            "data": {
                "symbol": "BTC-USDT-SPOT",
                "instrument_type": "spot",
                "exchange": "OKX",
            },
        }

        text = (
            "➕ *Add Spot Position*\n\n"
            "Symbol: BTC-USDT\n"
            "Please enter the quantity (in BTC):\n\n"
            "Example: `5.0` for 5 BTC"
        )

        await query.edit_message_text(
            text, reply_markup=get_back_button(), parse_mode="Markdown"
        )

    async def start_add_future_wizard(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start the Add Future wizard."""
        query = update.callback_query

        # Store wizard state
        context.user_data["wizard"] = {
            "type": "add_future",
            "step": "direction",
            "data": {
                "symbol": "BTC-USDT-PERP",
                "instrument_type": "perpetual",
                "exchange": "OKX",
                "direction": "long",  # Add default direction
            },
        }

        text = (
            "➕ *Add Future Position*\n\n"
            "Symbol: BTC-USDT-PERP\n"
            f"Direction: {'🟢 LONG' if context.user_data['wizard']['data']['direction'] == 'long' else '🔴 SHORT'}\n"
            "Please enter the quantity (in BTC):\n\n"
            "Example: `5.0` for 5 BTC"
        )

        keyboard = [
            [
                {
                    "text": "🟢 Long",
                    "callback_data": encode_callback_data(
                        "portfolio", "direction", {"direction": "long"}
                    ),
                },
                {
                    "text": "🔴 Short",
                    "callback_data": encode_callback_data(
                        "portfolio", "direction", {"direction": "short"}
                    ),
                },
            ],
            [{"text": "🔙 Back", "callback_data": "back"}],
        ]

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def start_remove_spot_wizard(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start the Remove Spot wizard."""
        query = update.callback_query

        # Check if we have spot positions
        spot_positions = [
            pos
            for pos in self.portfolio.positions.values()
            if pos.instrument_type == "spot"
        ]

        if not spot_positions:
            text = (
                "❌ *No Spot Positions*\n\nYou don't have any spot positions to remove."
            )
            await query.edit_message_text(
                text, reply_markup=get_back_button(), parse_mode="Markdown"
            )
            return

        # Show position list
        text = "➖ *Remove Spot Position*\n\nSelect position to remove:\n\n"
        keyboard = []

        for i, position in enumerate(spot_positions):
            direction = "🟢 LONG" if position.is_long else "🔴 SHORT"
            text += f"{i+1}. {position.symbol}: {position.qty:+.4f} @ ${position.avg_px:.2f} ({direction})\n"
            keyboard.append(
                [
                    {
                        "text": f"Remove {position.symbol}",
                        "callback_data": encode_callback_data(
                            "portfolio", "remove_spot", {"symbol": position.symbol}
                        ),
                    }
                ]
            )

        keyboard.append([{"text": "🔙 Back", "callback_data": "back"}])

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Add timestamp to prevent "Message is not modified" error
        text += f"\n_Updated at {datetime.now().strftime('%H:%M:%S')}_"

        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def start_remove_future_wizard(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start the Remove Future wizard."""
        query = update.callback_query

        # Check if we have future positions
        future_positions = [
            pos
            for pos in self.portfolio.positions.values()
            if pos.instrument_type == "perpetual"
        ]

        if not future_positions:
            text = "❌ *No Future Positions*\n\nYou don't have any future positions to remove."
            await query.edit_message_text(
                text, reply_markup=get_back_button(), parse_mode="Markdown"
            )
            return

        # Show position list
        text = "➖ *Remove Future Position*\n\nSelect position to remove:\n\n"
        keyboard = []

        for i, position in enumerate(future_positions):
            direction = "🟢 LONG" if position.is_long else "🔴 SHORT"
            text += f"{i+1}. {position.symbol}: {position.qty:+.4f} @ ${position.avg_px:.2f} ({direction})\n"
            keyboard.append(
                [
                    {
                        "text": f"Remove {position.symbol}",
                        "callback_data": encode_callback_data(
                            "portfolio", "remove_future", {"symbol": position.symbol}
                        ),
                    }
                ]
            )

        keyboard.append([{"text": "🔙 Back", "callback_data": "back"}])

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Add timestamp to prevent "Message is not modified" error
        text += f"\n_Updated at {datetime.now().strftime('%H:%M:%S')}_"

        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def confirm_portfolio_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict
    ):
        """Confirm a portfolio action."""
        query = update.callback_query

        trade = context.user_data.get("pending_trade")
        if not trade:
            await query.edit_message_text(
                "No pending trade found.",
                reply_markup=get_back_button(),
                parse_mode="Markdown",
            )
            return
        action_type = trade.get("action_type")
        symbol = trade.get("symbol")
        qty = trade.get("qty")
        price = trade.get("price")
        if action_type == "add":
            self.portfolio.update_fill(
                symbol, qty, price, trade.get("instrument_type"), trade.get("exchange")
            )
            text = f"✅ *Position Added*\n\n{symbol}: {qty:+.4f} @ ${price:.2f}"
        elif action_type == "remove":
            position = self.portfolio.get_position(symbol)
            if position:
                self.portfolio.update_fill(
                    symbol,
                    -position.qty,
                    price,
                    position.instrument_type,
                    position.exchange,
                )
                text = f"✅ *Position Removed*\n\n{symbol}: {position.qty:+.4f} @ ${position.avg_px:.2f}"
            else:
                text = "❌ Position not found."
        else:
            text = "❌ Unknown action."
        # Clear pending trade after confirmation
        context.user_data.pop("pending_trade", None)

        await query.edit_message_text(
            text, reply_markup=get_back_button(), parse_mode="Markdown"
        )

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the main menu."""
        query = update.callback_query
        welcome_text = "🤖 Spot Hedger Bot\n\nSelect an option:"

        await query.edit_message_text(welcome_text, reply_markup=get_main_menu())

    async def show_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show portfolio overview."""
        query = update.callback_query

        # Get portfolio snapshot
        snapshot = self.portfolio.snapshot()
        total_delta = self.portfolio.get_total_delta()

        # Calculate real-time P&L
        total_pnl = 0.0
        positions_text = ""

        for position in self.portfolio.positions.values():
            try:
                direction = "🟢 LONG" if position.is_long else "🔴 SHORT"

                # Handle different instrument types
                if position.instrument_type == "option":
                    # For options, use the stored price and show option-specific info
                    option_price = position.avg_px
                    # Try to get current option price from Deribit
                    try:
                        from ..exchanges.deribit_options import deribit_options

                        async with deribit_options as options:
                            ticker = await options.get_option_ticker(position.symbol)
                            if ticker and ticker.last_price > 0:
                                current_price = ticker.last_price
                                unrealized_pnl = (
                                    current_price - option_price
                                ) * position.qty
                                total_pnl += unrealized_pnl
                                pnl_color = "🟢" if unrealized_pnl >= 0 else "🔴"
                                positions_text += (
                                    f"• {position.symbol}: {position.qty:+.4f} @ ${option_price:.4f} "
                                    f"({direction})\n"
                                    f"  Current: ${current_price:.4f} | P&L: {pnl_color}${unrealized_pnl:+.2f}\n\n"
                                )
                            else:
                                # Fallback for options without current price
                                positions_text += (
                                    f"• {position.symbol}: {position.qty:+.4f} @ ${option_price:.4f} "
                                    f"({direction})\n"
                                    f"  Option Price: ${option_price:.4f}\n\n"
                                )
                    except Exception as e:
                        logger.warning(
                            f"Failed to get option price for {position.symbol}: {e}"
                        )
                        positions_text += (
                            f"• {position.symbol}: {position.qty:+.4f} @ ${option_price:.4f} "
                            f"({direction})\n"
                            f"  Option Price: ${option_price:.4f}\n\n"
                        )
                else:
                    # For spot/futures, get current price normally
                    current_price = await self.get_current_price(position.symbol)
                    unrealized_pnl = (current_price - position.avg_px) * position.qty
                    total_pnl += unrealized_pnl

                    pnl_color = "🟢" if unrealized_pnl >= 0 else "🔴"
                    positions_text += (
                        f"• {position.symbol}: {position.qty:+.4f} @ ${position.avg_px:.2f} "
                        f"({direction})\n"
                        f"  Current: ${current_price:.2f} | P&L: {pnl_color}${unrealized_pnl:+.2f}\n\n"
                    )
            except Exception as e:
                logger.warning(f"Failed to get price for {position.symbol}: {e}")
                direction = "🟢 LONG" if position.is_long else "🔴 SHORT"
                positions_text += (
                    f"• {position.symbol}: {position.qty:+.4f} @ ${position.avg_px:.2f} "
                    f"({direction})\n\n"
                )

        # Format portfolio text
        if not self.portfolio.positions:
            portfolio_text = "📊 *Portfolio Overview*\n\nNo positions"
        else:
            pnl_color = "🟢" if total_pnl >= 0 else "🔴"
            portfolio_text = (
                f"📊 *Portfolio Overview*\n\n"
                f"Total Delta: {total_delta:+.4f} BTC\n"
                f"Total Notional: ${snapshot['total_notional']:,.2f}\n"
                f"Unrealized P&L: {pnl_color}${total_pnl:+.2f}\n\n"
                f"*Positions:*\n{positions_text}"
            )

        # Add timestamp
        portfolio_text += f"\n_Updated at {datetime.now().strftime('%H:%M:%S')}_"

        await query.edit_message_text(
            portfolio_text, reply_markup=get_portfolio_menu(), parse_mode="Markdown"
        )

    async def show_hedge_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show hedge menu."""
        query = update.callback_query

        # Get current portfolio delta
        total_delta = self.portfolio.get_total_delta()

        # Get hedge recommendations with options
        try:
            # Get option chain for hedging
            from ..exchanges.deribit_options import deribit_options

            option_chain = await deribit_options.get_option_chain()

            recommendations = await hedge_service.calculate_hedge_recommendations(
                total_delta, self.portfolio.positions, option_chain
            )
        except Exception as e:
            logger.error(f"Error getting options data: {e}")
            # Fallback to perpetual-only recommendations
            recommendations = await hedge_service.calculate_hedge_recommendations(
                total_delta, self.portfolio.positions
            )

        # Calculate hedge recommendations
        hedge_text = (
            f"🛡️ *Hedge Menu*\n\n" f"Current Portfolio Delta: {total_delta:+.4f} BTC\n\n"
        )

        if abs(total_delta) < 0.01:
            hedge_text += "✅ Portfolio is delta-neutral (no hedge needed)"
        elif total_delta > 0:
            hedge_text += (
                f"📉 *Hedge Recommendation:*\n"
                f"• Short {abs(total_delta):.4f} BTC to neutralize\n"
                f"• Options: Protective Put or Short Future\n"
                f"• Perp Δ-Neutral: Short {abs(total_delta):.4f} BTC-PERP"
            )
        else:
            hedge_text += (
                f"📈 *Hedge Recommendation:*\n"
                f"• Long {abs(total_delta):.4f} BTC to neutralize\n"
                f"• Options: Covered Call or Long Future\n"
                f"• Perp Δ-Neutral: Long {abs(total_delta):.4f} BTC-PERP"
            )

        # Add options availability status
        if len(recommendations) > 1:  # More than just perpetual
            hedge_text += (
                "\n\n✅ *Options Available:* Real-time options pricing enabled"
            )
        else:
            hedge_text += "\n\n⚠️ *Options Status:* Using perpetual-only hedging"

        await query.edit_message_text(
            hedge_text, reply_markup=get_hedge_menu(), parse_mode="Markdown"
        )

    async def show_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show analytics summary and drill-down options."""
        query = update.callback_query
        from loguru import logger

        try:
            logger.info("show_analytics called")
            # Gather analytics using portfolio methods
            pnl_realized = self.portfolio.get_realized_pnl()
            pnl_unrealized = self.portfolio.get_unrealized_pnl()
            delta = self.portfolio.get_total_delta()
            var_95 = self.portfolio.get_var_95()
            drawdown = self.portfolio.get_max_drawdown()

            # Hedge effectiveness: % delta hedged
            gross_delta = abs(delta)
            spot_delta = delta  # For now, use total delta
            hedge_delta = 0.0  # This would be calculated from hedge positions
            effectiveness = (
                (abs(hedge_delta) / gross_delta * 100) if gross_delta > 0 else 0.0
            )

            # Option Greeks summary
            greeks = self.portfolio.get_greeks_summary()
            greeks_text = ""
            if greeks:
                greeks_text = "\n".join(
                    [f"• {k.capitalize()}: `{v:+.4f}`" for k, v in greeks.items()]
                )

            # Compose analytics summary
            text = (
                f"📊 *Portfolio Analytics*\n\n"
                f"• Realized P&L: `${pnl_realized:,.2f}`\n"
                f"• Unrealized P&L: `${pnl_unrealized:,.2f}`\n"
                f"• Current Delta: `{delta:+.4f}` BTC\n"
                f"• 95% VaR: `${var_95:,.2f}`\n"
                f"• Max Drawdown: `{drawdown:.2%}`\n"
                f"• Hedge Effectiveness: `{effectiveness:.1f}%`\n"
            )
            if greeks_text:
                text += f"\n*Option Greeks:*\n{greeks_text}"

            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            # Create analytics menu with drill-down options
            keyboard = [
                [
                    InlineKeyboardButton(
                        "📊 By Position",
                        callback_data=encode_callback_data("analytics", "by_position"),
                    ),
                    InlineKeyboardButton(
                        "🛡️ By Hedge",
                        callback_data=encode_callback_data("analytics", "by_hedge"),
                    ),
                ],
                [InlineKeyboardButton("🔙 Back", callback_data="back")],
            ]
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error in show_analytics: {e}")
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            await query.edit_message_text(
                "❌ Failed to load analytics. Please try again later.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
                ),
                parse_mode="Markdown",
            )

    async def show_transactions(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show transaction history."""
        query = update.callback_query

        # Get transaction summary
        summary = self.portfolio.get_transaction_summary()
        transactions = self.portfolio.get_transaction_history(limit=20)  # Show last 20

        # Compose transaction summary
        text = f"📋 *Transaction History*\n\n"

        if not transactions:
            text += "No transactions recorded yet."
        else:
            # Summary statistics
            total_pnl = summary["total_pnl"]
            total_volume = summary["total_volume"]
            pnl_color = "🟢" if total_pnl >= 0 else "🔴"

            text += (
                f"📊 *Summary:*\n"
                f"• Total Transactions: {summary['total_transactions']}\n"
                f"• Total Volume: ${total_volume:,.2f}\n"
                f"• Total P&L: {pnl_color}${total_pnl:+,.2f}\n\n"
            )

            # Recent transactions
            text += "📝 *Recent Transactions:*\n"
            for i, tx in enumerate(transactions[:10], 1):  # Show last 10
                # Format timestamp
                timestamp = tx.timestamp.strftime("%m/%d %H:%M")

                # Format quantity and price
                qty_str = (
                    f"{tx.qty:+.4f}" if abs(tx.qty) >= 0.0001 else f"{tx.qty:+.6f}"
                )
                price_str = f"${tx.price:.2f}"

                # Transaction type emoji
                type_emoji = {
                    "buy": "🟢",
                    "sell": "🔴",
                    "add": "➕",
                    "remove": "➖",
                    "hedge": "🛡️",
                }.get(tx.transaction_type, "📊")

                # P&L if available
                pnl_str = ""
                if tx.pnl is not None:
                    pnl_color = "🟢" if tx.pnl >= 0 else "🔴"
                    pnl_str = f" | P&L: {pnl_color}${tx.pnl:+,.2f}"

                text += (
                    f"{i}. {type_emoji} {tx.symbol} {qty_str} @ {price_str}"
                    f"{pnl_str}\n"
                    f"   {timestamp} | {tx.transaction_type.title()}\n\n"
                )

            if len(transactions) > 10:
                text += f"... and {len(transactions) - 10} more transactions\n\n"

        # Add timestamp
        text += f"_Updated at {datetime.now().strftime('%H:%M:%S')}_"

        # Create back button
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]

        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def handle_analytics_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, step: str, data: dict
    ):
        query = update.callback_query
        if step == "by_position":
            # List all positions
            positions = list(getattr(self.portfolio, "positions", {}).values())
            # Filter only valid positions (dict/object with symbol)
            valid_positions = []
            for pos in positions:
                if isinstance(pos, str):
                    continue
                if hasattr(pos, "symbol") or (
                    isinstance(pos, dict) and "symbol" in pos
                ):
                    valid_positions.append(pos)
            if not valid_positions:
                await query.edit_message_text(
                    "No positions.", reply_markup=get_back_button()
                )
                return
            text = "*Positions:*\n\n"
            buttons = []
            for i, pos in enumerate(valid_positions):
                symbol = pos.symbol if hasattr(pos, "symbol") else pos.get("symbol")
                qty = pos.qty if hasattr(pos, "qty") else pos.get("qty")
                text += f"{i+1}. `{symbol}` qty: `{qty}`\n"
                buttons.append(
                    [
                        {
                            "text": f"{symbol}",
                            "callback_data": f"analytics|position_detail|{i}",
                        }
                    ]
                )
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = [
                [InlineKeyboardButton(b["text"], callback_data=b["callback_data"])]
                for b in sum(buttons, [])
            ]
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="analytics")])
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
            )
        elif step == "position_detail":
            if isinstance(data, int):
                idx = data
            elif isinstance(data, str):
                try:
                    idx = int(data)
                except Exception:
                    idx = 0
            elif isinstance(data, dict):
                idx = int(data.get("idx", 0))
            else:
                idx = 0
            positions = list(getattr(self.portfolio, "positions", {}).values())
            # Filter only valid positions (dict/object with symbol)
            valid_positions = []
            for pos in positions:
                if isinstance(pos, str):
                    continue
                if hasattr(pos, "symbol") or (
                    isinstance(pos, dict) and "symbol" in pos
                ):
                    valid_positions.append(pos)
            if idx < 0 or idx >= len(valid_positions):
                await query.edit_message_text(
                    "Invalid position.", reply_markup=get_back_button()
                )
                return
            pos = valid_positions[idx]
            symbol = pos.symbol if hasattr(pos, "symbol") else pos.get("symbol")
            qty = pos.qty if hasattr(pos, "qty") else pos.get("qty")
            avg_px = pos.avg_px if hasattr(pos, "avg_px") else pos.get("avg_px")
            instrument_type = (
                pos.instrument_type
                if hasattr(pos, "instrument_type")
                else pos.get("instrument_type")
            )
            current_price = await self.get_current_price(symbol)
            pnl = (current_price - avg_px) * qty
            text = (
                f"*Position Detail*\n\n"
                f"Symbol: `{symbol}`\n"
                f"Qty: `{qty}`\n"
                f"Avg Px: `${avg_px}`\n"
                f"Current Px: `${current_price}`\n"
                f"Unrealized P&L: `${pnl:,.2f}`\n"
                f"Type: `{instrument_type}`\n"
            )
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⬅️ Back", callback_data="analytics|by_position|{}"
                    )
                ]
            ]
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
            )
        elif step == "by_hedge":
            hedges = getattr(self, "active_hedges", [])
            if not hedges:
                await query.edit_message_text(
                    "No active hedges.", reply_markup=get_back_button()
                )
                return
            text = "*Active Hedges:*\n\n"
            buttons = []
            for i, hedge in enumerate(hedges):
                desc = hedge.get("desc", hedge.get("symbol", f"Hedge {i+1}"))
                text += f"{i+1}. {desc}\n"
                buttons.append(
                    [
                        {
                            "text": f"{desc}",
                            "callback_data": f"analytics|hedge_detail|{i}",
                        }
                    ]
                )
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = [
                [InlineKeyboardButton(b["text"], callback_data=b["callback_data"])]
                for b in sum(buttons, [])
            ]
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="analytics")])
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
            )
        elif step == "hedge_detail":
            if isinstance(data, int):
                idx = data
            elif isinstance(data, str):
                try:
                    idx = int(data)
                except Exception:
                    idx = 0
            elif isinstance(data, dict):
                idx = int(data.get("idx", 0))
            else:
                idx = 0
            hedges = getattr(self, "active_hedges", [])
            if idx < 0 or idx >= len(hedges):
                await query.edit_message_text(
                    "Invalid hedge.", reply_markup=get_back_button()
                )
                return
            hedge = hedges[idx]
            desc = hedge.get("desc", hedge.get("symbol", f"Hedge {idx+1}"))
            price = hedge.get("price", 0.0)
            cost = hedge.get("cost", 0.0)
            qty = hedge.get("qty", 0.0)
            text = (
                f"*Hedge Detail*\n\n"
                f"Desc: `{desc}`\n"
                f"Qty: `{qty}`\n"
                f"Price: `${price}`\n"
                f"Cost: `${cost}`\n"
            )
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = [
                [InlineKeyboardButton("⬅️ Back", callback_data="analytics|by_hedge|{}")]
            ]
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                "Unknown analytics action.", reply_markup=get_back_button()
            )

    async def show_risk_config(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show the risk configuration menu with current thresholds and edit buttons."""
        query = update.callback_query
        cfg = self.risk_config
        text = (
            f"⚙️ *Risk Configuration*\n\n"
            f"• Absolute Delta (|Δ|): `{cfg['abs_delta']}` BTC  [✏️ Edit](delta)\n"
            f"• 95% VaR: `${cfg['var_95']:.2f}` USD  [✏️ Edit](var)\n"
            f"• Max Drawdown: `{cfg['max_drawdown']:.2%}`  [✏️ Edit](drawdown)\n\n"
            f"Select a metric to edit, or go back."
        )
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = [
            [
                InlineKeyboardButton(
                    "✏️ Edit |Δ|", callback_data="risk_config|edit|delta"
                )
            ],
            [InlineKeyboardButton("✏️ Edit VaR", callback_data="risk_config|edit|var")],
            [
                InlineKeyboardButton(
                    "✏️ Edit Drawdown", callback_data="risk_config|edit|drawdown"
                )
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="back")],
        ]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    async def handle_hedge_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, step: str, data: dict
    ):
        """Handle hedge-related callbacks."""
        logger.info(f"[handle_hedge_callback] step={step} data={data}")
        # Parse compact callback data for select flow
        if step == "protective_put_select_strike" and isinstance(data, str):
            data = {"expiry": data}
        elif step == "protective_put_select_confirm" and isinstance(data, str):
            # Support both 'expiry|strike' and 'expiry' only
            parts = data.split("|")
            if len(parts) == 2:
                data = {"expiry": parts[0], "strike": parts[1]}
            elif len(parts) == 1:
                data = {"expiry": parts[0]}
            else:
                # If data is already a dict or something else, leave as is
                pass
        elif step == "covered_call_select_strike" and isinstance(data, str):
            data = {"expiry": data}
        elif step == "covered_call_select_confirm" and isinstance(data, str):
            # Support both 'expiry|strike' and 'expiry' only
            parts = data.split("|")
            if len(parts) == 2:
                data = {"expiry": parts[0], "strike": parts[1]}
            elif len(parts) == 1:
                data = {"expiry": parts[0]}
            else:
                # If data is already a dict or something else, leave as is
                pass
        elif step == "collar_select_strike" and isinstance(data, str):
            data = {"expiry": data}
        elif step == "collar_select_confirm" and isinstance(data, str):
            # Support 'expiry|option_type|strike' format
            parts = data.split("|")
            if len(parts) == 3:
                data = {"expiry": parts[0], "option_type": parts[1], "strike": parts[2]}
            elif len(parts) == 2:
                data = {"expiry": parts[0], "strike": parts[1]}
            elif len(parts) == 1:
                data = {"expiry": parts[0]}
            else:
                # If data is already a dict or something else, leave as is
                pass
        elif step == "remove_hedge_confirm":
            if isinstance(data, str):
                data = {"idx": int(data)}
            elif isinstance(data, int):
                data = {"idx": data}
        import json

        # Parse data if it's a stringified dict
        if isinstance(data, str) and (data.startswith("{") and data.endswith("}")):
            try:
                data = json.loads(data.replace("'", '"'))
            except Exception:
                pass
        if step == "perp_delta_neutral":
            await self.start_perp_delta_neutral_hedge(update, context)
        elif step == "protective_put":
            await self.start_protective_put_hedge(update, context)
        elif step == "protective_put_auto":
            await self.protective_put_auto_flow(update, context)
        elif step == "protective_put_select":
            await self.protective_put_select_expiry(update, context)
        elif step == "protective_put_select_strike":
            await self.protective_put_select_strike(update, context, data)
        elif step == "protective_put_select_confirm":
            await self.protective_put_select_confirm(update, context, data)
        elif step == "covered_call":
            await self.start_covered_call_hedge(update, context)
        elif step == "covered_call_auto":
            await self.covered_call_auto_flow(update, context)
        elif step == "covered_call_select":
            await self.covered_call_select_expiry(update, context)
        elif step == "covered_call_select_strike":
            await self.covered_call_select_strike(update, context, data)
        elif step == "covered_call_select_confirm":
            await self.covered_call_select_confirm(update, context, data)
        elif step == "collar":
            await self.start_collar_hedge(update, context)
        elif step == "collar_auto":
            await self.collar_auto_flow(update, context)
        elif step == "collar_select":
            await self.collar_select_expiry(update, context)
        elif step == "collar_select_strike":
            await self.collar_select_strike(update, context, data)
        elif step == "collar_select_confirm":
            await self.collar_select_confirm(update, context, data)
        elif step == "show_collar_summary":
            await self.show_collar_summary(update, context)
        elif step == "dynamic_hedge":
            await self.start_dynamic_hedge(update, context)
        elif step == "dynamic_hedge_auto":
            await self.dynamic_hedge_auto_flow(update, context)

        elif step == "view_hedges":
            await self.show_active_hedges(update, context)
        elif step == "remove_hedge":
            await self.start_remove_hedge(update, context)
        elif step == "remove_hedge_confirm":
            await self.remove_hedge_confirm(update, context, data)
        elif step == "confirm":
            await self.confirm_hedge_action(update, context, data)
        elif step == "cancel":
            await self.show_hedge_menu(update, context)
        else:
            await update.callback_query.edit_message_text(
                "Unknown hedge action.", reply_markup=get_back_button()
            )

    async def start_perp_delta_neutral_hedge(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start perpetual delta-neutral hedge wizard."""
        query = update.callback_query

        total_delta = self.portfolio.get_total_delta()

        if abs(total_delta) < 0.01:
            text = "✅ *Portfolio Already Delta-Neutral*\n\nNo hedge needed - your portfolio is already delta-neutral."
            await query.edit_message_text(
                text, reply_markup=get_back_button(), parse_mode="Markdown"
            )
            return

        # Calculate hedge quantity (opposite of current delta)
        hedge_qty = -total_delta
        direction = "SHORT" if hedge_qty < 0 else "LONG"

        # Get current price
        current_price = await self.get_current_price("BTC-USDT-PERP")

        # Calculate costs
        costs = costing_service.calculate_total_cost(
            hedge_qty, current_price, "OKX", "perpetual"
        )

        text = (
            f"⚖️ *Perpetual Delta-Neutral Hedge*\n\n"
            f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
            f"Hedge Required: {abs(hedge_qty):.4f} BTC {direction}\n"
            f"Price: ${current_price:.2f}\n"
            f"Notional: ${abs(hedge_qty * current_price):,.2f}\n\n"
            f"{costing_service.get_cost_summary(hedge_qty, current_price, 'OKX', 'perpetual')}\n\n"
            f"This will make your portfolio delta-neutral."
        )

        # Store hedge data
        context.user_data["pending_hedge"] = {
            "type": "perp_delta_neutral",
            "symbol": "BTC-USDT-PERP",
            "qty": hedge_qty,
            "price": current_price,
            "instrument_type": "perpetual",
            "exchange": "OKX",
            "target_delta": 0.0,
        }

        await query.edit_message_text(
            text, reply_markup=get_confirmation_buttons("hedge"), parse_mode="Markdown"
        )

    async def start_protective_put_hedge(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start protective put hedge wizard."""
        query = update.callback_query

        total_delta = self.portfolio.get_total_delta()

        if total_delta <= 0:
            text = "❌ *No Protective Put Needed*\n\nProtective puts are for long positions only."
            await query.edit_message_text(
                text, reply_markup=get_back_button(), parse_mode="Markdown"
            )
            return

        # Step 1: Ask user to choose Select or Automatic
        logger = logging.getLogger(__name__)
        logger.info("[protective_put] Showing Select/Automatic options to user")
        text = (
            f"🛡️ *Protective Put Hedge*\n\n"
            f"Current Portfolio Delta: {total_delta:+.4f} BTC\n\n"
            f"How would you like to select your put option?"
        )
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔍 Select", callback_data="hedge|protective_put_select|{}"
                    ),
                    InlineKeyboardButton(
                        "⚡ Automatic", callback_data="hedge|protective_put_auto|{}"
                    ),
                ],
                [InlineKeyboardButton("⬅️ Back", callback_data="back")],
            ]
        )
        await query.edit_message_text(
            text, reply_markup=keyboard, parse_mode="Markdown"
        )

    async def protective_put_auto_flow(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Automatic protective put: current logic (fast, robust)."""
        query = update.callback_query
        total_delta = self.portfolio.get_total_delta()
        logger.info("[protective_put_auto_flow] Entered function")
        try:
            from ..exchanges.deribit_options import deribit_options

            logger.info("[protective_put_auto_flow] Before async with deribit_options")
            async with deribit_options:
                logger.info(
                    "[protective_put_auto_flow] Inside async with deribit_options"
                )
                instruments = await deribit_options.get_instruments()
                put_instruments = [
                    i
                    for i in instruments
                    if i.symbol.startswith("BTC")
                    and i.instrument_type == "option"
                    and "-P" in i.symbol
                ]
                logger.info(
                    f"[protective_put_auto_flow] Found {len(put_instruments)} put instruments"
                )
                if not put_instruments:
                    text = (
                        f"🛡️ *Protective Put Hedge*\n\n"
                        f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                        f"❌ No put options available for hedging.\n\n"
                        f"Try perpetual delta-neutral hedge instead."
                    )
                    await query.edit_message_text(
                        text, reply_markup=get_back_button(), parse_mode="Markdown"
                    )
                    logger.info(
                        "[protective_put_auto_flow] No put options, sent error message"
                    )
                    return
                current_price = await self.get_current_price("BTC-USDT-PERP")
                logger.info(
                    f"[protective_put_auto_flow] Got current price: {current_price}"
                )
                # Find 10 closest puts to ATM
                closest_puts = sorted(
                    put_instruments,
                    key=lambda x: abs(
                        x.symbol.split("-")[2]
                        and float(x.symbol.split("-")[2]) - current_price
                    ),
                )[:10]
                # Fetch tickers for these
                put_options = []
                for inst in closest_puts:
                    ticker = await deribit_options.get_option_ticker(inst.symbol)
                    if ticker:
                        put_options.append(ticker)
                logger.info(
                    f"[protective_put_auto_flow] Got {len(put_options)} put tickers"
                )
                if not put_options:
                    text = (
                        f"🛡️ *Protective Put Hedge*\n\n"
                        f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                        f"❌ No put options with price data.\n\n"
                        f"Try perpetual delta-neutral hedge instead."
                    )
                    await query.edit_message_text(
                        text, reply_markup=get_back_button(), parse_mode="Markdown"
                    )
                    logger.info(
                        "[protective_put_auto_flow] No put tickers, sent error message"
                    )
                    return
                best_put = min(put_options, key=lambda x: abs(x.strike - current_price))
                target_delta = total_delta * 0.5
                hedge_delta = total_delta - target_delta
                put_quantity = hedge_delta / abs(best_put.delta)
                # Use last_price if mid_price is 0 (when bid/ask are 0)
                price = (
                    best_put.mid_price
                    if best_put.mid_price > 0
                    else best_put.last_price
                )
                # If both are 0, use a fallback price based on strike
                if price <= 0:
                    # Use a simple estimate: 5% of strike for puts
                    price = best_put.strike * 0.05
                put_cost = put_quantity * price
                logger.info(
                    f"[protective_put_auto_flow] Price calculation: mid_price={best_put.mid_price}, last_price={best_put.last_price}, final_price={price}, cost={put_cost}"
                )
                risk_reduction = hedge_delta * current_price * 0.15
                text = (
                    f"🛡️ *Protective Put Hedge*\n\n"
                    f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                    f"Target Delta: {target_delta:+.4f} BTC\n\n"
                    f"*Recommended Put:*\n"
                    f"• Symbol: {best_put.symbol}\n"
                    f"• Strike: ${best_put.strike:,.0f}\n"
                    f"• Expiry: {best_put.expiry.strftime('%Y-%m-%d')}\n"
                    f"• Quantity: {put_quantity:.4f} contracts\n"
                    f"• Price: ${price:.2f}\n"
                    f"• Cost: ${put_cost:,.2f}\n"
                    f"• Risk Reduction: ${risk_reduction:,.2f}\n\n"
                    f"*Greeks:*\n"
                    f"• Delta: {best_put.delta:.4f}\n"
                    f"• Gamma: {best_put.gamma:.6f}\n"
                    f"• Theta: {best_put.theta:.4f}\n"
                    f"• Vega: {best_put.vega:.4f}\n"
                    f"• IV: {best_put.implied_volatility:.1%}\n\n"
                    f"This will protect your long position from downside risk."
                )
                context.user_data["pending_hedge"] = {
                    "type": "protective_put",
                    "symbol": best_put.symbol,
                    "qty": put_quantity,
                    "price": price,
                    "cost": put_cost,
                    "instrument_type": "option",
                    "exchange": "Deribit",
                    "target_delta": target_delta,
                    "option_contract": best_put,
                }
                await query.edit_message_text(
                    text,
                    reply_markup=get_confirmation_buttons("hedge"),
                    parse_mode="Markdown",
                )
                logger.info("[protective_put_auto_flow] Sent confirmation message")
        except Exception as e:
            logger.error(f"[protective_put_auto_flow] Exception: {e}")
            text = (
                f"🛡️ *Protective Put Hedge*\n\n"
                f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                f"❌ Error loading options data: {str(e)}\n\n"
                f"Try perpetual delta-neutral hedge instead."
            )
            await query.edit_message_text(
                text, reply_markup=get_back_button(), parse_mode="Markdown"
            )

    async def protective_put_select_expiry(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Step 1: Let user select expiry for protective put."""
        logger = logging.getLogger(__name__)
        logger.info(
            "[protective_put_select] User chose 'Select' - showing expiry options"
        )
        query = update.callback_query
        from ..exchanges.deribit_options import deribit_options

        async with deribit_options:
            instruments = await deribit_options.get_instruments()
            put_instruments = [
                i
                for i in instruments
                if i.symbol.startswith("BTC")
                and i.instrument_type == "option"
                and "-P" in i.symbol
            ]
            # Extract unique expiries
            expiries = sorted(
                list(set(i.symbol.split("-")[1] for i in put_instruments))
            )
            logger.info(
                f"[protective_put_select_expiry] Available expiries: {expiries}"
            )
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = [
                [
                    InlineKeyboardButton(
                        exp,
                        callback_data=encode_callback_data(
                            "hedge", "protective_put_select_strike", {"expiry": exp}
                        ),
                    )
                ]
                for exp in expiries[:10]
            ]
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "⬅️ Back", callback_data="hedge|protective_put|{}"
                    )
                ]
            )
            text = "Select expiry for your protective put:"
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def protective_put_select_strike(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict
    ):
        """Step 2: Let user select strike for chosen expiry."""
        logger = logging.getLogger(__name__)
        query = update.callback_query
        expiry = data.get("expiry")
        logger.info(f"[protective_put_select_strike] Entered with expiry={expiry}")
        from ..exchanges.deribit_options import deribit_options

        try:
            async with deribit_options:
                instruments = await deribit_options.get_instruments()
                logger.info(
                    f"[protective_put_select_strike] Got {len(instruments)} instruments"
                )
                put_instruments = [
                    i
                    for i in instruments
                    if i.symbol.startswith("BTC")
                    and i.instrument_type == "option"
                    and "-P" in i.symbol
                    and i.symbol.split("-")[1] == expiry
                ]
                logger.info(
                    f"[protective_put_select_strike] Found {len(put_instruments)} puts for expiry {expiry}"
                )
                strikes = sorted(
                    list(set(float(i.symbol.split("-")[2]) for i in put_instruments))
                )
                logger.info(f"[protective_put_select_strike] Strikes: {strikes}")
                print(
                    f"[protective_put_select_strike] Strikes for expiry {expiry}: {strikes}"
                )

                # Get current price to find strikes around it
                current_price = await self.get_current_price("BTC-USDT-PERP")
                logger.info(
                    f"[protective_put_select_strike] Current price: {current_price}"
                )

                # Find strikes 5 below and 5 above current price
                strikes_around_current = []
                for strike in strikes:
                    if len(strikes_around_current) >= 10:  # Max 10 strikes
                        break
                    if (
                        strike <= current_price + 5000
                        and strike >= current_price - 5000
                    ):
                        strikes_around_current.append(strike)

                # If we don't have enough strikes around current price, add more
                if len(strikes_around_current) < 10:
                    # Add strikes closest to current price
                    strikes_sorted_by_distance = sorted(
                        strikes, key=lambda x: abs(x - current_price)
                    )
                    for strike in strikes_sorted_by_distance:
                        if (
                            strike not in strikes_around_current
                            and len(strikes_around_current) < 10
                        ):
                            strikes_around_current.append(strike)

                # Sort by strike price (lowest to highest)
                strikes_around_current.sort()

                from telegram import InlineKeyboardMarkup, InlineKeyboardButton

                keyboard = [
                    [
                        InlineKeyboardButton(
                            f"${int(strike):,}",
                            callback_data=f"hedge|protective_put_select_confirm|{expiry}|{int(strike)}",
                        )
                    ]
                    for strike in strikes_around_current[:10]
                ]
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "⬅️ Back", callback_data="hedge|protective_put_select|{}"
                        )
                    ]
                )
                text = f"Select strike for expiry {expiry}:"
                await query.edit_message_text(
                    text, reply_markup=InlineKeyboardMarkup(keyboard)
                )
                logger.info(
                    f"[protective_put_select_strike] Sent strike selection message"
                )
        except Exception as e:
            logger.error(f"[protective_put_select_strike] Exception: {e}")
            await query.edit_message_text(
                f"❌ Error: {e}", reply_markup=get_back_button()
            )

    async def protective_put_select_confirm(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict
    ):
        """Step 3: Show summary for selected expiry/strike, ask for confirmation."""
        logger = logging.getLogger(__name__)
        logger.info(f"[protective_put_select_confirm] Entered with data: {data}")
        query = update.callback_query
        expiry = data.get("expiry")
        strike = float(data.get("strike"))
        from ..exchanges.deribit_options import deribit_options

        async with deribit_options:
            instruments = await deribit_options.get_instruments()
            # Find the symbol for this expiry/strike
            symbol = None
            for i in instruments:
                if (
                    i.symbol.startswith("BTC")
                    and i.instrument_type == "option"
                    and "-P" in i.symbol
                ):
                    parts = i.symbol.split("-")
                    if parts[1] == expiry and float(parts[2]) == strike:
                        symbol = i.symbol
                        break
            if not symbol:
                logger.error(
                    f"[protective_put_select_confirm] Option not found for expiry={expiry}, strike={strike}"
                )
                await query.edit_message_text(
                    "❌ Option not found.", reply_markup=get_back_button()
                )
                return
            ticker = await deribit_options.get_option_ticker(symbol)
            if not ticker:
                logger.error(
                    f"[protective_put_select_confirm] Option price unavailable for symbol={symbol}"
                )
                await query.edit_message_text(
                    "❌ Option price unavailable.", reply_markup=get_back_button()
                )
                return
            total_delta = self.portfolio.get_total_delta()
            target_delta = total_delta * 0.5
            hedge_delta = total_delta - target_delta
            put_quantity = (
                hedge_delta / abs(ticker.delta) if abs(ticker.delta) > 0 else 0.0
            )
            # Use last_price if mid_price is 0 (when bid/ask are 0)
            price = ticker.mid_price if ticker.mid_price > 0 else ticker.last_price
            # If both are 0, use a fallback price based on strike
            if price <= 0:
                current_price = await self.get_current_price("BTC-USDT-PERP")
                # Use a simple estimate: 5% of strike for puts
                price = ticker.strike * 0.05
            put_cost = put_quantity * price
            logger.info(
                f"[protective_put_select_confirm] Price calculation: mid_price={ticker.mid_price}, last_price={ticker.last_price}, final_price={price}, cost={put_cost}"
            )
            risk_reduction = (
                hedge_delta * (await self.get_current_price("BTC-USDT-PERP")) * 0.15
            )
            logger.info(
                f"[protective_put_select_confirm] Showing summary for symbol={symbol}, strike={strike}, expiry={expiry}"
            )
            text = (
                f"🛡️ *Protective Put Hedge*\n\n"
                f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                f"Target Delta: {target_delta:+.4f} BTC\n\n"
                f"*Selected Put:*\n"
                f"• Symbol: {ticker.symbol}\n"
                f"• Strike: ${ticker.strike:,.0f}\n"
                f"• Expiry: {ticker.expiry.strftime('%Y-%m-%d')}\n"
                f"• Quantity: {put_quantity:.4f} contracts\n"
                f"• Price: ${price:.2f}\n"
                f"• Cost: ${put_cost:,.2f}\n"
                f"• Risk Reduction: ${risk_reduction:,.2f}\n\n"
                f"*Greeks:*\n"
                f"• Delta: {ticker.delta:.4f}\n"
                f"• Gamma: {ticker.gamma:.6f}\n"
                f"• Theta: {ticker.theta:.4f}\n"
                f"• Vega: {ticker.vega:.4f}\n"
                f"• IV: {ticker.implied_volatility:.1%}\n\n"
                f"This will protect your long position from downside risk."
            )
            context.user_data["pending_hedge"] = {
                "type": "protective_put",
                "symbol": ticker.symbol,
                "qty": put_quantity,
                "price": price,
                "cost": put_cost,
                "instrument_type": "option",
                "exchange": "Deribit",
                "target_delta": target_delta,
                "option_contract": ticker,
            }
            await query.edit_message_text(
                text,
                reply_markup=get_confirmation_buttons("hedge"),
                parse_mode="Markdown",
            )

    async def start_covered_call_hedge(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start covered call hedge wizard."""
        query = update.callback_query

        total_delta = self.portfolio.get_total_delta()

        if total_delta <= 0:
            text = "❌ *No Covered Call Needed*\n\nCovered calls are for long positions only."
            await query.edit_message_text(
                text, reply_markup=get_back_button(), parse_mode="Markdown"
            )
            return

        # Step 1: Ask user to choose Select or Automatic
        logger = logging.getLogger(__name__)
        logger.info("[covered_call] Showing Select/Automatic options to user")
        text = (
            f"📈 *Covered Call Hedge*\n\n"
            f"Current Portfolio Delta: {total_delta:+.4f} BTC\n\n"
            f"How would you like to select your call option?"
        )
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔍 Select", callback_data="hedge|covered_call_select|{}"
                    ),
                    InlineKeyboardButton(
                        "⚡ Automatic", callback_data="hedge|covered_call_auto|{}"
                    ),
                ],
                [InlineKeyboardButton("⬅️ Back", callback_data="back")],
            ]
        )
        await query.edit_message_text(
            text, reply_markup=keyboard, parse_mode="Markdown"
        )

    async def covered_call_auto_flow(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Automatic covered call: current logic (fast, robust)."""
        query = update.callback_query
        total_delta = self.portfolio.get_total_delta()
        logger.info("[covered_call_auto_flow] Entered function")
        try:
            from ..exchanges.deribit_options import deribit_options

            logger.info("[covered_call_auto_flow] Before async with deribit_options")
            async with deribit_options:
                logger.info(
                    "[covered_call_auto_flow] Inside async with deribit_options"
                )
                instruments = await deribit_options.get_instruments()
                call_instruments = [
                    i
                    for i in instruments
                    if i.symbol.startswith("BTC")
                    and i.instrument_type == "option"
                    and "-C" in i.symbol
                ]
                logger.info(
                    f"[covered_call_auto_flow] Found {len(call_instruments)} call instruments"
                )
                if not call_instruments:
                    text = (
                        f"📈 *Covered Call Hedge*\n\n"
                        f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                        f"❌ No call options available for hedging.\n\n"
                        f"Try perpetual delta-neutral hedge instead."
                    )
                    await query.edit_message_text(
                        text, reply_markup=get_back_button(), parse_mode="Markdown"
                    )
                    logger.info(
                        "[covered_call_auto_flow] No call options, sent error message"
                    )
                    return
                current_price = await self.get_current_price("BTC-USDT-PERP")
                logger.info(
                    f"[covered_call_auto_flow] Got current price: {current_price}"
                )
                # Find 10 closest calls to ATM
                closest_calls = sorted(
                    call_instruments,
                    key=lambda x: abs(
                        x.symbol.split("-")[2]
                        and float(x.symbol.split("-")[2]) - current_price
                    ),
                )[:10]
                # Fetch tickers for these
                call_options = []
                for inst in closest_calls:
                    ticker = await deribit_options.get_option_ticker(inst.symbol)
                    if ticker:
                        call_options.append(ticker)
                logger.info(
                    f"[covered_call_auto_flow] Got {len(call_options)} call tickers"
                )
                if not call_options:
                    text = (
                        f"📈 *Covered Call Hedge*\n\n"
                        f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                        f"❌ No call options with price data.\n\n"
                        f"Try perpetual delta-neutral hedge instead."
                    )
                    await query.edit_message_text(
                        text, reply_markup=get_back_button(), parse_mode="Markdown"
                    )
                    logger.info(
                        "[covered_call_auto_flow] No call tickers, sent error message"
                    )
                    return
                # Find slightly OTM calls for income
                otm_calls = [
                    opt for opt in call_options if opt.strike > current_price * 1.05
                ]
                if not otm_calls:
                    # Use closest ATM call if no OTM available
                    best_call = min(
                        call_options, key=lambda x: abs(x.strike - current_price)
                    )
                else:
                    best_call = min(otm_calls, key=lambda x: x.strike)
                target_delta = total_delta * 0.7
                hedge_delta = total_delta - target_delta
                call_quantity = hedge_delta / best_call.delta
                # Use last_price if mid_price is 0 (when bid/ask are 0)
                price = (
                    best_call.mid_price
                    if best_call.mid_price > 0
                    else best_call.last_price
                )
                # If both are 0, use a fallback price based on strike
                if price <= 0:
                    # Use a simple estimate: 3% of strike for calls
                    price = best_call.strike * 0.03
                call_income = call_quantity * price
                logger.info(
                    f"[covered_call_auto_flow] Price calculation: mid_price={best_call.mid_price}, last_price={best_call.last_price}, final_price={price}, income={call_income}"
                )
                risk_reduction = hedge_delta * current_price * 0.08
                text = (
                    f"📈 *Covered Call Hedge*\n\n"
                    f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                    f"Target Delta: {target_delta:+.4f} BTC\n\n"
                    f"*Recommended Call:*\n"
                    f"• Symbol: {best_call.symbol}\n"
                    f"• Strike: ${best_call.strike:,.0f}\n"
                    f"• Expiry: {best_call.expiry.strftime('%Y-%m-%d')}\n"
                    f"• Quantity: {call_quantity:.4f} contracts\n"
                    f"• Price: ${price:.2f}\n"
                    f"• Income: ${call_income:,.2f}\n"
                    f"• Risk Reduction: ${risk_reduction:,.2f}\n\n"
                    f"*Greeks:*\n"
                    f"• Delta: {best_call.delta:.4f}\n"
                    f"• Gamma: {best_call.gamma:.6f}\n"
                    f"• Theta: {best_call.theta:.4f}\n"
                    f"• Vega: {best_call.vega:.4f}\n"
                    f"• IV: {best_call.implied_volatility:.1%}\n\n"
                    f"This will generate income while limiting upside potential."
                )
                context.user_data["pending_hedge"] = {
                    "type": "covered_call",
                    "symbol": best_call.symbol,
                    "qty": call_quantity,
                    "price": price,
                    "cost": call_income,
                    "instrument_type": "option",
                    "exchange": "Deribit",
                    "target_delta": target_delta,
                    "option_contract": best_call,
                }
                await query.edit_message_text(
                    text,
                    reply_markup=get_confirmation_buttons("hedge"),
                    parse_mode="Markdown",
                )
                logger.info("[covered_call_auto_flow] Sent confirmation message")
        except Exception as e:
            logger.error(f"[covered_call_auto_flow] Exception: {e}")
            text = (
                f"📈 *Covered Call Hedge*\n\n"
                f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                f"❌ Error loading options data: {str(e)}\n\n"
                f"Try perpetual delta-neutral hedge instead."
            )
            await query.edit_message_text(
                text, reply_markup=get_back_button(), parse_mode="Markdown"
            )

    async def covered_call_select_expiry(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Step 1: Let user select expiry for covered call."""
        logger = logging.getLogger(__name__)
        logger.info(
            "[covered_call_select] User chose 'Select' - showing expiry options"
        )
        query = update.callback_query
        from ..exchanges.deribit_options import deribit_options

        async with deribit_options:
            instruments = await deribit_options.get_instruments()
            call_instruments = [
                i
                for i in instruments
                if i.symbol.startswith("BTC")
                and i.instrument_type == "option"
                and "-C" in i.symbol
            ]
            # Extract unique expiries
            expiries = sorted(
                list(set(i.symbol.split("-")[1] for i in call_instruments))
            )
            logger.info(f"[covered_call_select_expiry] Available expiries: {expiries}")
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = [
                [
                    InlineKeyboardButton(
                        exp,
                        callback_data=encode_callback_data(
                            "hedge", "covered_call_select_strike", {"expiry": exp}
                        ),
                    )
                ]
                for exp in expiries[:10]
            ]
            keyboard.append(
                [InlineKeyboardButton("⬅️ Back", callback_data="hedge|covered_call|{}")]
            )
            text = "Select expiry for your covered call:"
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def covered_call_select_strike(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict
    ):
        """Step 2: Let user select strike for chosen expiry."""
        logger = logging.getLogger(__name__)
        query = update.callback_query
        expiry = data.get("expiry")
        logger.info(f"[covered_call_select_strike] Entered with expiry={expiry}")
        from ..exchanges.deribit_options import deribit_options

        try:
            async with deribit_options:
                instruments = await deribit_options.get_instruments()
                logger.info(
                    f"[covered_call_select_strike] Got {len(instruments)} instruments"
                )
                call_instruments = [
                    i
                    for i in instruments
                    if i.symbol.startswith("BTC")
                    and i.instrument_type == "option"
                    and "-C" in i.symbol
                    and i.symbol.split("-")[1] == expiry
                ]
                logger.info(
                    f"[covered_call_select_strike] Found {len(call_instruments)} calls for expiry {expiry}"
                )
                strikes = sorted(
                    list(set(float(i.symbol.split("-")[2]) for i in call_instruments))
                )
                logger.info(f"[covered_call_select_strike] Strikes: {strikes}")
                print(
                    f"[covered_call_select_strike] Strikes for expiry {expiry}: {strikes}"
                )

                # Get current price to find strikes around it
                current_price = await self.get_current_price("BTC-USDT-PERP")
                logger.info(
                    f"[covered_call_select_strike] Current price: {current_price}"
                )

                # Find strikes 5 below and 5 above current price
                strikes_around_current = []
                for strike in strikes:
                    if len(strikes_around_current) >= 10:  # Max 10 strikes
                        break
                    if (
                        strike <= current_price + 5000
                        and strike >= current_price - 5000
                    ):
                        strikes_around_current.append(strike)

                # If we don't have enough strikes around current price, add more
                if len(strikes_around_current) < 10:
                    # Add strikes closest to current price
                    strikes_sorted_by_distance = sorted(
                        strikes, key=lambda x: abs(x - current_price)
                    )
                    for strike in strikes_sorted_by_distance:
                        if (
                            strike not in strikes_around_current
                            and len(strikes_around_current) < 10
                        ):
                            strikes_around_current.append(strike)

                # Sort by strike price (lowest to highest)
                strikes_around_current.sort()

                from telegram import InlineKeyboardMarkup, InlineKeyboardButton

                keyboard = [
                    [
                        InlineKeyboardButton(
                            f"${int(strike):,}",
                            callback_data=f"hedge|covered_call_select_confirm|{expiry}|{int(strike)}",
                        )
                    ]
                    for strike in strikes_around_current[:10]
                ]
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "⬅️ Back", callback_data="hedge|covered_call_select|{}"
                        )
                    ]
                )
                text = f"Select strike for expiry {expiry}:"
                await query.edit_message_text(
                    text, reply_markup=InlineKeyboardMarkup(keyboard)
                )
                logger.info(
                    f"[covered_call_select_strike] Sent strike selection message"
                )
        except Exception as e:
            logger.error(f"[covered_call_select_strike] Exception: {e}")
            await query.edit_message_text(
                f"❌ Error: {e}", reply_markup=get_back_button()
            )

    async def covered_call_select_confirm(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict
    ):
        """Step 3: Show summary for selected expiry/strike, ask for confirmation."""
        logger = logging.getLogger(__name__)
        logger.info(f"[covered_call_select_confirm] Entered with data: {data}")
        query = update.callback_query
        expiry = data.get("expiry")
        strike = float(data.get("strike"))
        from ..exchanges.deribit_options import deribit_options

        async with deribit_options:
            instruments = await deribit_options.get_instruments()
            # Find the symbol for this expiry/strike
            symbol = None
            for i in instruments:
                if (
                    i.symbol.startswith("BTC")
                    and i.instrument_type == "option"
                    and "-C" in i.symbol
                ):
                    parts = i.symbol.split("-")
                    if parts[1] == expiry and float(parts[2]) == strike:
                        symbol = i.symbol
                        break
            if not symbol:
                logger.error(
                    f"[covered_call_select_confirm] Option not found for expiry={expiry}, strike={strike}"
                )
                await query.edit_message_text(
                    "❌ Option not found.", reply_markup=get_back_button()
                )
                return
            ticker = await deribit_options.get_option_ticker(symbol)
            if not ticker:
                logger.error(
                    f"[covered_call_select_confirm] Option price unavailable for symbol={symbol}"
                )
                await query.edit_message_text(
                    "❌ Option price unavailable.", reply_markup=get_back_button()
                )
                return
            total_delta = self.portfolio.get_total_delta()
            target_delta = total_delta * 0.7
            hedge_delta = total_delta - target_delta
            call_quantity = hedge_delta / ticker.delta if abs(ticker.delta) > 0 else 0.0
            # Use last_price if mid_price is 0 (when bid/ask are 0)
            price = ticker.mid_price if ticker.mid_price > 0 else ticker.last_price
            # If both are 0, use a fallback price based on strike
            if price <= 0:
                # Use a simple estimate: 3% of strike for calls
                price = ticker.strike * 0.03
            call_income = call_quantity * price
            logger.info(
                f"[covered_call_select_confirm] Price calculation: mid_price={ticker.mid_price}, last_price={ticker.last_price}, final_price={price}, income={call_income}"
            )
            risk_reduction = (
                hedge_delta * (await self.get_current_price("BTC-USDT-PERP")) * 0.08
            )
            logger.info(
                f"[covered_call_select_confirm] Showing summary for symbol={symbol}, strike={strike}, expiry={expiry}"
            )
            text = (
                f"📈 *Covered Call Hedge*\n\n"
                f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                f"Target Delta: {target_delta:+.4f} BTC\n\n"
                f"*Selected Call:*\n"
                f"• Symbol: {ticker.symbol}\n"
                f"• Strike: ${ticker.strike:,.0f}\n"
                f"• Expiry: {ticker.expiry.strftime('%Y-%m-%d')}\n"
                f"• Quantity: {call_quantity:.4f} contracts\n"
                f"• Price: ${price:.2f}\n"
                f"• Income: ${call_income:,.2f}\n"
                f"• Risk Reduction: ${risk_reduction:,.2f}\n\n"
                f"*Greeks:*\n"
                f"• Delta: {ticker.delta:.4f}\n"
                f"• Gamma: {ticker.gamma:.6f}\n"
                f"• Theta: {ticker.theta:.4f}\n"
                f"• Vega: {ticker.vega:.4f}\n"
                f"• IV: {ticker.implied_volatility:.1%}\n\n"
                f"This will generate income while limiting upside potential."
            )
            context.user_data["pending_hedge"] = {
                "type": "covered_call",
                "symbol": ticker.symbol,
                "qty": call_quantity,
                "price": price,
                "cost": call_income,
                "instrument_type": "option",
                "exchange": "Deribit",
                "target_delta": target_delta,
                "option_contract": ticker,
            }
            await query.edit_message_text(
                text,
                reply_markup=get_confirmation_buttons("hedge"),
                parse_mode="Markdown",
            )

    async def start_collar_hedge(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start collar hedge wizard."""
        query = update.callback_query

        total_delta = self.portfolio.get_total_delta()

        if total_delta <= 0:
            text = "❌ *No Collar Needed*\n\nCollars are for long positions only."
            await query.edit_message_text(
                text, reply_markup=get_back_button(), parse_mode="Markdown"
            )
            return

        # Step 1: Ask user to choose Select or Automatic
        logger = logging.getLogger(__name__)
        logger.info("[collar] Showing Select/Automatic options to user")

        # Clear any previous collar selection
        if "collar_selection" in context.user_data:
            del context.user_data["collar_selection"]
        text = (
            f"🔒 *Collar Hedge*\n\n"
            f"Current Portfolio Delta: {total_delta:+.4f} BTC\n\n"
            f"How would you like to select your collar options?"
        )
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔍 Select", callback_data="hedge|collar_select|{}"
                    ),
                    InlineKeyboardButton(
                        "⚡ Automatic", callback_data="hedge|collar_auto|{}"
                    ),
                ],
                [InlineKeyboardButton("⬅️ Back", callback_data="back")],
            ]
        )
        await query.edit_message_text(
            text, reply_markup=keyboard, parse_mode="Markdown"
        )

    async def collar_auto_flow(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Automatic collar: current logic (fast, robust)."""
        query = update.callback_query
        total_delta = self.portfolio.get_total_delta()
        logger.info("[collar_auto_flow] Entered function")
        try:
            from ..exchanges.deribit_options import deribit_options

            logger.info("[collar_auto_flow] Before async with deribit_options")
            async with deribit_options:
                logger.info("[collar_auto_flow] Inside async with deribit_options")
                instruments = await deribit_options.get_instruments()
                put_instruments = [
                    i
                    for i in instruments
                    if i.symbol.startswith("BTC")
                    and i.instrument_type == "option"
                    and "-P" in i.symbol
                ]
                call_instruments = [
                    i
                    for i in instruments
                    if i.symbol.startswith("BTC")
                    and i.instrument_type == "option"
                    and "-C" in i.symbol
                ]
                logger.info(
                    f"[collar_auto_flow] Found {len(put_instruments)} put and {len(call_instruments)} call instruments"
                )
                if not put_instruments or not call_instruments:
                    text = (
                        f"🔒 *Collar Hedge*\n\n"
                        f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                        f"❌ Insufficient options available for collar.\n\n"
                        f"Try perpetual delta-neutral hedge instead."
                    )
                    await query.edit_message_text(
                        text, reply_markup=get_back_button(), parse_mode="Markdown"
                    )
                    logger.info(
                        "[collar_auto_flow] Insufficient options, sent error message"
                    )
                    return
                current_price = await self.get_current_price("BTC-USDT-PERP")
                logger.info(f"[collar_auto_flow] Got current price: {current_price}")
                # Find 10 closest puts and calls to ATM
                closest_puts = sorted(
                    put_instruments,
                    key=lambda x: abs(
                        x.symbol.split("-")[2]
                        and float(x.symbol.split("-")[2]) - current_price
                    ),
                )[:10]
                closest_calls = sorted(
                    call_instruments,
                    key=lambda x: abs(
                        x.symbol.split("-")[2]
                        and float(x.symbol.split("-")[2]) - current_price
                    ),
                )[:10]
                # Fetch tickers for these
                put_options = []
                call_options = []
                for inst in closest_puts:
                    ticker = await deribit_options.get_option_ticker(inst.symbol)
                    if ticker:
                        put_options.append(ticker)
                for inst in closest_calls:
                    ticker = await deribit_options.get_option_ticker(inst.symbol)
                    if ticker:
                        call_options.append(ticker)
                logger.info(
                    f"[collar_auto_flow] Got {len(put_options)} put and {len(call_options)} call tickers"
                )
                if not put_options or not call_options:
                    text = (
                        f"🔒 *Collar Hedge*\n\n"
                        f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                        f"❌ No options with price data available for collar.\n\n"
                        f"Try perpetual delta-neutral hedge instead."
                    )
                    await query.edit_message_text(
                        text, reply_markup=get_back_button(), parse_mode="Markdown"
                    )
                    logger.info("[collar_auto_flow] No tickers, sent error message")
                    return
                # Find ATM put and OTM call
                best_put = min(
                    put_options, key=lambda x: abs(x.strike - current_price * 0.95)
                )
                otm_calls = [
                    opt for opt in call_options if opt.strike > current_price * 1.10
                ]
                if not otm_calls:
                    text = (
                        f"🔒 *Collar Hedge*\n\n"
                        f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                        f"❌ No suitable OTM calls available for collar.\n\n"
                        f"Try perpetual delta-neutral hedge instead."
                    )
                    await query.edit_message_text(
                        text, reply_markup=get_back_button(), parse_mode="Markdown"
                    )
                    logger.info("[collar_auto_flow] No OTM calls, sent error message")
                    return
                best_call = min(otm_calls, key=lambda x: x.strike)
                # Calculate collar quantities
                put_quantity = total_delta / abs(best_put.delta)
                call_quantity = total_delta / best_call.delta
                # Net cost (put cost - call premium)
                # Use last_price if mid_price is 0 (when bid/ask are 0)
                put_price = (
                    best_put.mid_price
                    if best_put.mid_price > 0
                    else best_put.last_price
                )
                call_price = (
                    best_call.mid_price
                    if best_call.mid_price > 0
                    else best_call.last_price
                )
                # If both are 0, use fallback prices based on strike
                if put_price <= 0:
                    put_price = best_put.strike * 0.05  # 5% of strike for puts
                if call_price <= 0:
                    call_price = best_call.strike * 0.03  # 3% of strike for calls
                put_cost = put_quantity * put_price
                call_income = call_quantity * call_price
                logger.info(
                    f"[collar_auto_flow] Put price: {put_price}, Call price: {call_price}, Put cost: {put_cost}, Call income: {call_income}"
                )
                net_cost = put_cost - call_income
                # Risk reduction
                risk_reduction = total_delta * current_price * 0.20
                text = (
                    f"🔒 *Collar Hedge*\n\n"
                    f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                    f"Target Delta: {total_delta * 0.3:+.4f} BTC\n\n"
                    f"*Collar Strategy:*\n"
                    f"• Put: {best_put.symbol} @ ${best_put.strike:,.0f}\n"
                    f"• Call: {best_call.symbol} @ ${best_call.strike:,.0f}\n"
                    f"• Put Qty: {put_quantity:.4f} contracts\n"
                    f"• Call Qty: {call_quantity:.4f} contracts\n"
                    f"• Put Price: ${put_price:.2f}\n"
                    f"• Call Price: ${call_price:.2f}\n"
                    f"• Put Cost: ${put_cost:,.2f}\n"
                    f"• Call Income: ${call_income:,.2f}\n"
                    f"• Net Cost: ${net_cost:,.2f}\n"
                    f"• Risk Reduction: ${risk_reduction:,.2f}\n\n"
                    f"*Put Greeks:*\n"
                    f"• Delta: {best_put.delta:.4f} | IV: {best_put.implied_volatility:.1%}\n\n"
                    f"*Call Greeks:*\n"
                    f"• Delta: {best_call.delta:.4f} | IV: {best_call.implied_volatility:.1%}\n\n"
                    f"This creates a defined risk/reward profile."
                )
                context.user_data["pending_hedge"] = {
                    "type": "collar",
                    "symbol": f"{best_put.symbol} + {best_call.symbol}",
                    "qty": min(put_quantity, call_quantity),
                    "price": net_cost / min(put_quantity, call_quantity),
                    "cost": net_cost,
                    "instrument_type": "option",
                    "exchange": "Deribit",
                    "target_delta": total_delta * 0.3,
                    "option_contract": best_put,  # Store put as primary
                    "collar_data": {
                        "put": best_put,
                        "call": best_call,
                        "put_qty": put_quantity,
                        "call_qty": call_quantity,
                    },
                }
                await query.edit_message_text(
                    text,
                    reply_markup=get_confirmation_buttons("hedge"),
                    parse_mode="Markdown",
                )
                logger.info("[collar_auto_flow] Sent confirmation message")
        except Exception as e:
            logger.error(f"[collar_auto_flow] Exception: {e}")
            text = (
                f"🔒 *Collar Hedge*\n\n"
                f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                f"❌ Error loading options data: {str(e)}\n\n"
                f"Try perpetual delta-neutral hedge instead."
            )
            await query.edit_message_text(
                text, reply_markup=get_back_button(), parse_mode="Markdown"
            )

    async def collar_select_expiry(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Step 1: Let user select expiry for collar."""
        logger = logging.getLogger(__name__)
        logger.info("[collar_select] User chose 'Select' - showing expiry options")
        query = update.callback_query
        from ..exchanges.deribit_options import deribit_options

        async with deribit_options:
            instruments = await deribit_options.get_instruments()
            put_instruments = [
                i
                for i in instruments
                if i.symbol.startswith("BTC")
                and i.instrument_type == "option"
                and "-P" in i.symbol
            ]
            call_instruments = [
                i
                for i in instruments
                if i.symbol.startswith("BTC")
                and i.instrument_type == "option"
                and "-C" in i.symbol
            ]
            # Extract unique expiries (common to both puts and calls)
            put_expiries = set(i.symbol.split("-")[1] for i in put_instruments)
            call_expiries = set(i.symbol.split("-")[1] for i in call_instruments)
            common_expiries = sorted(list(put_expiries.intersection(call_expiries)))
            logger.info(f"[collar_select_expiry] Available expiries: {common_expiries}")
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = [
                [
                    InlineKeyboardButton(
                        exp,
                        callback_data=encode_callback_data(
                            "hedge", "collar_select_strike", {"expiry": exp}
                        ),
                    )
                ]
                for exp in common_expiries[:10]
            ]
            keyboard.append(
                [InlineKeyboardButton("⬅️ Back", callback_data="hedge|collar|{}")]
            )
            text = "Select expiry for your collar (both put and call):"
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def collar_select_strike(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict
    ):
        """Step 2: Let user select strikes for chosen expiry."""
        logger = logging.getLogger(__name__)
        query = update.callback_query
        expiry = data.get("expiry")
        logger.info(f"[collar_select_strike] Entered with expiry={expiry}")
        from ..exchanges.deribit_options import deribit_options

        try:
            async with deribit_options:
                instruments = await deribit_options.get_instruments()
                logger.info(
                    f"[collar_select_strike] Got {len(instruments)} instruments"
                )
                put_instruments = [
                    i
                    for i in instruments
                    if i.symbol.startswith("BTC")
                    and i.instrument_type == "option"
                    and "-P" in i.symbol
                    and i.symbol.split("-")[1] == expiry
                ]
                call_instruments = [
                    i
                    for i in instruments
                    if i.symbol.startswith("BTC")
                    and i.instrument_type == "option"
                    and "-C" in i.symbol
                    and i.symbol.split("-")[1] == expiry
                ]
                logger.info(
                    f"[collar_select_strike] Found {len(put_instruments)} puts and {len(call_instruments)} calls for expiry {expiry}"
                )
                put_strikes = sorted(
                    list(set(float(i.symbol.split("-")[2]) for i in put_instruments))
                )
                call_strikes = sorted(
                    list(set(float(i.symbol.split("-")[2]) for i in call_instruments))
                )
                logger.info(f"[collar_select_strike] Put strikes: {put_strikes}")
                logger.info(f"[collar_select_strike] Call strikes: {call_strikes}")
                print(
                    f"[collar_select_strike] Put strikes for expiry {expiry}: {put_strikes}"
                )
                print(
                    f"[collar_select_strike] Call strikes for expiry {expiry}: {call_strikes}"
                )

                # Get current price to find strikes around it
                current_price = await self.get_current_price("BTC-USDT-PERP")
                logger.info(f"[collar_select_strike] Current price: {current_price}")

                # Find strikes around current price for both puts and calls
                put_strikes_around_current = []
                call_strikes_around_current = []

                for strike in put_strikes:
                    if len(put_strikes_around_current) >= 5:  # Max 5 put strikes
                        break
                    if (
                        strike <= current_price + 3000
                        and strike >= current_price - 3000
                    ):
                        put_strikes_around_current.append(strike)

                for strike in call_strikes:
                    if len(call_strikes_around_current) >= 5:  # Max 5 call strikes
                        break
                    if (
                        strike <= current_price + 5000
                        and strike >= current_price + 1000  # OTM calls only
                    ):
                        call_strikes_around_current.append(strike)

                # If we don't have enough strikes, add more
                if len(put_strikes_around_current) < 5:
                    put_strikes_sorted_by_distance = sorted(
                        put_strikes, key=lambda x: abs(x - current_price)
                    )
                    for strike in put_strikes_sorted_by_distance:
                        if (
                            strike not in put_strikes_around_current
                            and len(put_strikes_around_current) < 5
                        ):
                            put_strikes_around_current.append(strike)

                if len(call_strikes_around_current) < 5:
                    call_strikes_sorted_by_distance = sorted(
                        call_strikes, key=lambda x: abs(x - current_price)
                    )
                    for strike in call_strikes_sorted_by_distance:
                        if (
                            strike not in call_strikes_around_current
                            and len(call_strikes_around_current) < 5
                        ):
                            call_strikes_around_current.append(strike)

                # Sort by strike price (lowest to highest)
                put_strikes_around_current.sort()
                call_strikes_around_current.sort()

                from telegram import InlineKeyboardMarkup, InlineKeyboardButton

                # Create keyboard with put and call strikes
                keyboard = []

                # Add put strikes section
                keyboard.append(
                    [InlineKeyboardButton("🛡️ PUT STRIKES:", callback_data="info")]
                )
                for strike in put_strikes_around_current[:5]:
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                f"🛡️ ${int(strike):,}",
                                callback_data=f"hedge|collar_select_confirm|{expiry}|put|{int(strike)}",
                            )
                        ]
                    )

                # Add call strikes section
                keyboard.append(
                    [InlineKeyboardButton("📈 CALL STRIKES:", callback_data="info")]
                )
                for strike in call_strikes_around_current[:5]:
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                f"📈 ${int(strike):,}",
                                callback_data=f"hedge|collar_select_confirm|{expiry}|call|{int(strike)}",
                            )
                        ]
                    )

                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "⬅️ Back", callback_data="hedge|collar_select|{}"
                        )
                    ]
                )
                text = f"Select strike for expiry {expiry}:\n\n🛡️ Choose a PUT strike (protection)\n📈 Choose a CALL strike (income)"
                await query.edit_message_text(
                    text, reply_markup=InlineKeyboardMarkup(keyboard)
                )
                logger.info(f"[collar_select_strike] Sent strike selection message")
        except Exception as e:
            logger.error(f"[collar_select_strike] Exception: {e}")
            await query.edit_message_text(
                f"❌ Error: {e}", reply_markup=get_back_button()
            )

    async def collar_select_confirm(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict
    ):
        """Step 3: Store selected option and check if both legs are selected."""
        logger = logging.getLogger(__name__)
        logger.info(f"[collar_select_confirm] Entered with data: {data}")
        query = update.callback_query
        expiry = data.get("expiry")
        option_type = data.get("option_type")  # "put" or "call"
        strike = float(data.get("strike"))
        from ..exchanges.deribit_options import deribit_options

        async with deribit_options:
            instruments = await deribit_options.get_instruments()
            # Find the symbol for this expiry/strike/type
            symbol = None
            for i in instruments:
                if (
                    i.symbol.startswith("BTC")
                    and i.instrument_type == "option"
                    and f"-{option_type.upper()[0]}" in i.symbol
                ):
                    parts = i.symbol.split("-")
                    if parts[1] == expiry and float(parts[2]) == strike:
                        symbol = i.symbol
                        break
            if not symbol:
                logger.error(
                    f"[collar_select_confirm] Option not found for expiry={expiry}, strike={strike}, type={option_type}"
                )
                await query.edit_message_text(
                    "❌ Option not found.", reply_markup=get_back_button()
                )
                return
            ticker = await deribit_options.get_option_ticker(symbol)
            if not ticker:
                logger.error(
                    f"[collar_select_confirm] Option price unavailable for symbol={symbol}"
                )
                await query.edit_message_text(
                    "❌ Option price unavailable.", reply_markup=get_back_button()
                )
                return

            # Store the selected option in user_data
            if "collar_selection" not in context.user_data:
                context.user_data["collar_selection"] = {}

            context.user_data["collar_selection"][option_type] = {
                "symbol": symbol,
                "ticker": ticker,
                "strike": strike,
                "expiry": expiry,
            }

            logger.info(
                f"[collar_select_confirm] Stored {option_type} selection: {symbol}"
            )

            # Check if both put and call are selected
            collar_selection = context.user_data.get("collar_selection", {})
            if "put" in collar_selection and "call" in collar_selection:
                # Both legs selected, show combined summary
                await self.show_collar_summary(update, context)
            else:
                # Only one leg selected, ask for the other
                remaining_type = "call" if option_type == "put" else "put"
                text = (
                    f"✅ *{option_type.upper()} Selected*\n\n"
                    f"• {option_type.title()}: {symbol}\n"
                    f"• Strike: ${strike:,.0f}\n\n"
                    f"Now select your {remaining_type} strike to complete the collar."
                )
                from telegram import InlineKeyboardMarkup, InlineKeyboardButton

                keyboard = [
                    [
                        InlineKeyboardButton(
                            f"Select {remaining_type.upper()}",
                            callback_data=f"hedge|collar_select_strike|{expiry}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⬅️ Back", callback_data="hedge|collar_select|{}"
                        )
                    ],
                ]

                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown",
                )

    async def show_collar_summary(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show combined collar summary with both put and call."""
        logger = logging.getLogger(__name__)
        logger.info("[show_collar_summary] Showing combined collar summary")
        query = update.callback_query

        collar_selection = context.user_data.get("collar_selection", {})
        put_data = collar_selection.get("put")
        call_data = collar_selection.get("call")

        if not put_data or not call_data:
            await query.edit_message_text(
                "❌ Error: Both put and call must be selected for collar.",
                reply_markup=get_back_button(),
            )
            return

        put_ticker = put_data["ticker"]
        call_ticker = call_data["ticker"]

        total_delta = self.portfolio.get_total_delta()
        target_delta = total_delta * 0.3
        hedge_delta = total_delta - target_delta

        # Calculate quantities
        put_quantity = (
            hedge_delta / abs(put_ticker.delta) if abs(put_ticker.delta) > 0 else 0.0
        )
        call_quantity = (
            hedge_delta / call_ticker.delta if abs(call_ticker.delta) > 0 else 0.0
        )

        # Calculate prices with fallbacks
        put_price = (
            put_ticker.mid_price if put_ticker.mid_price > 0 else put_ticker.last_price
        )
        if put_price <= 0:
            put_price = put_ticker.strike * 0.05

        call_price = (
            call_ticker.mid_price
            if call_ticker.mid_price > 0
            else call_ticker.last_price
        )
        if call_price <= 0:
            call_price = call_ticker.strike * 0.03

        put_cost = put_quantity * put_price
        call_income = call_quantity * call_price
        net_cost = put_cost - call_income

        current_price = await self.get_current_price("BTC-USDT-PERP")
        risk_reduction = total_delta * current_price * 0.20

        logger.info(
            f"[show_collar_summary] Put cost: {put_cost}, Call income: {call_income}, Net cost: {net_cost}"
        )

        text = (
            f"🔒 *Collar Hedge Summary*\n\n"
            f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
            f"Target Delta: {target_delta:+.4f} BTC\n\n"
            f"*Collar Strategy:*\n"
            f"• Put: {put_ticker.symbol} @ ${put_ticker.strike:,.0f}\n"
            f"• Call: {call_ticker.symbol} @ ${call_ticker.strike:,.0f}\n"
            f"• Put Qty: {put_quantity:.4f} contracts\n"
            f"• Call Qty: {call_quantity:.4f} contracts\n"
            f"• Put Price: ${put_price:.2f}\n"
            f"• Call Price: ${call_price:.2f}\n"
            f"• Put Cost: ${put_cost:,.2f}\n"
            f"• Call Income: ${call_income:,.2f}\n"
            f"• Net Cost: ${net_cost:,.2f}\n"
            f"• Risk Reduction: ${risk_reduction:,.2f}\n\n"
            f"*Put Greeks:*\n"
            f"• Delta: {put_ticker.delta:.4f} | IV: {put_ticker.implied_volatility:.1%}\n\n"
            f"*Call Greeks:*\n"
            f"• Delta: {call_ticker.delta:.4f} | IV: {call_ticker.implied_volatility:.1%}\n\n"
            f"This creates a defined risk/reward profile."
        )

        # Store complete collar data
        context.user_data["pending_hedge"] = {
            "type": "collar",
            "symbol": f"{put_ticker.symbol} + {call_ticker.symbol}",
            "qty": min(put_quantity, call_quantity),
            "price": (
                net_cost / min(put_quantity, call_quantity)
                if min(put_quantity, call_quantity) > 0
                else 0
            ),
            "cost": net_cost,
            "instrument_type": "option",
            "exchange": "Deribit",
            "target_delta": target_delta,
            "option_contract": put_ticker,  # Store put as primary
            "collar_data": {
                "put": put_ticker,
                "call": call_ticker,
                "put_qty": put_quantity,
                "call_qty": call_quantity,
            },
        }

        await query.edit_message_text(
            text,
            reply_markup=get_confirmation_buttons("hedge"),
            parse_mode="Markdown",
        )

    async def start_dynamic_hedge(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start dynamic hedge wizard."""
        query = update.callback_query

        total_delta = self.portfolio.get_total_delta()

        if abs(total_delta) < 0.01:
            text = "✅ *Portfolio Already Delta-Neutral*\n\nNo dynamic hedge needed - your portfolio is already delta-neutral."
            await query.edit_message_text(
                text, reply_markup=get_back_button(), parse_mode="Markdown"
            )
            return

        # Go directly to automatic flow
        logger = logging.getLogger(__name__)
        logger.info("[dynamic_hedge] Starting automatic dynamic hedge")
        await self.dynamic_hedge_auto_flow(update, context)

    async def dynamic_hedge_auto_flow(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Automatic dynamic hedge flow - bot finds the best option."""
        import logging

        logger = logging.getLogger(__name__)
        logger.info("[dynamic_hedge_auto_flow] Starting automatic dynamic hedge")
        query = update.callback_query

        total_delta = self.portfolio.get_total_delta()

        try:
            # Get option chain for dynamic hedge (ultra-fast approach)
            from ..exchanges.deribit_options import deribit_options

            async with deribit_options:
                # Get current price first
                current_price = await self.get_current_price("BTC-USDT-PERP")

                # Get only a small sample of instruments for speed
                instruments = await deribit_options.get_instruments()

                # Filter to BTC options and limit to 10 closest to current price
                btc_options = []
                for i in instruments:
                    if i.symbol.startswith("BTC") and i.instrument_type == "option":
                        parts = i.symbol.split("-")
                        if len(parts) >= 4:  # Valid option symbol
                            try:
                                strike = float(parts[2])
                                # Only consider options within 10% of current price (tighter filter)
                                if abs(strike - current_price) <= current_price * 0.1:
                                    btc_options.append((i, abs(strike - current_price)))
                            except ValueError:
                                continue

                # Sort by distance from current price and take only top 5
                btc_options.sort(key=lambda x: x[1])
                btc_options = [opt[0] for opt in btc_options[:5]]

                if not btc_options:
                    text = (
                        f"♻️ *Dynamic Hedge - Automatic*\n\n"
                        f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                        f"❌ No suitable options available for dynamic hedging.\n\n"
                        f"Try perpetual delta-neutral hedge instead."
                    )
                    await query.edit_message_text(
                        text, reply_markup=get_back_button(), parse_mode="Markdown"
                    )
                    return

                # Get tickers for only the top 5 options (much faster)
                option_chain = []
                for option in btc_options:
                    ticker = await deribit_options.get_option_ticker(option.symbol)
                    if ticker:
                        option_chain.append(ticker)

                if not option_chain:
                    text = (
                        f"♻️ *Dynamic Hedge - Automatic*\n\n"
                        f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                        f"❌ No option prices available for dynamic hedging.\n\n"
                        f"Try perpetual delta-neutral hedge instead."
                    )
                    await query.edit_message_text(
                        text, reply_markup=get_back_button(), parse_mode="Markdown"
                    )
                    return

                # Find best option manually (faster than hedge service)
                best_option = None
                best_score = 0

                for option in option_chain:
                    # Calculate effectiveness score
                    delta_impact = abs(option.delta)
                    price = (
                        option.mid_price if option.mid_price > 0 else option.last_price
                    )
                    if price <= 0:
                        if option.option_type == "put":
                            price = option.strike * 0.05
                        else:
                            price = option.strike * 0.03

                    # Score based on delta impact vs cost
                    if price > 0:
                        score = delta_impact / price
                        if score > best_score:
                            best_score = score
                            best_option = option

                if not best_option:
                    text = (
                        f"♻️ *Dynamic Hedge - Automatic*\n\n"
                        f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                        f"❌ No suitable options found for dynamic hedge.\n\n"
                        f"Try perpetual delta-neutral hedge instead."
                    )
                    await query.edit_message_text(
                        text, reply_markup=get_back_button(), parse_mode="Markdown"
                    )
                    return

                # Calculate hedge quantities
                target_delta = total_delta * 0.3  # Reduce to 30% of current delta
                hedge_delta = total_delta - target_delta
                quantity = (
                    hedge_delta / abs(best_option.delta)
                    if abs(best_option.delta) > 0
                    else 0.0
                )

                # Use last_price if mid_price is 0 (when bid/ask are 0)
                price = (
                    best_option.mid_price
                    if best_option.mid_price > 0
                    else best_option.last_price
                )
                # If both are 0, use a fallback price based on strike
                if price <= 0:
                    # Use a simple estimate based on option type
                    if best_option.option_type == "put":
                        price = best_option.strike * 0.05  # 5% of strike for puts
                    else:
                        price = best_option.strike * 0.03  # 3% of strike for calls
                cost = quantity * price
                logger.info(
                    f"[dynamic_hedge_auto_flow] Price calculation: mid_price={best_option.mid_price}, last_price={best_option.last_price}, final_price={price}, cost={cost}"
                )

                # Determine hedge type
                hedge_type = (
                    "protective_put"
                    if best_option.option_type == "put"
                    else "covered_call"
                )

                text = (
                    f"♻️ Dynamic Hedge - Automatic\n\n"
                    f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                    f"Target Delta: {target_delta:+.4f} BTC\n\n"
                    f"Optimal Hedge Found:\n"
                    f"• Type: {hedge_type.replace('_', ' ').title()}\n"
                    f"• Symbol: {best_option.symbol}\n"
                    f"• Strike: ${best_option.strike:,.0f}\n"
                    f"• Expiry: {best_option.expiry.strftime('%Y-%m-%d')}\n"
                    f"• Quantity: {quantity:.4f} contracts\n"
                    f"• Price: ${price:.2f}\n"
                    f"• Cost: ${cost:,.2f}\n"
                    f"• Effectiveness: {best_score:.2f}\n\n"
                    f"Greeks:\n"
                    f"• Delta: {best_option.delta:.4f}\n"
                    f"• Gamma: {best_option.gamma:.6f}\n"
                    f"• Theta: {best_option.theta:.4f}\n"
                    f"• Vega: {best_option.vega:.4f}\n"
                    f"• IV: {best_option.implied_volatility:.1%}\n\n"
                    f"Dynamic Features:\n"
                    f"• Auto-rebalancing based on delta changes\n"
                    f"• Real-time Greeks monitoring\n"
                    f"• Optimal strike selection\n"
                    f"• Cost-effective hedging"
                )

                # Store hedge data
                context.user_data["pending_hedge"] = {
                    "type": "dynamic_hedge",
                    "symbol": best_option.symbol,
                    "qty": quantity,
                    "price": price,
                    "cost": cost,
                    "instrument_type": "option",
                    "exchange": "Deribit",
                    "target_delta": target_delta,
                    "option_contract": best_option,
                }

                await query.edit_message_text(
                    text,
                    reply_markup=get_confirmation_buttons("hedge"),
                    parse_mode="Markdown",
                )

        except Exception as e:
            logger.error(f"Error in dynamic hedge auto flow: {e}")
            text = (
                f"♻️ *Dynamic Hedge - Automatic*\n\n"
                f"Current Portfolio Delta: {total_delta:+.4f} BTC\n"
                f"❌ Error loading options data: {str(e)}\n\n"
                f"Try perpetual delta-neutral hedge instead."
            )
            await query.edit_message_text(
                text, reply_markup=get_back_button(), parse_mode="Markdown"
            )

    async def show_active_hedges(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show active hedges."""
        query = update.callback_query

        if not self.active_hedges:
            text = (
                f"📂 *Active Hedges*\n\n"
                f"No active hedges found.\n\n"
                f"Create a hedge to see it here."
            )
        else:
            text = "📂 *Active Hedges*\n\n"
            for i, hedge in enumerate(self.active_hedges, 1):
                text += (
                    f"{i}. {hedge['type'].replace('_', ' ').title()} | {hedge['symbol']} | Qty: {hedge['qty']} @ ${hedge['price']}\n"
                    f"   Exchange: {hedge['exchange']} | Time: {hedge['timestamp']}\n\n"
                )
        await query.edit_message_text(
            text, reply_markup=get_back_button(), parse_mode="Markdown"
        )

    async def start_remove_hedge(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start remove hedge wizard."""
        query = update.callback_query

        if not self.active_hedges:
            text = (
                f"🗑️ *Remove Hedge*\n\n"
                f"No active hedges to remove.\n\n"
                f"Create a hedge first to remove it."
            )
            await query.edit_message_text(
                text, reply_markup=get_back_button(), parse_mode="Markdown"
            )
            return

        from telegram import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = []
        for i, hedge in enumerate(self.active_hedges, 1):
            label = f"Remove {hedge['type'].replace('_', ' ').title()} | {hedge['symbol']} | Qty: {hedge['qty']}"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        label, callback_data=f"hedge|remove_hedge_confirm|{i-1}"
                    )
                ]
            )
        keyboard.append(
            [InlineKeyboardButton("⬅️ Back", callback_data="hedge|view_hedges|{}")]
        )
        text = "🗑️ *Remove Hedge*\n\nSelect a hedge to remove:"
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    async def remove_hedge_confirm(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict
    ):
        """Remove the selected hedge from active_hedges and portfolio positions."""
        query = update.callback_query
        idx = data.get("idx") if isinstance(data, dict) else data
        if idx is not None and 0 <= idx < len(self.active_hedges):
            removed = self.active_hedges.pop(idx)
            # Remove the corresponding position from the portfolio
            symbol = removed.get("symbol")
            qty = removed.get("qty")
            instrument_type = removed.get("instrument_type")
            exchange = removed.get("exchange")
            hedge_type = removed.get("type")
            # For collar, remove both put and call
            if hedge_type == "collar" and "collar_data" in removed:
                collar_data = removed["collar_data"]
                put = collar_data.get("put")
                call = collar_data.get("call")
                put_qty = collar_data.get("put_qty", 0)
                call_qty = collar_data.get("call_qty", 0)
                if put:
                    self.portfolio.update_fill(
                        put.symbol, -put_qty, put.mid_price, "option", "Deribit"
                    )
                if call:
                    self.portfolio.update_fill(
                        call.symbol, call_qty, call.mid_price, "option", "Deribit"
                    )
            else:
                # Remove the position by reversing the fill
                self.portfolio.update_fill(
                    symbol, -qty, removed.get("price", 0), instrument_type, exchange
                )
            text = (
                f"✅ *Hedge Removed*\n\n"
                f"{removed['type'].replace('_', ' ').title()} | {removed['symbol']} | Qty: {removed['qty']} @ ${removed['price']}\n"
                f"Exchange: {removed['exchange']} | Time: {removed['timestamp']}\n"
                f"Corresponding position removed from portfolio."
            )
        else:
            text = "❌ Invalid hedge selection."
        await query.edit_message_text(
            text, reply_markup=get_back_button(), parse_mode="Markdown"
        )

    async def confirm_hedge_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict
    ):
        """Confirm a hedge action."""
        query = update.callback_query

        hedge = context.user_data.get("pending_hedge")
        if not hedge:
            await query.edit_message_text(
                "No pending hedge found.",
                reply_markup=get_back_button(),
                parse_mode="Markdown",
            )
            return

        hedge_type = hedge.get("type")
        symbol = hedge.get("symbol")
        qty = hedge.get("qty")
        price = hedge.get("price")
        # Only add to active_hedges if not a duplicate
        if not any(
            h
            for h in self.active_hedges
            if h["type"] == hedge_type
            and h["symbol"] == symbol
            and h["qty"] == qty
            and h["price"] == price
            and h["exchange"] == hedge.get("exchange")
        ):
            self.active_hedges.append(
                {
                    "type": hedge_type,
                    "symbol": symbol,
                    "qty": qty,
                    "price": price,
                    "instrument_type": hedge.get("instrument_type"),
                    "exchange": hedge.get("exchange"),
                    "target_delta": hedge.get("target_delta"),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

        if hedge_type == "perp_delta_neutral":
            # Execute the hedge
            self.portfolio.update_fill(
                symbol, qty, price, hedge.get("instrument_type"), hedge.get("exchange")
            )
            text = f"✅ *Delta-Neutral Hedge Executed*\n\n{symbol}: {qty:+.4f} @ ${price:.2f}\n\nPortfolio is now delta-neutral!"
        elif hedge_type == "protective_put":
            # Execute the hedge
            self.portfolio.update_fill(
                symbol, qty, price, hedge.get("instrument_type"), hedge.get("exchange")
            )
            text = f"✅ *Protective Put Hedge Executed*\n\n{symbol}: {qty:+.4f} @ ${price:.2f}\n\nPortfolio delta reduced."
        elif hedge_type == "covered_call":
            # Execute the hedge
            self.portfolio.update_fill(
                symbol, qty, price, hedge.get("instrument_type"), hedge.get("exchange")
            )
            text = f"✅ *Covered Call Hedge Executed*\n\n{symbol}: {qty:+.4f} @ ${price:.2f}\n\nPortfolio delta reduced and income generated."
        elif hedge_type == "collar":
            # Execute collar hedge (both put and call)
            collar_data = hedge.get("collar_data", {})
            put = collar_data.get("put")
            call = collar_data.get("call")
            put_qty = collar_data.get("put_qty", 0)
            call_qty = collar_data.get("call_qty", 0)

            if put and call:
                # Add put position
                self.portfolio.update_fill(
                    put.symbol, put_qty, put.mid_price, "option", "Deribit"
                )
                # Add short call position
                self.portfolio.update_fill(
                    call.symbol, -call_qty, call.mid_price, "option", "Deribit"
                )
                text = f"✅ *Collar Hedge Executed*\n\nPut: {put.symbol} {put_qty:+.4f} @ ${put.mid_price:.2f}\nCall: {call.symbol} {-call_qty:+.4f} @ ${call.mid_price:.2f}\n\nPortfolio has defined risk/reward profile."
            else:
                text = "❌ Error: Invalid collar data."
        elif hedge_type == "dynamic_hedge":
            # Execute the dynamic hedge
            self.portfolio.update_fill(
                symbol, qty, price, hedge.get("instrument_type"), hedge.get("exchange")
            )
            text = f"✅ *Dynamic Hedge Executed*\n\n{symbol}: {qty:+.4f} @ ${price:.2f}\n\nPortfolio dynamically hedged with optimal options strategy."
        else:
            text = "❌ Unknown hedge type."

        # Clear pending hedge
        context.user_data.pop("pending_hedge", None)

        await query.edit_message_text(
            text, reply_markup=get_back_button(), parse_mode="Markdown"
        )

    async def handle_analytics_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, step: str, data: dict
    ):
        query = update.callback_query
        if step == "by_position":
            # List all positions
            positions = list(getattr(self.portfolio, "positions", {}).values())
            # Filter only valid positions (dict/object with symbol)
            valid_positions = []
            for pos in positions:
                if isinstance(pos, str):
                    continue
                if hasattr(pos, "symbol") or (
                    isinstance(pos, dict) and "symbol" in pos
                ):
                    valid_positions.append(pos)
            if not valid_positions:
                await query.edit_message_text(
                    "No positions.", reply_markup=get_back_button()
                )
                return
            text = "*Positions:*\n\n"
            buttons = []
            for i, pos in enumerate(valid_positions):
                symbol = pos.symbol if hasattr(pos, "symbol") else pos.get("symbol")
                qty = pos.qty if hasattr(pos, "qty") else pos.get("qty")
                text += f"{i+1}. `{symbol}` qty: `{qty}`\n"
                buttons.append(
                    [
                        {
                            "text": f"{symbol}",
                            "callback_data": f"analytics|position_detail|{i}",
                        }
                    ]
                )
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = [
                [InlineKeyboardButton(b["text"], callback_data=b["callback_data"])]
                for b in sum(buttons, [])
            ]
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="analytics")])
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
            )
        elif step == "position_detail":
            if isinstance(data, int):
                idx = data
            elif isinstance(data, str):
                try:
                    idx = int(data)
                except Exception:
                    idx = 0
            elif isinstance(data, dict):
                idx = int(data.get("idx", 0))
            else:
                idx = 0
            positions = list(getattr(self.portfolio, "positions", {}).values())
            # Filter only valid positions (dict/object with symbol)
            valid_positions = []
            for pos in positions:
                if isinstance(pos, str):
                    continue
                if hasattr(pos, "symbol") or (
                    isinstance(pos, dict) and "symbol" in pos
                ):
                    valid_positions.append(pos)
            if idx < 0 or idx >= len(valid_positions):
                await query.edit_message_text(
                    "Invalid position.", reply_markup=get_back_button()
                )
                return
            pos = valid_positions[idx]
            symbol = pos.symbol if hasattr(pos, "symbol") else pos.get("symbol")
            qty = pos.qty if hasattr(pos, "qty") else pos.get("qty")
            avg_px = pos.avg_px if hasattr(pos, "avg_px") else pos.get("avg_px")
            instrument_type = (
                pos.instrument_type
                if hasattr(pos, "instrument_type")
                else pos.get("instrument_type")
            )
            current_price = await self.get_current_price(symbol)
            pnl = (current_price - avg_px) * qty
            text = (
                f"*Position Detail*\n\n"
                f"Symbol: `{symbol}`\n"
                f"Qty: `{qty}`\n"
                f"Avg Px: `${avg_px}`\n"
                f"Current Px: `${current_price}`\n"
                f"Unrealized P&L: `${pnl:,.2f}`\n"
                f"Type: `{instrument_type}`\n"
            )
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = [
                [
                    InlineKeyboardButton(
                        "⬅️ Back", callback_data="analytics|by_position|{}"
                    )
                ]
            ]
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
            )
        elif step == "by_hedge":
            hedges = getattr(self, "active_hedges", [])
            if not hedges:
                await query.edit_message_text(
                    "No active hedges.", reply_markup=get_back_button()
                )
                return
            text = "*Active Hedges:*\n\n"
            buttons = []
            for i, hedge in enumerate(hedges):
                desc = hedge.get("desc", hedge.get("symbol", f"Hedge {i+1}"))
                text += f"{i+1}. {desc}\n"
                buttons.append(
                    [
                        {
                            "text": f"{desc}",
                            "callback_data": f"analytics|hedge_detail|{i}",
                        }
                    ]
                )
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = [
                [InlineKeyboardButton(b["text"], callback_data=b["callback_data"])]
                for b in sum(buttons, [])
            ]
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="analytics")])
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
            )
        elif step == "hedge_detail":
            if isinstance(data, int):
                idx = data
            elif isinstance(data, str):
                try:
                    idx = int(data)
                except Exception:
                    idx = 0
            elif isinstance(data, dict):
                idx = int(data.get("idx", 0))
            else:
                idx = 0
            hedges = getattr(self, "active_hedges", [])
            if idx < 0 or idx >= len(hedges):
                await query.edit_message_text(
                    "Invalid hedge.", reply_markup=get_back_button()
                )
                return
            hedge = hedges[idx]
            desc = hedge.get("desc", hedge.get("symbol", f"Hedge {idx+1}"))
            price = hedge.get("price", 0.0)
            cost = hedge.get("cost", 0.0)
            qty = hedge.get("qty", 0.0)
            text = (
                f"*Hedge Detail*\n\n"
                f"Desc: `{desc}`\n"
                f"Qty: `{qty}`\n"
                f"Price: `${price}`\n"
                f"Cost: `${cost}`\n"
            )
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = [
                [InlineKeyboardButton("⬅️ Back", callback_data="analytics|by_hedge|{}")]
            ]
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                "Unknown analytics action.", reply_markup=get_back_button()
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (for wizard input)."""
        text = update.message.text

        # Risk config value input (check first)
        if context.user_data.get("awaiting_risk_value"):
            logger = logging.getLogger(__name__)
            logger.info("[handle_message] Received risk config value input")
            metric = context.user_data.get("risk_config_edit")
            value = text.strip()
            # Validate input
            try:
                float_value = float(value)
            except Exception:
                await update.message.reply_text(
                    f"❌ Invalid value. Please enter a number.",
                    parse_mode="Markdown",
                )
                return
            context.user_data["risk_config_new_value"] = float_value
            context.user_data["awaiting_risk_value"] = False
            # Ask for confirmation
            await update.message.reply_text(
                f"Confirm new value for {metric}: `{float_value}`?",
                reply_markup=self._get_risk_confirm_keyboard(),
                parse_mode="Markdown",
            )
            return

        # Wizard-based flows
        if "wizard" not in context.user_data:
            return

        wizard = context.user_data["wizard"]

        if wizard["type"] == "add_spot" and wizard["step"] == "quantity":
            await self.handle_spot_quantity(update, context, text)
        elif wizard["type"] == "add_future" and wizard["step"] == "quantity":
            await self.handle_future_quantity(update, context, text)

    def _get_risk_confirm_keyboard(self):
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton

        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Confirm", callback_data="risk_config|confirm|{}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data="risk_config|cancel|{}"
                    )
                ],
            ]
        )

    async def handle_spot_quantity(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, quantity_text: str
    ):
        """Handle spot quantity input."""
        try:
            quantity = float(quantity_text)
            if quantity <= 0:
                await update.message.reply_text("❌ Quantity must be positive.")
                return

            # Get current price from market data
            current_price = await self.get_current_price("BTC-USDT-SPOT")

            # Calculate costs using costing service
            costs = costing_service.calculate_total_cost(
                quantity, current_price, "OKX", "spot"
            )

            # Calculate delta impact
            delta_impact = quantity  # 1:1 for spot

            text = (
                f"📋 *Trade Preview*\n\n"
                f"Symbol: BTC-USDT-SPOT\n"
                f"Quantity: {quantity:+.4f} BTC\n"
                f"Price: ${current_price:.2f}\n"
                f"Delta Impact: {delta_impact:+.4f} BTC\n\n"
                f"{costing_service.get_cost_summary(quantity, current_price, 'OKX', 'spot')}"
            )

            # Store trade data
            context.user_data["pending_trade"] = {
                "action_type": "add",
                "symbol": "BTC-USDT-SPOT",
                "qty": quantity,
                "price": current_price,
                "instrument_type": "spot",
                "exchange": "OKX",
            }

            await update.message.reply_text(
                text,
                reply_markup=get_confirmation_buttons("portfolio"),
                parse_mode="Markdown",
            )

            # Clear wizard state
            del context.user_data["wizard"]

        except ValueError:
            await update.message.reply_text(
                "❌ Please enter a valid number (e.g., 5.0)"
            )

    async def handle_future_quantity(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, quantity_text: str
    ):
        """Handle future quantity input."""
        try:
            quantity = float(quantity_text)
            if quantity <= 0:
                await update.message.reply_text("❌ Quantity must be positive.")
                return

            wizard = context.user_data["wizard"]
            direction = wizard["data"].get("direction", "long")

            # Adjust quantity based on direction
            if direction == "short":
                quantity = -quantity

            # Get current price from market data
            current_price = await self.get_current_price("BTC-USDT-PERP")

            # Calculate costs using costing service
            costs = costing_service.calculate_total_cost(
                quantity, current_price, "OKX", "perpetual"
            )

            # Calculate delta impact
            delta_impact = quantity  # 1:1 for perpetuals

            text = (
                f"📋 *Trade Preview*\n\n"
                f"Symbol: BTC-USDT-PERP\n"
                f"Direction: {'🟢 LONG' if quantity > 0 else '🔴 SHORT'}\n"
                f"Quantity: {abs(quantity):.4f} BTC\n"
                f"Price: ${current_price:.2f}\n"
                f"Delta Impact: {delta_impact:+.4f} BTC\n\n"
                f"{costing_service.get_cost_summary(quantity, current_price, 'OKX', 'perpetual')}"
            )

            # Store trade data
            context.user_data["pending_trade"] = {
                "action_type": "add",
                "symbol": "BTC-USDT-PERP",
                "qty": quantity,
                "price": current_price,
                "instrument_type": "perpetual",
                "exchange": "OKX",
            }

            await update.message.reply_text(
                text,
                reply_markup=get_confirmation_buttons("portfolio"),
                parse_mode="Markdown",
            )

            # Clear wizard state
            del context.user_data["wizard"]

        except ValueError:
            await update.message.reply_text(
                "❌ Please enter a valid number (e.g., 5.0)"
            )

    async def handle_future_direction(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict
    ):
        """Handle future direction selection."""
        query = update.callback_query
        direction = data.get("direction", "long")

        # Update wizard state
        if "wizard" in context.user_data:
            context.user_data["wizard"]["data"]["direction"] = direction
            context.user_data["wizard"]["step"] = "quantity"

        text = (
            f"➕ *Add Future Position*\n\n"
            f"Symbol: BTC-USDT-PERP\n"
            f"Direction: {'🟢 LONG' if direction == 'long' else '🔴 SHORT'}\n"
            f"Please enter the quantity (in BTC):\n\n"
            f"Example: `5.0` for 5 BTC"
        )

        await query.edit_message_text(
            text, reply_markup=get_back_button(), parse_mode="Markdown"
        )

    async def handle_remove_spot(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict
    ):
        """Handle remove spot position."""
        query = update.callback_query
        symbol = data.get("symbol")

        if not symbol:
            await query.edit_message_text(
                "❌ No symbol specified.", reply_markup=get_back_button()
            )
            return

        position = self.portfolio.get_position(symbol)
        if not position:
            await query.edit_message_text(
                f"❌ Position {symbol} not found.", reply_markup=get_back_button()
            )
            return

        # Get current price
        current_price = await self.get_current_price(symbol)

        # Calculate costs
        costs = costing_service.calculate_total_cost(
            -position.qty, current_price, position.exchange, position.instrument_type
        )

        text = (
            f"📋 *Remove Position Preview*\n\n"
            f"Symbol: {symbol}\n"
            f"Current Position: {position.qty:+.4f} @ ${position.avg_px:.2f}\n"
            f"Current Price: ${current_price:.2f}\n"
            f"P&L: ${(current_price - position.avg_px) * position.qty:+.2f}\n\n"
            f"{costing_service.get_cost_summary(-position.qty, current_price, position.exchange, position.instrument_type)}"
        )

        # Store pending trade
        context.user_data["pending_trade"] = {
            "action_type": "remove",
            "symbol": symbol,
            "qty": -position.qty,
            "price": current_price,
            "instrument_type": position.instrument_type,
            "exchange": position.exchange,
        }

        await query.edit_message_text(
            text,
            reply_markup=get_confirmation_buttons("portfolio"),
            parse_mode="Markdown",
        )

    async def handle_remove_future(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict
    ):
        """Handle remove future position."""
        query = update.callback_query
        symbol = data.get("symbol")

        if not symbol:
            await query.edit_message_text(
                "❌ No symbol specified.", reply_markup=get_back_button()
            )
            return

        position = self.portfolio.get_position(symbol)
        if not position:
            await query.edit_message_text(
                f"❌ Position {symbol} not found.", reply_markup=get_back_button()
            )
            return

        # Get current price
        current_price = await self.get_current_price(symbol)

        # Calculate costs
        costs = costing_service.calculate_total_cost(
            -position.qty, current_price, position.exchange, position.instrument_type
        )

        text = (
            f"📋 *Remove Position Preview*\n\n"
            f"Symbol: {symbol}\n"
            f"Current Position: {position.qty:+.4f} @ ${position.avg_px:.2f}\n"
            f"Current Price: ${current_price:.2f}\n"
            f"P&L: ${(current_price - position.avg_px) * position.qty:+.2f}\n\n"
            f"{costing_service.get_cost_summary(-position.qty, current_price, position.exchange, position.instrument_type)}"
        )

        # Store pending trade
        context.user_data["pending_trade"] = {
            "action_type": "remove",
            "symbol": symbol,
            "qty": -position.qty,
            "price": current_price,
            "instrument_type": position.instrument_type,
            "exchange": position.exchange,
        }

        await query.edit_message_text(
            text,
            reply_markup=get_confirmation_buttons("portfolio"),
            parse_mode="Markdown",
        )

    async def handle_risk_config_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, step: str, data: dict
    ):
        """Handle risk config menu and edit flows."""
        query = update.callback_query
        if step == "edit":
            metric = data if isinstance(data, str) else data.get("metric")
            # Ask for new value
            if metric == "delta":
                prompt = "Enter new *absolute delta* threshold (BTC):"
            elif metric == "var":
                prompt = "Enter new *95% VaR* threshold (USD):"
            elif metric == "drawdown":
                prompt = "Enter new *max drawdown* (as decimal, e.g. 0.15 for 15%):"
            else:
                prompt = "Unknown metric."
            await query.edit_message_text(prompt, parse_mode="Markdown")
            context.user_data["risk_config_edit"] = metric
            context.user_data["awaiting_risk_value"] = True
        elif step == "confirm":
            metric = context.user_data.get("risk_config_edit")
            value = context.user_data.get("risk_config_new_value")
            # Update config
            if metric == "delta":
                self.risk_config["abs_delta"] = float(value)
            elif metric == "var":
                self.risk_config["var_95"] = float(value)
            elif metric == "drawdown":
                self.risk_config["max_drawdown"] = float(value)
            await query.edit_message_text(f"✅ Updated {metric} threshold to {value}.")
            await self.show_risk_config(update, context)
        elif step == "cancel":
            await self.show_risk_config(update, context)
        else:
            await query.edit_message_text("Unknown risk config action.")


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
